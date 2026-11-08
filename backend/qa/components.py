"""SOLID-aligned components for Grounded Q&A in SE201 Study Buddy.

Provides fine-grained, decoupled interfaces and implementations for:
- QueryGuard (Security & prompt injection detection)
- QueryReformulator (Contextual conversational query rewriting with caching & short-circuiting)
- ContextBuilder (Retrieved context formatting and prompt scaffolding)
- CitationVerifier (Inline citation extraction, normalization, and hallucination verification)
- GroundingEvaluator (Confidence scoring and visual UI badge generation)
- PipelineProfiler (Analyzability and performance telemetry)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import time
from typing import Any, Mapping, Protocol, runtime_checkable

from backend.interfaces import ChatTurn, Chunk, Citation, LLMClient
from backend.qa.qa_prompts import (
    CITATION_PATTERN,
    GROUNDED_QA_SYSTEM_PROMPT,
    INJECTION_PATTERNS,
    OUT_OF_SCOPE_FALLBACK_TEXT,
    REFORMULATION_SYSTEM_PROMPT,
    SECURITY_REFUSAL_TEXT,
    build_qa_prompt,
    compute_grounding_confidence,
    extract_supporting_excerpt,
    format_chunks,
    format_grounding_badge,
    is_out_of_scope_response,
    verify_citation_against_chunks,
)


# ---------------------------------------------------------------------------
# Protocols (Interface Segregation Principle & Dependency Inversion)
# ---------------------------------------------------------------------------

@runtime_checkable
class QueryGuard(Protocol):
    """SRP: Guard against prompt injection, jailbreaks, and adversarial queries."""

    def check(self, user_query: str) -> tuple[str, bool]:
        """Return (cleaned_query, is_injection_detected)."""
        ...


@runtime_checkable
class QueryReformulator(Protocol):
    """SRP: Multi-turn conversational query contextualization."""

    def contextualize(self, user_query: str, history: list[ChatTurn]) -> str:
        """Reformulate conversational follow-ups into standalone retrieval queries."""
        ...


@runtime_checkable
class CitationVerifier(Protocol):
    """SRP: Citation extraction and hallucination verification against retrieved context."""

    def extract_and_verify(
        self,
        response_text: str,
        chunks: list[Chunk],
    ) -> tuple[list[Citation], bool]:
        """Return (verified_citations, raw_citations_found)."""
        ...


@runtime_checkable
class GroundingEvaluator(Protocol):
    """SRP: Confidence scoring and visual UI badge annotations."""

    def evaluate(
        self,
        citations: list[Citation],
        chunks: list[Chunk],
        is_grounded: bool,
    ) -> tuple[int, str]:
        """Return (confidence_score, visual_badge)."""
        ...


# ---------------------------------------------------------------------------
# Analyzability & Performance Telemetry
# ---------------------------------------------------------------------------

@dataclass
class QAPipelineMetrics:
    """Latency, token, and verification diagnostics for analyzability."""
    guard_latency_ms: float = 0.0
    reformulation_latency_ms: float = 0.0
    retrieval_latency_ms: float = 0.0
    generation_latency_ms: float = 0.0
    verification_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    reformulated: bool = False
    chunks_retrieved_count: int = 0
    raw_citations_found: bool = False
    valid_citations_count: int = 0
    confidence_score: int = 0


# ---------------------------------------------------------------------------
# Concrete Implementations
# ---------------------------------------------------------------------------

class RegexQueryGuard:
    """Fast compiled-regex guard against known adversarial prompt injections."""

    def __init__(self, patterns: list[re.Pattern] | None = None):
        self.patterns = patterns or INJECTION_PATTERNS

    def check(self, user_query: str) -> tuple[str, bool]:
        clean_query = user_query.strip()
        for pattern in self.patterns:
            if pattern.search(clean_query):
                return clean_query, True
        return clean_query, False


class ConversationalQueryReformulator:
    """High-performance multi-turn query reformulator.

    Includes fast-path short-circuiting and LRU query cache to eliminate
    redundant LLM roundtrips and improve system responsiveness.
    """

    def __init__(self, llm: LLMClient | None = None, max_cache_size: int = 64):
        self.llm = llm
        self._cache: dict[tuple[str, str], str] = {}
        self._max_cache_size = max_cache_size
        self._follow_up_cues = [
            "it", "this", "that", "these", "those", "they",
            "point", "step", "again", "more detail", "elaborate", "why", "how so"
        ]

    def contextualize(self, user_query: str, history: list[ChatTurn]) -> str:
        clean_query = user_query.strip()
        if not history:
            return clean_query

        # Performance optimization: fast-path check if question is clearly self-contained
        q_lower = clean_query.lower()
        has_cues = any(re.search(r"\b" + re.escape(cue) + r"\b", q_lower) for cue in self._follow_up_cues)
        is_short = len(clean_query.split()) <= 4

        if not has_cues and not is_short:
            return clean_query

        # Check in-memory cache
        cache_key = (clean_query, history[-1].content[:100] if history else "")
        if cache_key in self._cache:
            return self._cache[cache_key]

        rewritten = clean_query
        if self.llm is not None and hasattr(self.llm, "complete"):
            try:
                history_summary = "\n".join(
                    f"{turn.role.capitalize()}: {turn.content[:200]}"
                    for turn in history[-4:]
                )
                prompt = f"Chat History:\n{history_summary}\n\nFollow-up Question: {clean_query}\n\nStandalone Query:"
                result = self.llm.complete(
                    system=REFORMULATION_SYSTEM_PROMPT,
                    messages=[ChatTurn(role="user", content=prompt)],
                )
                candidate = result.strip().strip('"').strip("'")
                if candidate and len(candidate) > 2:
                    rewritten = candidate
            except Exception:
                rewritten = self._heuristic_fallback(clean_query, history)
        else:
            rewritten = self._heuristic_fallback(clean_query, history)

        # Update cache (evict simplest entry if at cap)
        if len(self._cache) >= self._max_cache_size:
            self._cache.pop(next(iter(self._cache)))
        self._cache[cache_key] = rewritten
        return rewritten

    @staticmethod
    def _heuristic_fallback(query: str, history: list[ChatTurn]) -> str:
        latest_turn = history[-1].content
        keywords = [
            w for w in re.findall(r"[A-Za-z0-9_-]{4,}", latest_turn)
            if w.lower() not in {"this", "that", "with", "from", "have", "were", "what"}
        ]
        context_prefix = " ".join(keywords[:4]) if keywords else ""
        return f"{context_prefix} {query}".strip()


class StrictCitationVerifier:
    """Verifies citations from LLM output against retrieved chunk metadata to prevent hallucinations."""

    def extract_and_verify(
        self,
        response_text: str,
        chunks: list[Chunk],
    ) -> tuple[list[Citation], bool]:
        raw_citations_found = bool(CITATION_PATTERN.search(response_text))
        citations: list[Citation] = []
        seen = set()

        for match in CITATION_PATTERN.finditer(response_text):
            source = match.group(1).strip()
            location = match.group(2).strip()
            key = (source.lower(), location.lower())
            if key in seen:
                continue
            seen.add(key)

            is_valid, matched_quote = verify_citation_against_chunks(source, location, chunks)
            if not is_valid:
                # Discard hallucinated citation
                continue

            citations.append(Citation(source_file=source, location=location, quote=matched_quote))

        return citations, raw_citations_found


class DefaultGroundingEvaluator:
    """Evaluates composite grounding confidence and builds visual badges."""

    def evaluate(
        self,
        citations: list[Citation],
        chunks: list[Chunk],
        is_grounded: bool,
    ) -> tuple[int, str]:
        confidence = compute_grounding_confidence(citations, chunks, is_grounded)
        primary_source = (
            citations[0].source_file if citations
            else (chunks[0].source_file if chunks else "")
        )
        badge = format_grounding_badge(confidence, primary_source)
        return confidence, badge

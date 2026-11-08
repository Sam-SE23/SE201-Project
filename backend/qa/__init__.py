"""Real grounded Q&A engine (owner: Guru).

Adheres to SOLID principles:
- Single Responsibility: Guarding, reformulation, verification, and evaluation are partitioned.
- Open/Closed: Engine accepts injected pipelines, guards, and validators without modifying core orchestration.
- Liskov Substitution: Strictly satisfies backend.interfaces.QAEngine.
- Interface Segregation: Protocols are scoped to exact capabilities (QueryGuard, QueryReformulator, etc.).
- Dependency Inversion: Depends on abstract Protocols rather than concrete implementations.

Provides:
    create_qa_engine(llm: LLMClient) -> QAEngine
"""

from __future__ import annotations

import time
from typing import Any, Mapping

from backend.interfaces import Answer, ChatTurn, Chunk, Citation, LLMClient, QAEngine, Retriever
from backend.qa.components import (
    CitationVerifier,
    ConversationalQueryReformulator,
    DefaultGroundingEvaluator,
    GroundingEvaluator,
    QAPipelineMetrics,
    QueryGuard,
    QueryReformulator,
    RegexQueryGuard,
    StrictCitationVerifier,
)
from backend.qa.qa_prompts import (
    CITATION_PATTERN,
    GROUNDED_QA_SYSTEM_PROMPT,
    OUT_OF_SCOPE_FALLBACK_TEXT,
    SECURITY_REFUSAL_TEXT,
    build_qa_prompt,
    compute_grounding_confidence,
    contextualize_query,
    extract_citations_from_text,
    extract_supporting_excerpt,
    format_chunks,
    format_grounding_badge,
    is_out_of_scope_response,
    sanitize_and_detect_injection,
)

TOP_K = 4


class GroundedQAEngine:
    """QAEngine implementing grounded Q&A pipeline with strict citations and SOLID architecture."""

    def __init__(
        self,
        llm: LLMClient,
        top_k: int = TOP_K,
        guard: QueryGuard | None = None,
        reformulator: QueryReformulator | None = None,
        citation_verifier: CitationVerifier | None = None,
        evaluator: GroundingEvaluator | None = None,
    ):
        self.llm = llm
        self.top_k = top_k
        self.guard = guard or RegexQueryGuard()
        self.reformulator = reformulator or ConversationalQueryReformulator(llm)
        self.citation_verifier = citation_verifier or StrictCitationVerifier()
        self.evaluator = evaluator or DefaultGroundingEvaluator()
        self.last_metrics: QAPipelineMetrics | None = None

    def answer(
        self,
        question: str,
        retriever: Retriever,
        history: list[ChatTurn],
    ) -> Answer:
        metrics = QAPipelineMetrics()
        t0 = time.perf_counter()

        # 0. Adversarial Injection & Security Defense Check (SRP: QueryGuard)
        t_guard = time.perf_counter()
        _, is_injection = self.guard.check(question)
        metrics.guard_latency_ms = (time.perf_counter() - t_guard) * 1000

        if is_injection:
            metrics.total_latency_ms = (time.perf_counter() - t0) * 1000
            self.last_metrics = metrics
            return Answer(
                text=SECURITY_REFUSAL_TEXT,
                citations=[],
                chunks_used=[],
                grounded=False,
            )

        # 1. Multi-turn Conversational Query Reformulation (SRP: QueryReformulator)
        t_re = time.perf_counter()
        retrieval_query = self.reformulator.contextualize(question, history)
        metrics.reformulation_latency_ms = (time.perf_counter() - t_re) * 1000
        metrics.reformulated = (retrieval_query != question.strip())

        # 2. Vector Search Retrieval
        t_ret = time.perf_counter()
        chunks = retriever.retrieve(retrieval_query, self.top_k)
        metrics.retrieval_latency_ms = (time.perf_counter() - t_ret) * 1000
        metrics.chunks_retrieved_count = len(chunks)

        if not chunks:
            metrics.total_latency_ms = (time.perf_counter() - t0) * 1000
            self.last_metrics = metrics
            return Answer(
                text=OUT_OF_SCOPE_FALLBACK_TEXT,
                citations=[],
                chunks_used=[],
                grounded=False,
            )

        # Populate supporting excerpts on retrieved chunks for UI visibility
        augmented_chunks = [
            Chunk(
                id=c.id,
                text=extract_supporting_excerpt(c.text),
                source_file=c.source_file,
                location=c.location,
                score=c.score,
            )
            for c in chunks
        ]

        # 3. Build Grounded Prompt with retrieved context
        user_prompt = build_qa_prompt(question, chunks)
        messages = list(history) + [ChatTurn(role="user", content=user_prompt)]

        # 4. LLM Generation
        t_gen = time.perf_counter()
        response_text = self.llm.complete(
            system=GROUNDED_QA_SYSTEM_PROMPT,
            messages=messages,
        )
        metrics.generation_latency_ms = (time.perf_counter() - t_gen) * 1000

        # 5. Extract citations and evaluate grounding (SRP: CitationVerifier)
        t_ver = time.perf_counter()
        citations, raw_citations_found = self.citation_verifier.extract_and_verify(
            response_text,
            chunks,
        )
        metrics.verification_latency_ms = (time.perf_counter() - t_ver) * 1000
        metrics.raw_citations_found = raw_citations_found
        metrics.valid_citations_count = len(citations)

        # If LLM generated inline citations but none verified, flag as ungrounded
        if raw_citations_found and not citations:
            is_grounded = False
        else:
            is_grounded = not is_out_of_scope_response(response_text)

        # Fallback to chunk metadata only if no inline citations were generated in text
        if not raw_citations_found and not citations and chunks and not is_out_of_scope_response(response_text):
            citations = [Citation(c.source_file, c.location, c.text) for c in chunks]

        # 6. Compute Grounding Confidence Score and Visual Badge (SRP: GroundingEvaluator)
        confidence, badge = self.evaluator.evaluate(citations, chunks, is_grounded)
        metrics.confidence_score = confidence
        metrics.total_latency_ms = (time.perf_counter() - t0) * 1000
        self.last_metrics = metrics

        annotated_text = f"{badge}\n\n{response_text.strip()}"

        return Answer(
            text=annotated_text,
            citations=citations,
            chunks_used=augmented_chunks,
            grounded=is_grounded,
        )


def create_qa_engine(llm: LLMClient) -> QAEngine:
    return GroundedQAEngine(llm)


__all__ = [
    "GroundedQAEngine",
    "create_qa_engine",
    "GROUNDED_QA_SYSTEM_PROMPT",
    "OUT_OF_SCOPE_FALLBACK_TEXT",
    "build_qa_prompt",
    "format_chunks",
    "extract_citations_from_text",
    "is_out_of_scope_response",
    "QueryGuard",
    "QueryReformulator",
    "CitationVerifier",
    "GroundingEvaluator",
    "QAPipelineMetrics",
]

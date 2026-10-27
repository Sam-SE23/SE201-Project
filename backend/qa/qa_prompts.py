"""Prompts and prompt templates for Grounded Q&A in SE201 Study Buddy."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Mapping

from backend.interfaces import ChatTurn, Chunk, Citation

REFORMULATION_SYSTEM_PROMPT = """You are a conversational query reformulation assistant for a Course Study Buddy RAG system.
Given a conversation history and a follow-up user question, rewrite the follow-up question into a standalone search query that contains all necessary technical context and nouns from previous turns.
Do NOT answer the question. Only output the rewritten standalone query. If the query is already self-contained, return it unchanged.
"""

SECURITY_REFUSAL_TEXT = (
    "Security Notice: Query contains instructions that violate grounding rules. "
    "Answers must strictly remain within the scope of uploaded course materials."
)

INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"act\s+as\s+(an?\s+)?ungrounded", re.IGNORECASE),
    re.compile(r"disregard\s+(the\s+)?rules?", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"DAN\s+mode", re.IGNORECASE),
    re.compile(r"developer\s+mode", re.IGNORECASE),
]


def sanitize_and_detect_injection(user_query: str) -> tuple[str, bool]:
    """Inspect query for adversarial injection or jailbreak attempts.

    Returns (sanitized_query, is_injection_detected).
    """
    clean_query = user_query.strip()
    for pattern in INJECTION_PATTERNS:
        if pattern.search(clean_query):
            return clean_query, True
    return clean_query, False


def contextualize_query(
    user_query: str,
    history: list[ChatTurn],
    llm: Any = None,
) -> str:
    """Rewrite follow-up queries using conversation history to ensure standalone retrieval.

    If history is empty, returns user_query as is.
    If an LLM client is available, prompts it to resolve coreferences and ambiguous follow-ups;
    otherwise applies heuristic coreference rewriting.
    """
    if not history:
        return user_query.strip()

    # Heuristic detection of conversational follow-ups
    q_lower = user_query.strip().lower()
    follow_up_cues = ["it", "this", "that", "these", "those", "they", "point", "step", "again", "more detail", "elaborate", "why", "how so"]
    is_ambiguous = any(re.search(r"\b" + re.escape(cue) + r"\b", q_lower) for cue in follow_up_cues) or len(user_query.split()) <= 4

    if not is_ambiguous:
        return user_query.strip()

    if llm is not None and hasattr(llm, "complete"):
        try:
            history_summary = "\n".join(f"{turn.role.capitalize()}: {turn.content[:200]}" for turn in history[-4:])
            prompt = f"Chat History:\n{history_summary}\n\nFollow-up Question: {user_query}\n\nStandalone Query:"
            rewritten = llm.complete(
                system=REFORMULATION_SYSTEM_PROMPT,
                messages=[ChatTurn(role="user", content=prompt)],
            )
            cleaned = rewritten.strip().strip('"').strip("'")
            if cleaned and len(cleaned) > 2:
                return cleaned
        except Exception:
            pass  # Fall back to heuristic

    # Deterministic heuristic fallback: extract key technical noun phrases from latest turn
    latest_turn = history[-1].content
    # Extract noun tokens (length > 3, alphanumeric)
    keywords = [w for w in re.findall(r"[A-Za-z0-9_-]{4,}", latest_turn) if w.lower() not in {"this", "that", "with", "from", "have", "were", "what"}]
    context_prefix = " ".join(keywords[:4]) if keywords else ""
    return f"{context_prefix} {user_query}".strip()

GROUNDED_QA_SYSTEM_PROMPT = """You are an AI Course Study Assistant for SE201: AI-Driven Software Engineering. Your goal is to answer student questions accurately, concisely, and strictly grounded in the provided course materials.

CRITICAL GROUNDING & CITATION RULES:
1. STRICT GROUNDING: Answer the user's question USING ONLY the provided course contexts in <retrieved_context>. Do NOT use outside training data, external facts, or unstated assumptions.
2. INLINE CITATIONS: Every factual claim, bullet point, or explanation must end with an explicit inline citation matching the metadata of the source chunk. Use the format: [Source Title, Section/Slide #] (or [Source Title, Page #]).
3. OUT-OF-SCOPE FALLBACK: If the provided <retrieved_context> does NOT contain sufficient information to answer the question, respond with:
   "I cannot find information regarding this topic in the provided course materials. Please consult the course staff or syllabus."
   Do NOT attempt to guess, fill in missing details from general knowledge, or fabricate answers.
4. ACADEMIC INTEGRITY & SOCRATIC GUIDANCE: If a student asks for complete code solutions to graded assignments, lab tasks, or quiz answer keys:
   - Under no circumstances generate complete, ready-to-submit assignment code.
   - Instead, provide a structured 3-step Socratic hint guide and a conceptual pseudocode framework grounded in the lecture slides, with explicit inline citations:
     Step 1: Conceptual Architecture (explain the theoretical mechanism and algorithmic objective).
     Step 2: Step-by-Step Implementation Hints (detail component interactions and data structures to consider).
     Step 3: Conceptual Pseudocode Framework & Debugging Checks (provide high-level pseudocode scaffolding with edge cases to test).
5. NO PREAMBLES: Jump straight into the answer without saying "Based on the provided context..." or "According to the slides...".
"""

OUT_OF_SCOPE_FALLBACK_TEXT = (
    "I cannot find information regarding this topic in the provided course materials. "
    "Please consult the course staff or syllabus."
)

QA_USER_PROMPT_TEMPLATE = """<retrieved_context>
{formatted_chunks}
</retrieved_context>

User Question: {user_query}

Provide a well-structured, clear, and fully cited answer adhering strictly to the system prompt rules above."""


def format_chunk(chunk: Chunk | Mapping[str, Any], index: int = 1) -> str:
    """Format an individual chunk into a structured context block.

    Supports both Chunk dataclasses (interfaces.py) and dicts (e.g. from retrieve.py).
    Expected keys/attributes:
      - text: the text content of the chunk
      - source_title / source_file / source: document title or filename
      - slide_or_page / location / page: slide number, page number, or section label
    """
    if isinstance(chunk, Chunk):
        text = chunk.text
        source_title = chunk.source_file
        slide_or_page = chunk.location
    else:
        text = chunk.get("text", "")
        source_title = (
            chunk.get("source_title")
            or chunk.get("source_file")
            or chunk.get("source")
            or "Unknown Source"
        )
        slide_or_page = (
            chunk.get("slide_or_page")
            or chunk.get("location")
            or chunk.get("page")
            or "Unknown Section"
        )

    # Normalize integer or numeric page/slide representations if needed
    if isinstance(slide_or_page, int) or (
        isinstance(slide_or_page, str) and slide_or_page.isdigit()
    ):
        location_str = f"Page {slide_or_page}"
    else:
        location_str = str(slide_or_page)

    return (
        f"--- Chunk {index} ---\n"
        f"Source: {source_title}\n"
        f"Location: {location_str}\n"
        f"Content:\n{text.strip()}"
    )


def format_chunks(chunks: list[Chunk | Mapping[str, Any]]) -> str:
    """Format a list of retrieved chunks into the {formatted_chunks} string."""
    if not chunks:
        return "No relevant context found."
    return "\n\n".join(format_chunk(c, i) for i, c in enumerate(chunks, start=1))


def build_qa_prompt(user_query: str, chunks: list[Chunk | Mapping[str, Any]]) -> str:
    """Build the complete user prompt from user_query and retrieved chunks."""
    return QA_USER_PROMPT_TEMPLATE.format(
        formatted_chunks=format_chunks(chunks),
        user_query=user_query.strip(),
    )


# Matches citations like [Source Title, Slide 5], [Lecture 2.pdf, Page 12], etc.
CITATION_PATTERN = re.compile(r"\[([^,\]]+),\s*([^\]]+)\]")


def _normalize_loc(loc: str) -> str:
    """Normalize location string for robust matching, e.g. 'Slide 5' -> 'slide 5', 'Page 12' -> 'p.12'."""
    s = loc.strip().lower()
    s = re.sub(r"^page\s*", "p.", s)
    s = re.sub(r"^p\.\s*", "p.", s)
    s = re.sub(r"^slide\s*", "slide ", s)
    return s


def verify_citation_against_chunks(
    source: str,
    location: str,
    chunks: list[Chunk | Mapping[str, Any]],
) -> tuple[bool, str]:
    """Verify if a cited source and slide/page location exists in chunks_used.

    Returns (is_valid, matching_quote).
    """
    norm_source = source.strip().lower()
    norm_loc = _normalize_loc(location)
    loc_digits = re.findall(r"\d+", norm_loc)

    for c in chunks:
        c_source = c.source_file if isinstance(c, Chunk) else (
            c.get("source_file") or c.get("source_title") or c.get("source") or ""
        )
        c_loc = c.location if isinstance(c, Chunk) else (
            c.get("location") or c.get("slide_or_page") or str(c.get("page") or "")
        )
        norm_c_source = c_source.strip().lower()
        norm_c_loc = _normalize_loc(c_loc)
        c_digits = re.findall(r"\d+", norm_c_loc)

        # Check source filename or title overlap
        source_matches = (
            norm_source in norm_c_source
            or norm_c_source in norm_source
            or Path(norm_source).stem == Path(norm_c_source).stem
        )
        if not source_matches:
            continue

        # Check location match (either normalized match or matching slide/page number)
        loc_matches = (norm_loc == norm_c_loc) or (loc_digits and c_digits and loc_digits[0] == c_digits[0])
        if loc_matches:
            quote = c.text if isinstance(c, Chunk) else c.get("text", "")
            return True, quote

    return False, ""


def extract_citations_from_text(
    response_text: str,
    chunks: list[Chunk | Mapping[str, Any]] | None = None,
) -> list[Citation]:
    """Parse inline citations of the form `[Source Title, Section/Slide/Page #]` from response text.

    If chunks are provided, programmatically verifies each citation against chunks_used metadata.
    Invalid citations that hallucinate non-existent slide/page numbers are dropped.
    """
    citations: list[Citation] = []
    seen = set()

    for match in CITATION_PATTERN.finditer(response_text):
        source = match.group(1).strip()
        location = match.group(2).strip()
        key = (source.lower(), location.lower())
        if key in seen:
            continue
        seen.add(key)

        quote = ""
        if chunks is not None:
            is_valid, matched_quote = verify_citation_against_chunks(source, location, chunks)
            if not is_valid:
                # Flagged as invalid / hallucinated citation not present in retrieved context
                continue
            quote = matched_quote

        citations.append(Citation(source_file=source, location=location, quote=quote))

    return citations


def is_out_of_scope_response(response_text: str) -> bool:
    """Determine whether the response was an out-of-scope fallback."""
    canonical = OUT_OF_SCOPE_FALLBACK_TEXT.lower().strip()
    return (
        canonical in response_text.lower()
        or "i cannot find information regarding this topic in the provided course materials"
        in response_text.lower()
    )


def compute_grounding_confidence(
    citations: list[Citation],
    chunks: list[Chunk | Mapping[str, Any]],
    is_grounded: bool,
) -> int:
    """Compute a composite Grounding Confidence Score (0-100%).

    Factors in chunk retrieval presence, similarity scores, valid citation count, and grounding flag.
    """
    if not is_grounded or not chunks:
        return 0

    score = 70  # Base grounded confidence

    # Factor in validated citations
    if citations:
        score += min(len(citations) * 10, 20)
    else:
        score -= 20

    # Factor in chunk retrieval scores if available
    scores = [
        c.score for c in chunks
        if isinstance(c, Chunk) and c.score is not None
    ]
    if scores:
        avg_sim = sum(scores) / len(scores)
        if avg_sim >= 0.6:
            score += 10
        elif avg_sim < 0.35:
            score -= 10

    return max(0, min(100, score))


def format_grounding_badge(confidence: int, primary_source: str = "") -> str:
    """Generate a clean visual grounding badge for UI display."""
    src_label = f" [Grounded in {primary_source}]" if primary_source else ""
    if confidence >= 85:
        return f"🟢 Grounding Confidence: {confidence}%{src_label}"
    elif confidence >= 60:
        return f"🟡 Grounding Confidence: {confidence}%{src_label}"
    else:
        return f"🔴 Grounding Confidence: {confidence}% (Low Grounding / Fallback)"


def extract_supporting_excerpt(chunk_text: str, max_sentences: int = 2) -> str:
    """Extract a concise 1-2 sentence supporting quote excerpt from chunk text."""
    sentences = re.split(r"(?<=[.!?])\s+", chunk_text.strip())
    excerpt = " ".join(sentences[:max_sentences]).strip()
    return excerpt if excerpt else chunk_text[:200]

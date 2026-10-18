"""Prompts and prompt templates for Grounded Q&A in SE201 Study Buddy."""

from __future__ import annotations

import re
from typing import Any, Mapping

from backend.interfaces import Chunk, Citation

GROUNDED_QA_SYSTEM_PROMPT = """You are an AI Course Study Assistant for SE201: AI-Driven Software Engineering. Your goal is to answer student questions accurately, concisely, and strictly grounded in the provided course materials.

CRITICAL GROUNDING & CITATION RULES:
1. STRICT GROUNDING: Answer the user's question USING ONLY the provided course contexts in <retrieved_context>. Do NOT use outside training data, external facts, or unstated assumptions.
2. INLINE CITATIONS: Every factual claim, bullet point, or explanation must end with an explicit inline citation matching the metadata of the source chunk. Use the format: [Source Title, Section/Slide #] (or [Source Title, Page #]).
3. OUT-OF-SCOPE FALLBACK: If the provided <retrieved_context> does NOT contain sufficient information to answer the question, respond with:
   "I cannot find information regarding this topic in the provided course materials. Please consult the course staff or syllabus."
   Do NOT attempt to guess, fill in missing details from general knowledge, or fabricate answers.
4. ACADEMIC INTEGRITY: If the student asks for direct code solutions to graded assignments, provide high-level conceptual guidance, pseudocode, or debugging hints with source citations—do NOT generate complete assignment solutions.
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


def extract_citations_from_text(
    response_text: str,
    chunks: list[Chunk | Mapping[str, Any]] | None = None,
) -> list[Citation]:
    """Parse inline citations of the form `[Source Title, Section/Slide/Page #]` from response text.

    Optionally matches against the retrieved chunks to associate supporting quote text.
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

        # Find best matching chunk quote if available
        quote = ""
        if chunks:
            for c in chunks:
                c_source = c.source_file if isinstance(c, Chunk) else (
                    c.get("source_title") or c.get("source_file") or c.get("source") or ""
                )
                c_loc = c.location if isinstance(c, Chunk) else (
                    c.get("slide_or_page") or c.get("location") or str(c.get("page") or "")
                )
                if source.lower() in c_source.lower() or c_source.lower() in source.lower():
                    quote = c.text if isinstance(c, Chunk) else c.get("text", "")
                    break

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

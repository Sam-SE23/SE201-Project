"""Real grounded Q&A engine (owner: Guru).

Provides:
    create_qa_engine(llm: LLMClient) -> QAEngine
"""

from __future__ import annotations

from typing import Any, Mapping

from backend.interfaces import Answer, ChatTurn, Chunk, Citation, LLMClient, QAEngine, Retriever
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
    """QAEngine implementing grounded Q&A pipeline with strict citations."""

    def __init__(self, llm: LLMClient, top_k: int = TOP_K):
        self.llm = llm
        self.top_k = top_k

    def answer(
        self,
        question: str,
        retriever: Retriever,
        history: list[ChatTurn],
    ) -> Answer:
        # 0. Adversarial Injection & Security Defense Check
        _, is_injection = sanitize_and_detect_injection(question)
        if is_injection:
            return Answer(
                text=SECURITY_REFUSAL_TEXT,
                citations=[],
                chunks_used=[],
                grounded=False,
            )

        # 1. Multi-turn Conversational Query Reformulation
        retrieval_query = contextualize_query(question, history, llm=self.llm)

        # 2. Vector Search Retrieval
        chunks = retriever.retrieve(retrieval_query, self.top_k)
        if not chunks:
            return Answer(
                text=OUT_OF_SCOPE_FALLBACK_TEXT,
                citations=[],
                chunks_used=[],
                grounded=False,
            )

        # Populate supporting excerpts on retrieved chunks for UI visibility
        augmented_chunks = []
        for c in chunks:
            excerpt = extract_supporting_excerpt(c.text)
            augmented_chunks.append(Chunk(
                id=c.id,
                text=excerpt,  # concise supporting excerpt
                source_file=c.source_file,
                location=c.location,
                score=c.score,
            ))

        # 3. Build Grounded Prompt with retrieved context
        user_prompt = build_qa_prompt(question, chunks)

        # Combine previous conversation turns with the current prompt
        messages = list(history) + [ChatTurn(role="user", content=user_prompt)]

        # 4. LLM Generation
        response_text = self.llm.complete(
            system=GROUNDED_QA_SYSTEM_PROMPT,
            messages=messages,
        )

        # 5. Extract citations and evaluate grounding
        raw_citations_found = bool(CITATION_PATTERN.search(response_text))
        citations = extract_citations_from_text(response_text, chunks=chunks)
        
        # If the LLM cited sources but none verified against chunks_used, mark ungrounded
        if raw_citations_found and not citations:
            is_grounded = False
        else:
            is_grounded = not is_out_of_scope_response(response_text)

        # Fallback to chunk metadata only if no inline citations were in text at all
        if not raw_citations_found and not citations and chunks and not is_out_of_scope_response(response_text):
            citations = [Citation(c.source_file, c.location, c.text) for c in chunks]

        # 6. Compute Grounding Confidence Score and Prepend Visual Badge
        confidence = compute_grounding_confidence(citations, chunks, is_grounded)
        primary_source = citations[0].source_file if citations else (chunks[0].source_file if chunks else "")
        badge = format_grounding_badge(confidence, primary_source)
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
]

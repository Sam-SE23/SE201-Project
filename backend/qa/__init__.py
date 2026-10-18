"""Real grounded Q&A engine (owner: Guru).

Provides:
    create_qa_engine(llm: LLMClient) -> QAEngine
"""

from __future__ import annotations

from typing import Any, Mapping

from backend.interfaces import Answer, ChatTurn, Chunk, Citation, LLMClient, QAEngine, Retriever
from backend.qa.qa_prompts import (
    GROUNDED_QA_SYSTEM_PROMPT,
    OUT_OF_SCOPE_FALLBACK_TEXT,
    build_qa_prompt,
    extract_citations_from_text,
    format_chunks,
    is_out_of_scope_response,
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
        # 1. Vector Search Retrieval
        chunks = retriever.retrieve(question, self.top_k)
        if not chunks:
            return Answer(
                text=OUT_OF_SCOPE_FALLBACK_TEXT,
                citations=[],
                chunks_used=[],
                grounded=False,
            )

        # 2. Build Grounded Prompt with retrieved context
        user_prompt = build_qa_prompt(question, chunks)

        # Combine previous conversation turns with the current prompt
        messages = list(history) + [ChatTurn(role="user", content=user_prompt)]

        # 3. LLM Generation
        response_text = self.llm.complete(
            system=GROUNDED_QA_SYSTEM_PROMPT,
            messages=messages,
        )

        # 4. Extract citations and evaluate grounding
        citations = extract_citations_from_text(response_text, chunks=chunks)
        # Fallback to chunk metadata if citations couldn't be regex-parsed but answer is present
        if not citations and chunks and not is_out_of_scope_response(response_text):
            citations = [Citation(c.source_file, c.location, c.text) for c in chunks]

        is_grounded = not is_out_of_scope_response(response_text)

        return Answer(
            text=response_text.strip(),
            citations=citations,
            chunks_used=chunks,
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

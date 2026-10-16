"""Stub QA engine: quotes the best-matching passage instead of calling an LLM."""

from __future__ import annotations

from backend.interfaces import Answer, ChatTurn, Citation, Retriever

TOP_K = 3


class FakeQA:
    def answer(self, question: str, retriever: Retriever,
               history: list[ChatTurn]) -> Answer:
        chunks = retriever.retrieve(question, TOP_K)
        if not chunks:
            return Answer(
                text="I couldn't find anything about that in your uploaded materials.",
                grounded=False,
            )
        citations = [Citation(c.source_file, c.location, c.text) for c in chunks]
        best = chunks[0].text.replace("\n", " ")
        if len(best) > 300:
            best = best[:300].rsplit(" ", 1)[0] + "…"
        text = (
            "**[STUB: the real QA engine is not connected yet]**\n\n"
            f"The most relevant passage I found says: \"{best}\" [1]"
        )
        if len(chunks) > 1:
            refs = ", ".join(f"[{i}]" for i in range(2, len(chunks) + 1))
            text += f"\n\nSee also {refs}."
        return Answer(text=text, citations=citations, chunks_used=chunks)

"""Stub retriever: keyword-overlap scoring over real extracted text.

It stands in for the Chroma/embedding retriever until that is ready. It does
read the uploaded files, so the UI shows real chunks and real locations.
"""

from __future__ import annotations

import re
from pathlib import Path

from backend.baseline.ctrl_f import extract_pages
from backend.interfaces import Chunk

CHUNK_CHARS = 600
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "of", "in", "on", "at",
    "to", "for", "and", "or", "what", "when", "where", "which", "who", "how",
    "why", "do", "does", "did", "it", "this", "that", "with", "as", "by", "from",
    "i", "you", "we", "they", "can", "should", "will", "about",
}


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS}


class FakeRetriever:
    def __init__(self) -> None:
        self._chunks: list[Chunk] = []

    def ingest(self, paths: list[Path]) -> int:
        names = {p.name for p in paths}
        self._chunks = [c for c in self._chunks if c.source_file not in names]
        added = 0
        for path in paths:
            for page in extract_pages(path):
                for i, text in enumerate(_split(page.text)):
                    self._chunks.append(Chunk(
                        id=f"{page.source_file}:{page.location}:{i}",
                        text=text,
                        source_file=page.source_file,
                        location=page.location,
                    ))
                    added += 1
        return added

    def retrieve(self, query: str, k: int) -> list[Chunk]:
        q = _tokens(query)
        if not q:
            return []
        scored = []
        for c in self._chunks:
            overlap = len(q & _tokens(c.text))
            if overlap:
                scored.append(Chunk(c.id, c.text, c.source_file, c.location,
                                    score=overlap / len(q)))
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:k]

    def list_documents(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in self._chunks:
            counts[c.source_file] = counts.get(c.source_file, 0) + 1
        return counts


def _split(text: str) -> list[str]:
    """Greedy split on blank lines / newlines into chunks of about CHUNK_CHARS."""
    chunks, current = [], ""
    for line in text.splitlines():
        if current and len(current) + len(line) > CHUNK_CHARS:
            chunks.append(current.strip())
            current = ""
        current += line + "\n"
    if current.strip():
        chunks.append(current.strip())
    return chunks

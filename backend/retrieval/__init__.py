"""Real retriever: adapts Lichelle's Chroma pipeline (rag-pipeline/) to the Retriever interface.

Provides:
    create_retriever() -> Retriever

Her pipeline is used as is, so build_index.py and `python -m pipeline.retrieve`
still work standalone and share the same Chroma store as the app.
"""

from __future__ import annotations

import sys
from pathlib import Path

from backend.interfaces import Chunk, Retriever

RAG_DIR = Path(__file__).resolve().parent / "rag-pipeline"

# Chroma always returns k hits, even for questions the material doesn't cover.
# Hits below this cosine similarity are dropped so out-of-scope questions get no
# chunks, which makes the QA engine use its "not found" fallback. Tune it on the
# benchmark's out-of-scope questions.
MIN_SCORE = 0.3


def _location(source: str, page: int) -> str:
    return f"slide {page}" if source.lower().endswith(".pptx") else f"p.{page}"


class ChromaRetriever:
    def __init__(self, min_score: float = MIN_SCORE) -> None:
        # rag-pipeline/ has a hyphen so it can't be a package; her modules import
        # each other as top-level `config` / `pipeline`, so put it first on the path.
        if str(RAG_DIR) not in sys.path:
            sys.path.insert(0, str(RAG_DIR))
        from pipeline import chunk, embed, ingest, retrieve, store

        self._chunk, self._embed, self._ingest = chunk, embed, ingest
        self._retrieve, self._store = retrieve, store
        self.min_score = min_score

    def ingest(self, paths: list[Path]) -> int:
        collection = self._store.get_collection()
        added = 0
        for path in paths:
            path = Path(path)
            loader = self._ingest.load_pptx if path.suffix.lower() == ".pptx" else self._ingest.load_pdf
            pages = loader(path)
            # Re-uploading a file replaces its chunks instead of colliding on ids.
            collection.delete(where={"source": path.name})
            chunks = self._chunk.chunk_pages(pages)
            if not chunks:
                continue
            self._store.add_chunks(chunks, self._embed.embed([c.text for c in chunks]))
            added += len(chunks)
        return added

    def retrieve(self, query: str, k: int) -> list[Chunk]:
        if not query.strip() or not self.list_documents():
            return []
        hits = self._retrieve.retrieve(query, k)
        out = []
        for i, h in enumerate(hits):
            if h["score"] < self.min_score:
                continue
            location = _location(h["source"], h["page"])
            out.append(Chunk(id=f"{h['source']}:{location}:{i}", text=h["text"],
                             source_file=h["source"], location=location, score=h["score"]))
        return out

    def list_documents(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for meta in self._store.get_collection().get(include=["metadatas"])["metadatas"]:
            counts[meta["source"]] = counts.get(meta["source"], 0) + 1
        return counts


def create_retriever() -> Retriever:
    return ChromaRetriever()

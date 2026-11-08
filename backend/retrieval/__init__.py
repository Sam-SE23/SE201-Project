"""Real retriever: adapts Lichelle's hybrid RAG pipeline (rag-pipeline/) to the Retriever interface.

Provides:
    create_retriever() -> Retriever

Her pipeline is used as is: vector search (Chroma) + BM25 keyword search, fused
and then reranked by a cross-encoder. build_index.py, evaluate_retrieval.py and
`python -m pipeline.retrieve` still work standalone on the same store as the app.

What the adapter adds on top of her code:
- Uploads from the GUI go into Chroma, and the BM25 keyword index is rebuilt
  from Chroma afterwards. Her bm25.build_index() overwrites the whole index,
  so Chroma is treated as the single source of truth.
- Reranker scores are converted to 0-1 probabilities, so Chunk.score keeps
  meaning "higher = more relevant, 0-1" for the QA engine's confidence badge.
- Hits below MIN_SCORE are dropped, so out-of-scope questions get no chunks and
  the QA engine falls back to "not found".
"""

from __future__ import annotations

import logging
import math
import sys
from pathlib import Path
from types import SimpleNamespace

from backend.files import delete_stored_copy
from backend.interfaces import Chunk, Retriever

log = logging.getLogger(__name__)

RAG_DIR = Path(__file__).resolve().parent / "rag-pipeline"

# Minimum reranker relevance probability (0-1) for a hit to be kept. Her
# pipeline always returns k hits, even for questions the material doesn't cover,
# so this cutoff is what makes out-of-scope questions return nothing.
# This is a cross-encoder probability, not cosine similarity. Measured on 9 Nov
# with the 21 SE201 PDFs indexed (705 chunks): the top hit for the 20 benchmark
# questions scored 0.026-0.9997 (weakest: temperature 0.026, GPU memory 0.31,
# neuron 0.46, back-propagation 0.56), and for 7 off-topic questions
# (photosynthesis, football, sourdough, Hamlet, stocks, volcanoes, translation)
# at most 0.0011. 0.01 keeps all 20 benchmark questions and drops all 7.
# "What is the capital of France?" scores 0.95 because Week 5 uses it as an example.
MIN_SCORE = 0.01


def _location(source: str, page: int) -> str:
    return f"slide {page}" if source.lower().endswith(".pptx") else f"p.{page}"


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def _reranker_returns_logits(reranker) -> bool:
    """sentence-transformers v4+ returns raw logits for ms-marco cross-encoders;
    older versions apply a sigmoid. Check which activation this one uses."""
    import torch

    activation = (getattr(reranker, "activation_fn", None)
                  or getattr(reranker, "default_activation_function", None))
    return activation is None or isinstance(activation, torch.nn.Identity)


class ChromaRetriever:
    def __init__(self, min_score: float = MIN_SCORE, store_dir: Path | None = None,
                 data_dir: Path | None = None) -> None:
        # rag-pipeline/ has a hyphen so it can't be a package; her modules import
        # each other as top-level `config` / `pipeline`, so put it first on the path.
        if str(RAG_DIR) not in sys.path:
            sys.path.insert(0, str(RAG_DIR))
        from pipeline import bm25, chunk, embed, ingest, retrieve, store

        self._bm25, self._chunk, self._embed = bm25, chunk, embed
        self._ingest, self._retrieve, self._store = ingest, retrieve, store
        self.min_score = min_score
        # Her build_index.py indexes every file in this folder, so remove()
        # deletes the file here too, or a rebuild would bring it back.
        self.data_dir = Path(data_dir) if data_dir is not None else ingest.DATA_DIR

        if store_dir is not None:
            # Her modules read these globals on every call, so this redirects
            # both indexes (used by tests to keep off the real store).
            store_dir = Path(store_dir)
            store.STORE_DIR = store_dir
            bm25.BM25_INDEX_PATH = store_dir / "bm25_corpus.json"
            bm25._bm25, bm25._records = None, []

        # Load the reranker now rather than on the first question. Without it her
        # pipeline mixes BM25 and cosine scores, so no single cutoff would work.
        try:
            reranker = retrieve.get_reranker()
        except Exception as e:  # noqa: BLE001 - surfaced in the app's status line
            raise RuntimeError(f"Reranker '{retrieve.RERANKER_MODEL}' failed to load: {e}") from e
        self._needs_sigmoid = _reranker_returns_logits(reranker)

        # Stores built before BM25 existed (or copied without it) get it rebuilt.
        if self.list_documents() and not bm25.BM25_INDEX_PATH.exists():
            log.info("BM25 index missing; rebuilding it from the vector store")
            self._rebuild_bm25()

    def ingest(self, paths: list[Path]) -> int:
        collection = self._store.get_collection()
        added = 0
        processed = False
        for path in paths:
            path = Path(path)
            loader = self._ingest.load_pptx if path.suffix.lower() == ".pptx" else self._ingest.load_pdf
            pages = loader(path)
            # Re-uploading a file replaces its chunks instead of colliding on ids.
            collection.delete(where={"source": path.name})
            processed = True
            chunks = self._chunk.chunk_pages(pages)  # also strips prompt-injection lines
            if not chunks:
                continue
            warnings = {(c.page, c.warning) for c in chunks if c.suspicious}
            for page, warning in sorted(warnings):
                log.warning("%s (%s): %s", path.name, _location(path.name, page), warning)
            self._store.add_chunks(chunks, self._embed.embed([c.text for c in chunks]))
            added += len(chunks)
        if processed:
            self._rebuild_bm25()
        return added

    def retrieve(self, query: str, k: int) -> list[Chunk]:
        if not query.strip() or not self.list_documents():
            return []
        out = []
        for i, h in enumerate(self._retrieve.retrieve(query, k)):
            score = _sigmoid(h["score"]) if self._needs_sigmoid else h["score"]
            if score < self.min_score:
                continue
            location = _location(h["source"], h["page"])
            out.append(Chunk(id=f"{h['source']}:{location}:{i}", text=h["text"],
                             source_file=h["source"], location=location, score=round(score, 4)))
        return out

    def remove(self, source_file: str) -> int:
        """Forget a file: drop its chunks from both indexes and delete its copy in
        the pipeline's data folder. Return the number of chunks removed.

        Not part of the Retriever interface yet, because the stubs don't have it."""
        removed = self.list_documents().get(source_file, 0)
        self._store.get_collection().delete(where={"source": source_file})
        self._rebuild_bm25()
        delete_stored_copy(self.data_dir, source_file)
        return removed

    def list_documents(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for meta in self._store.get_collection().get(include=["metadatas"])["metadatas"]:
            counts[meta["source"]] = counts.get(meta["source"], 0) + 1
        return counts

    def _rebuild_bm25(self) -> None:
        """Rewrite the BM25 keyword index from everything in the vector store."""
        data = self._store.get_collection().get(include=["documents", "metadatas"])
        if not data["ids"]:
            self._bm25.reset_index()
            return
        records = [
            SimpleNamespace(id=chunk_id, text=text, source=meta["source"], page=meta["page"],
                            original_text=meta.get("original_text", text),
                            suspicious=bool(meta.get("suspicious", False)),
                            warning=meta.get("warning") or None)
            for chunk_id, text, meta in zip(data["ids"], data["documents"], data["metadatas"])
        ]
        self._bm25.build_index(records)


def create_retriever() -> Retriever:
    return ChromaRetriever()

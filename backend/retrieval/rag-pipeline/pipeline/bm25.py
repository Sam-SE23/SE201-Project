"""Persisted BM25 corpus used for hybrid keyword retrieval."""

import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from config import BM25_INDEX_PATH

_bm25 = None
_records: list[dict] = []


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def build_index(chunks) -> None:
    payload = [
        {
            "id": chunk.id,
            "text": chunk.text,
            "original_text": chunk.original_text,
            "source": chunk.source,
            "page": chunk.page,
            "suspicious": chunk.suspicious,
            "warning": chunk.warning,
        }
        for chunk in chunks
    ]
    BM25_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    BM25_INDEX_PATH.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    _load_index()


def reset_index() -> None:
    global _bm25, _records
    _bm25 = None
    _records = []
    if BM25_INDEX_PATH.exists():
        BM25_INDEX_PATH.unlink()


def _load_index() -> None:
    global _bm25, _records
    if not BM25_INDEX_PATH.exists():
        raise FileNotFoundError(
            f"BM25 index not found at {BM25_INDEX_PATH}; run build_index.py first"
        )
    _records = json.loads(BM25_INDEX_PATH.read_text(encoding="utf-8"))
    _bm25 = BM25Okapi([_tokenize(record["text"]) for record in _records])


def search(query: str, limit: int) -> list[dict]:
    if _bm25 is None:
        _load_index()
    if not _records:
        return []
    scores = _bm25.get_scores(_tokenize(query))
    ranked = sorted(
        enumerate(scores),
        key=lambda item: float(item[1]),
        reverse=True,
    )
    return [
        {**_records[index], "score": round(float(score), 4)}
        for index, score in ranked[:limit]
    ]

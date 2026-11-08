"""
Step 5: Retrieval.

This is THE function Member 2 builds against. Keep its signature and
return shape stable, if it needs to change, let Sam know.
"""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import (
    DEFAULT_TOP_K,
    RERANKER_FALLBACK_TO_EMBEDDING,
    RERANKER_MODEL,
    RERANK_CANDIDATES,
    BM25_CANDIDATES,
    RRF_K,
)
from pipeline.embed import embed
from pipeline.store import get_collection
from pipeline.bm25 import search as bm25_search

_reranker = None


def get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        print(f"[retrieve] loading reranker: {RERANKER_MODEL} (first call only)")
        _reranker = CrossEncoder(RERANKER_MODEL)
    return _reranker


def retrieve(query: str, k: int = DEFAULT_TOP_K) -> list[dict]:
    """
    Embed `query`, run similarity search against the vector store, and
    return the top-k chunks ranked by relevance.

    Returns a list of dicts shaped like:
        {
            "text": str,        # the chunk's text
            "source": str,      # filename it came from
            "page": int,        # page/slide number
            "score": float,     # final ranking score (higher = more relevant)
        }
    """
    collection = get_collection()
    query_vector = embed([query])[0]

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=max(k, RERANK_CANDIDATES),
    )

    if not results["documents"] or not results["documents"][0]:
        return []

    vector_hits = {}
    for chunk_id, doc, meta, distance in zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # Chroma returns cosine *distance*; convert it to an initial ranking
        # score before the cross-encoder reranks the candidates.
        score = 1 - distance
        vector_hits[chunk_id] = {
            "id": chunk_id,
            "text": doc,
            "source": meta["source"],
            "page": meta["page"],
            "score": round(score, 4),
        }

    keyword_hits = bm25_search(query, BM25_CANDIDATES)
    keyword_by_id = {hit["id"]: hit for hit in keyword_hits}
    vector_ranks = {
        chunk_id: rank for rank, chunk_id in enumerate(vector_hits, start=1)
    }
    keyword_ranks = {
        hit["id"]: rank for rank, hit in enumerate(keyword_hits, start=1)
    }
    candidate_ids = set(vector_hits) | set(keyword_by_id)
    fused = []
    for chunk_id in candidate_ids:
        rrf_score = 0.0
        if chunk_id in vector_ranks:
            rrf_score += 1 / (RRF_K + vector_ranks[chunk_id])
        if chunk_id in keyword_ranks:
            rrf_score += 1 / (RRF_K + keyword_ranks[chunk_id])
        hit = (
            vector_hits[chunk_id]
            if chunk_id in vector_hits
            else keyword_by_id[chunk_id]
        ).copy()
        hit["rrf_score"] = rrf_score
        fused.append(hit)
    out = sorted(fused, key=lambda hit: hit["rrf_score"], reverse=True)

    try:
        reranker = get_reranker()
        rerank_scores = reranker.predict([(query, hit["text"]) for hit in out])
        ranked = sorted(
            zip(rerank_scores, out),
            key=lambda item: float(item[0]),
            reverse=True,
        )
        for rerank_score, hit in ranked:
            hit["score"] = round(float(rerank_score), 4)
        return [_public_hit(hit) for _, hit in ranked[:k]]
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        if not RERANKER_FALLBACK_TO_EMBEDDING:
            raise RuntimeError(
                f"Unable to load or run reranker '{RERANKER_MODEL}'"
            ) from error
        print(
            f"[retrieve] WARNING: reranker unavailable; "
            f"using fused BM25/vector ranking: {error}"
        )
        return [_public_hit(hit) for hit in out[:k]]


def _public_hit(hit: dict) -> dict:
    return {
        "text": hit["text"],
        "source": hit["source"],
        "page": hit["page"],
        "score": hit["score"],
    }


if __name__ == "__main__":
    import json
    query = input("Query: ").strip() or "What is this document about?"
    hits = retrieve(query)
    print(json.dumps(hits, indent=2))
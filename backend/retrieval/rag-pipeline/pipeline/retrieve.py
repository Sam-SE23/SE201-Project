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
)
from pipeline.embed import embed
from pipeline.store import get_collection

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

    out = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # Chroma returns cosine *distance*; convert it to an initial ranking
        # score before the cross-encoder reranks the candidates.
        score = 1 - distance
        out.append({
            "text": doc,
            "source": meta["source"],
            "page": meta["page"],
            "score": round(score, 4),
        })

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
        return [hit for _, hit in ranked[:k]]
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        if not RERANKER_FALLBACK_TO_EMBEDDING:
            raise RuntimeError(
                f"Unable to load or run reranker '{RERANKER_MODEL}'"
            ) from error
        print(
            f"[retrieve] WARNING: reranker unavailable; "
            f"using embedding ranking: {error}"
        )
        return out[:k]


if __name__ == "__main__":
    import json
    query = input("Query: ").strip() or "What is this document about?"
    hits = retrieve(query)
    print(json.dumps(hits, indent=2))
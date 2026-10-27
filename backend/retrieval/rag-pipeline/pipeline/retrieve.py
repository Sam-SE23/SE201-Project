"""
Step 5: Retrieval.

This is THE function Member 2 builds against. Keep its signature and
return shape stable, if it needs to change, let Sam know.
"""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import DEFAULT_TOP_K
from pipeline.embed import embed
from pipeline.store import get_collection


def retrieve(query: str, k: int = DEFAULT_TOP_K) -> list[dict]:
    """
    Embed `query`, run similarity search against the vector store, and
    return the top-k chunks ranked by relevance.

    Returns a list of dicts shaped like:
        {
            "text": str,        # the chunk's text
            "source": str,      # filename it came from
            "page": int,        # page/slide number
            "score": float,     # similarity score (higher = more relevant)
        }
    """
    collection = get_collection()
    query_vector = embed([query])[0]

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=k,
    )

    if not results["documents"] or not results["documents"][0]:
        return []

    out = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # Chroma returns cosine *distance*; convert to a similarity score
        # (higher = better) so downstream code doesn't have to think about it.
        score = 1 - distance
        out.append({
            "text": doc,
            "source": meta["source"],
            "page": meta["page"],
            "score": round(score, 4),
        })
    return out


if __name__ == "__main__":
    import json
    query = input("Query: ").strip() or "What is this document about?"
    hits = retrieve(query, k=5)
    print(json.dumps(hits, indent=2))
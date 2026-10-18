"""
Step 3: Embedding.

Turns text into vectors using a pretrained sentence-embedding model.
No training involved. Model loads once and is reused for every call
(loading it per-call causes slowdown D: ).
"""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import EMBEDDING_MODEL

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print(f"[embed] loading model: {EMBEDDING_MODEL} (first call only)")
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of strings. Returns one vector per input string."""
    model = get_model()
    vectors = model.encode(texts, show_progress_bar=len(texts) > 20, normalize_embeddings=True)
    return vectors.tolist()


if __name__ == "__main__":
    sample = ["What is retrieval-augmented generation?", "RAG combines retrieval with generation."]
    vecs = embed(sample)
    print(f"[embed] got {len(vecs)} vectors of dimension {len(vecs[0])}")
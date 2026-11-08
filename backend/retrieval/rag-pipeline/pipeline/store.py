"""
Step 4: Vector store.

Thin wrapper around Chroma so the rest of the codebase never touches
the Chroma API directly.
"""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import STORE_DIR, COLLECTION_NAME

import chromadb


def get_collection():
    client = chromadb.PersistentClient(path=str(STORE_DIR))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def add_chunks(chunks, embeddings):
    """chunks: list[Chunk] (see pipeline/chunk.py), embeddings: list[list[float]]"""
    collection = get_collection()
    collection.add(
        ids=[c.id for c in chunks],
        embeddings=embeddings,
        documents=[c.text for c in chunks],
        metadatas=[{"source": c.source, "page": c.page} for c in chunks],
    )
    return collection


def reset_collection():
    """Wipe the store -- useful when you change chunking/embedding and want
    to rebuild from scratch rather than accumulating duplicates."""
    client = chromadb.PersistentClient(path=str(STORE_DIR))
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"[store] deleted existing collection '{COLLECTION_NAME}'")
    except Exception:
        pass  # didn't exist yet, nothing to delete
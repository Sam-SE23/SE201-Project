"""
Central config for the ingestion/retrieval pipeline.
Keep every tunable knob here so chunk-size/top-k experiments are one-line changes.
"""

from pathlib import Path

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"            # drop raw PDFs/PPTX here
STORE_DIR = PROJECT_ROOT / "store"           # chroma persists its DB here
BM25_INDEX_PATH = STORE_DIR / "bm25_corpus.json"
COLLECTION_NAME = "course_docs"

# --- Chunking ---
CHUNK_SIZE = 800          # characters per chunk
CHUNK_OVERLAP = 120        # ~15% overlap

# --- Embedding model ---
# Local English retrieval model; compare against all-MiniLM on the evaluation set.
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# --- Retrieval ---
DEFAULT_TOP_K = 5
RERANK_CANDIDATES = 50
BM25_CANDIDATES = 50
RRF_K = 60
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANKER_FALLBACK_TO_EMBEDDING = True
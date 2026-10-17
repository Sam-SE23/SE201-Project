"""
Central config for the ingestion/retrieval pipeline.
Keep every tunable knob here so chunk-size/top-k experiments are one-line changes.
"""

from pathlib import Path

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"            # drop raw PDFs/PPTX here
STORE_DIR = PROJECT_ROOT / "store"           # chroma persists its DB here
COLLECTION_NAME = "course_docs"

# --- Chunking ---
CHUNK_SIZE = 800          # characters per chunk (start here, tune later)
CHUNK_OVERLAP = 120        # ~15% overlap

# --- Embedding model ---
# Local, free, no API key needed. May switch to bge-small-en-v1.5
# for later iterations.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# --- Retrieval ---
DEFAULT_TOP_K = 5
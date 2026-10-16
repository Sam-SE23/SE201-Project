"""Settings, read from environment variables (or a .env file at the repo root)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = Path(os.getenv("STUDY_BUDDY_DATA_DIR", ROOT / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
LOG_PATH = DATA_DIR / "logs" / "ai_log.jsonl"

# "stub" or "real" per component. "real" loads the teammate's module and
# falls back to the stub (with a warning in the UI) if it is not ready yet.
BACKENDS = {
    "llm": os.getenv("STUDY_BUDDY_LLM", "stub"),
    "retriever": os.getenv("STUDY_BUDDY_RETRIEVER", "stub"),
    "qa": os.getenv("STUDY_BUDDY_QA", "stub"),
    "quiz": os.getenv("STUDY_BUDDY_QUIZ", "stub"),
}

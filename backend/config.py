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

# Real LLM (backend/llm), called through LiteLLM. The model string picks the
# provider: "ollama_chat/<tag>" for a local Ollama model, or "<provider>/<model>"
# for a hosted one (e.g. "anthropic/claude-sonnet-5-5", "gemini/<model>").
LLM_MODEL = os.getenv("STUDY_BUDDY_LLM_MODEL", "")
# API key for a hosted model, whichever the provider. If empty, LiteLLM falls
# back to the provider's own variable (e.g. ANTHROPIC_API_KEY). Ollama needs none.
LLM_API_KEY = os.getenv("STUDY_BUDDY_LLM_API_KEY", "")
# Ollama's default context window is small and silently drops the start of long
# prompts, which is where the grounding rules are, so set it explicitly.
LLM_NUM_CTX = int(os.getenv("STUDY_BUDDY_LLM_NUM_CTX", "8192"))
LLM_TIMEOUT = float(os.getenv("STUDY_BUDDY_LLM_TIMEOUT", "120"))
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://127.0.0.1:11434")

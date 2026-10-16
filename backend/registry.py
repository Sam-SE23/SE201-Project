"""Builds the components, choosing the real module or the stub for each.

Each real package exposes one factory function:

    backend.llm        create_llm() -> LLMClient
    backend.retrieval  create_retriever() -> Retriever
    backend.qa         create_qa_engine(llm) -> QAEngine
    backend.quiz       create_quiz_engine(llm) -> QuizEngine

Set e.g. STUDY_BUDDY_RETRIEVER=real in .env to use it.
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field

from backend import config
from backend.interfaces import LLMClient, QAEngine, QuizEngine, Retriever
from backend.stubs import FakeLLM, FakeQA, FakeQuiz, FakeRetriever

log = logging.getLogger(__name__)


@dataclass
class Components:
    llm: LLMClient
    retriever: Retriever
    qa: QAEngine
    quiz: QuizEngine
    status: dict[str, str] = field(default_factory=dict)   # name -> "stub" / "real"
    warnings: list[str] = field(default_factory=list)


def _load(name: str, module: str, factory: str, stub, *args):
    """Return (component, status, warning or None)."""
    if config.BACKENDS[name] != "real":
        return stub(), "stub", None
    try:
        component = getattr(importlib.import_module(module), factory)(*args)
        return component, "real", None
    except Exception as e:  # noqa: BLE001 - any failure falls back to the stub
        msg = f"{name}: real module failed to load ({type(e).__name__}: {e}); using stub"
        log.warning(msg)
        return stub(), "stub", msg


def build() -> Components:
    status, warnings = {}, []

    def load(name, module, factory, stub, *args):
        component, status[name], warning = _load(name, module, factory, stub, *args)
        if warning:
            warnings.append(warning)
        return component

    llm = load("llm", "backend.llm", "create_llm", FakeLLM)
    retriever = load("retriever", "backend.retrieval", "create_retriever", FakeRetriever)
    qa = load("qa", "backend.qa", "create_qa_engine", FakeQA, llm)
    quiz = load("quiz", "backend.quiz", "create_quiz_engine", FakeQuiz, llm)
    return Components(llm, retriever, qa, quiz, status, warnings)

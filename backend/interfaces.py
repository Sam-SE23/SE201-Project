"""Team contract for AI Study Buddy.

Every component the orchestrator uses is described here as a dataclass (data
passed around) or a Protocol (behaviour a module must provide). To plug in a
real implementation, write a class with the same method signatures. No
inheritance is needed, because Protocols use structural typing.

Owners:
    Retriever  - Lichelle (ingestion, chunking, embeddings, vector store)
    QAEngine   - Guru (grounded answer generation + citations)
    QuizEngine - Sheen Hern (quiz generation, grading, weak topics)
    LLMClient  - shared; provider (Claude / GPT) still to be decided
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    """A piece of text from an ingested document."""
    id: str
    text: str
    source_file: str          # file name, e.g. "week3_slides.pptx"
    location: str             # human-readable, e.g. "p.3" or "slide 7"
    score: float | None = None  # retrieval similarity, higher = more relevant


@dataclass
class Citation:
    """A pointer from an answer back to the source material."""
    source_file: str
    location: str
    quote: str                # the supporting text from the source


@dataclass
class Answer:
    """Result of a grounded Q&A call."""
    text: str
    citations: list[Citation] = field(default_factory=list)
    chunks_used: list[Chunk] = field(default_factory=list)
    grounded: bool = True     # False = the material does not answer the question


@dataclass
class QuizQuestion:
    id: str
    topic: str
    question: str
    answer_key: str
    source: Citation
    choices: list[str] | None = None  # None = free-text answer


@dataclass
class Grade:
    question_id: str
    correct: bool
    feedback: str
    score: float = 0.0        # 0.0 - 1.0, allows partial credit


@dataclass
class ChatTurn:
    """One message in the Q&A conversation history."""
    role: str                 # "user" or "assistant"
    content: str


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------

@runtime_checkable
class Retriever(Protocol):
    def ingest(self, paths: list[Path]) -> int:
        """Parse, chunk and index the files. Return the number of chunks added."""
        ...

    def retrieve(self, query: str, k: int) -> list[Chunk]:
        """Return the k most relevant chunks for the query, best first."""
        ...

    def list_documents(self) -> dict[str, int]:
        """Return {file name: chunk count} for everything ingested so far."""
        ...


@runtime_checkable
class QAEngine(Protocol):
    def answer(self, question: str, retriever: Retriever,
               history: list[ChatTurn]) -> Answer:
        """Answer using only retrieved material.

        The retriever is passed in as a tool, so the engine decides when
        and what to retrieve.
        """
        ...


@runtime_checkable
class QuizEngine(Protocol):
    def generate(self, topic: str, n: int, retriever: Retriever) -> list[QuizQuestion]:
        """Generate n questions on the topic, grounded in retrieved material."""
        ...

    def grade(self, question: QuizQuestion, user_answer: str) -> Grade:
        ...

    def weak_topics(self, questions: list[QuizQuestion], grades: list[Grade]) -> list[str]:
        """Return topics the student should review, based on their grades."""
        ...


@runtime_checkable
class LLMClient(Protocol):
    model_name: str

    def complete(self, system: str, messages: list[ChatTurn],
                 tools: list[dict] | None = None) -> str:
        """Provider-agnostic text completion. Swap Claude/GPT in behind this."""
        ...

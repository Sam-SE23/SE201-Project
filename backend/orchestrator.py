"""The single entry point the frontend calls.

Each public method maps to one user action in the UI. Component errors are
caught here and turned into friendly messages, so the UI never shows a stack trace.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from backend import config, registry
from backend.baseline.ctrl_f import CtrlFBaseline, Hit
from backend.disclosure_log import DisclosureLog
from backend.interfaces import Answer, ChatTurn, Citation, Grade, QuizQuestion

log = logging.getLogger(__name__)

SUPPORTED = {".pdf", ".pptx"}


@dataclass
class UploadResult:
    ok: bool
    message: str
    documents: dict[str, int]


@dataclass
class QuizSession:
    topic: str
    questions: list[QuizQuestion]
    grades: list[Grade] = field(default_factory=list)

    @property
    def index(self) -> int:
        return len(self.grades)

    @property
    def current(self) -> QuizQuestion | None:
        return self.questions[self.index] if self.index < len(self.questions) else None

    @property
    def finished(self) -> bool:
        return self.index >= len(self.questions)


@dataclass
class QuizSummary:
    correct: int
    total: int
    weak_topics: list[str]
    review: list[Citation]    # sources behind the questions the student missed


class Orchestrator:
    def __init__(self, components: registry.Components | None = None,
                 upload_dir: Path = config.UPLOAD_DIR,
                 log_path: Path = config.LOG_PATH) -> None:
        c = components or registry.build()
        self.llm, self.retriever, self.qa, self.quiz = c.llm, c.retriever, c.qa, c.quiz
        self.status = c.status
        self.warnings = c.warnings
        self.baseline = CtrlFBaseline()
        self.log = DisclosureLog(log_path)
        self.upload_dir = upload_dir

    # -- documents ---------------------------------------------------------

    def upload(self, paths: list[Path]) -> UploadResult:
        paths = [Path(p) for p in paths]
        bad = [p.name for p in paths if p.suffix.lower() not in SUPPORTED]
        good = [p for p in paths if p.suffix.lower() in SUPPORTED]
        if not good:
            return UploadResult(False, "Please upload PDF or PPTX files.", self.documents())

        self.upload_dir.mkdir(parents=True, exist_ok=True)
        stored = []
        for p in good:
            dest = self.upload_dir / p.name
            if p.resolve() != dest.resolve():
                shutil.copy(p, dest)
            stored.append(dest)

        try:
            added = self.retriever.ingest(stored)
            self.baseline.index(stored)
        except Exception as e:  # noqa: BLE001
            log.exception("ingest failed")
            return UploadResult(False, f"Couldn't process the files: {e}", self.documents())

        msg = f"Ingested {len(stored)} file(s), {added} chunks."
        if bad:
            msg += f" Skipped unsupported: {', '.join(bad)}."
        return UploadResult(True, msg, self.documents())

    def documents(self) -> dict[str, int]:
        return self.retriever.list_documents()

    # -- Q&A -----------------------------------------------------------------

    def ask(self, question: str, history: list[ChatTurn]) -> Answer:
        question = question.strip()
        if not question:
            return Answer("Please type a question.", grounded=False)
        if not self.documents():
            return Answer("Upload some course materials in the **Documents** tab first.",
                          grounded=False)
        try:
            answer = self.qa.answer(question, self.retriever, history)
        except Exception as e:  # noqa: BLE001
            log.exception("qa failed")
            return Answer(f"Something went wrong while answering: {e}", grounded=False)

        self.log.record("qa", self._backend(), question=question,
                        chunks_retrieved=[c.id for c in answer.chunks_used],
                        answer=answer.text, citations=answer.citations,
                        grounded=answer.grounded)
        return answer

    def ctrl_f(self, keyword: str) -> list[Hit]:
        return self.baseline.search(keyword)

    # -- quiz ----------------------------------------------------------------

    def start_quiz(self, topic: str, n: int) -> tuple[QuizSession | None, str]:
        topic = topic.strip()
        if not topic:
            return None, "Enter a topic for the quiz."
        if not self.documents():
            return None, "Upload some course materials in the **Documents** tab first."
        try:
            questions = self.quiz.generate(topic, n, self.retriever)
        except Exception as e:  # noqa: BLE001
            log.exception("quiz generation failed")
            return None, f"Couldn't generate a quiz: {e}"
        if not questions:
            return None, f"Couldn't find enough material about **{topic}** to make a quiz."

        self.log.record("quiz_generate", self._backend(), topic=topic, requested=n,
                        questions=questions)
        msg = f"Generated {len(questions)} question(s) on **{topic}**."
        if len(questions) < n:
            msg += f" (Asked for {n}; the material only supported {len(questions)}.)"
        return QuizSession(topic, questions), msg

    def submit_answer(self, session: QuizSession, user_answer: str) -> Grade:
        question = session.current
        if question is None:
            raise ValueError("Quiz is already finished")
        try:
            grade = self.quiz.grade(question, user_answer)
        except Exception as e:  # noqa: BLE001
            log.exception("grading failed")
            grade = Grade(question.id, False, f"Couldn't grade this answer: {e}")
        session.grades.append(grade)
        self.log.record("quiz_grade", self._backend(), question=question.question,
                        user_answer=user_answer, grade=grade)
        return grade

    def quiz_summary(self, session: QuizSession) -> QuizSummary:
        graded = session.questions[:len(session.grades)]
        try:
            weak = self.quiz.weak_topics(graded, session.grades)
        except Exception:  # noqa: BLE001
            log.exception("weak_topics failed")
            weak = []
        review = [q.source for q, g in zip(graded, session.grades) if not g.correct]
        correct = sum(g.correct for g in session.grades)
        return QuizSummary(correct, len(session.grades), weak, review)

    # -- misc ----------------------------------------------------------------

    def _backend(self) -> dict[str, str]:
        return {**self.status, "model": getattr(self.llm, "model_name", "unknown")}

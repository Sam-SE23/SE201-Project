"""Stub quiz engine: fill-in-the-blank questions built from retrieved sentences."""

from __future__ import annotations

import re

from backend.interfaces import Citation, Grade, QuizQuestion, Retriever

BLANK = "_____"


class FakeQuiz:
    def generate(self, topic: str, n: int, retriever: Retriever) -> list[QuizQuestion]:
        questions: list[QuizQuestion] = []
        for chunk in retriever.retrieve(topic, n * 3):
            for sentence in re.split(r"(?<=[.!?])\s+|\n", chunk.text):
                q = _blank_out(sentence)
                if q is None:
                    continue
                prompt, answer = q
                questions.append(QuizQuestion(
                    id=f"q{len(questions) + 1}",
                    topic=topic,
                    question=f"Fill in the blank: {prompt}",
                    answer_key=answer,
                    source=Citation(chunk.source_file, chunk.location, sentence.strip()),
                ))
                break  # at most one question per chunk, for variety
            if len(questions) == n:
                break
        return questions

    def grade(self, question: QuizQuestion, user_answer: str) -> Grade:
        correct = user_answer.strip().lower() == question.answer_key.lower()
        feedback = ("Correct!" if correct
                    else f"Not quite. The answer is **{question.answer_key}**.")
        return Grade(question.id, correct, feedback, 1.0 if correct else 0.0)

    def weak_topics(self, questions: list[QuizQuestion], grades: list[Grade]) -> list[str]:
        by_topic: dict[str, list[float]] = {}
        topic_of = {q.id: q.topic for q in questions}
        for g in grades:
            by_topic.setdefault(topic_of[g.question_id], []).append(g.score)
        return [t for t, scores in by_topic.items() if sum(scores) / len(scores) < 0.5]


def _blank_out(sentence: str) -> tuple[str, str] | None:
    """Blank the longest word in a reasonably long sentence."""
    sentence = " ".join(sentence.split())
    words = sentence.split()
    if len(words) < 6:
        return None
    candidates = [w.strip(".,;:()\"'") for w in words]
    candidates = [w for w in candidates if w.isalpha() and len(w) >= 5]
    if not candidates:
        return None
    answer = max(candidates, key=len)
    return sentence.replace(answer, BLANK, 1), answer

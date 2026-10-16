"""Turns backend objects into Markdown for display. No Gradio imports here."""

from __future__ import annotations

from backend.baseline.ctrl_f import Hit
from backend.interfaces import Answer, Citation, Grade, QuizQuestion
from backend.orchestrator import QuizSession, QuizSummary

QUOTE_CHARS = 400
MAX_HITS = 20


def status_line(status: dict[str, str], warnings: list[str]) -> str:
    parts = " · ".join(f"{name}: `{mode}`" for name, mode in status.items())
    text = f"<sub>Components: {parts}</sub>"
    for w in warnings:
        text += f"\n\n⚠️ <sub>{w}</sub>"
    return text


def answer_markdown(answer: Answer) -> str:
    if answer.grounded:
        return answer.text
    return f"🔍 **Not found in your materials**\n\n{answer.text}"


def _quote(text: str) -> str:
    text = " ".join(text.split())
    if len(text) > QUOTE_CHARS:
        text = text[:QUOTE_CHARS].rsplit(" ", 1)[0] + "…"
    return text


def citation_line(c: Citation) -> str:
    return f"**{c.source_file}**, {c.location}"


def sources_markdown(citations: list[Citation]) -> str:
    if not citations:
        return "_No sources were cited for the last answer._"
    blocks = [f"**[{i}]** {citation_line(c)}\n> {_quote(c.quote)}"
              for i, c in enumerate(citations, start=1)]
    return "\n\n".join(blocks)


def hits_markdown(keyword: str, hits: list[Hit]) -> str:
    keyword = keyword.strip()
    if not keyword:
        return "_Type a keyword to search the raw text._"
    if not hits:
        return (f"**0 exact matches** for `{keyword}`.\n\n"
                "_Ctrl+F only finds exact wording. Try a shorter keyword._")
    files = len({h.source_file for h in hits})
    lines = [f"**{len(hits)} match(es)** for `{keyword}` across {files} file(s):"]
    for h in hits[:MAX_HITS]:
        lines.append(f"- **{h.source_file}**, {h.location}: {h.snippet}")
    if len(hits) > MAX_HITS:
        lines.append(f"- _…and {len(hits) - MAX_HITS} more_")
    return "\n".join(lines)


def documents_rows(documents: dict[str, int]) -> list[list]:
    return [[name, count] for name, count in sorted(documents.items())]


def quiz_progress(session: QuizSession) -> str:
    return f"**Question {session.index + 1} of {len(session.questions)}** · topic: _{session.topic}_"


def quiz_question(q: QuizQuestion) -> str:
    text = f"### {q.question}"
    if q.choices:
        text += "\n\n" + "\n".join(f"- {c}" for c in q.choices)
    return text


def quiz_feedback(grade: Grade, q: QuizQuestion) -> str:
    icon = "✅" if grade.correct else "❌"
    return (f"{icon} {grade.feedback}\n\n"
            f"<sub>Source: {citation_line(q.source)}</sub>\n> {_quote(q.source.quote)}")


def quiz_summary(summary: QuizSummary) -> str:
    pct = round(100 * summary.correct / summary.total) if summary.total else 0
    text = f"## Score: {summary.correct} / {summary.total} ({pct}%)"
    if summary.weak_topics:
        topics = ", ".join(f"**{t}**" for t in summary.weak_topics)
        text += f"\n\n📌 **Weak topics to review:** {topics}"
    if summary.review:
        text += "\n\n**Revisit these sections** (or ask about them in the Ask tab):\n"
        text += "\n".join(f"- {citation_line(c)}" for c in summary.review)
    elif summary.total:
        text += "\n\n🎉 No missed questions. Nice work!"
    return text

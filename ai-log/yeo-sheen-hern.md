# AI Use Log for Yeo Sheen Hern

## 2026-11-08 · Grounded quiz mode

- **Tool (model)** — Codex (GPT-6)
- **Files** — `backend/quiz/__init__.py`, `backend/registry.py`, `frontend/components.py`, `frontend/formatting.py`, `tests/test_quiz.py`, `tests/test_orchestrator.py`, `README.md`, `.env.example`
- **Outcome** — Implemented the quiz engine and connected it to the existing Quiz tab.

### What I asked for

Set up the project, identify the work required to finish quiz mode, and implement it on a feature branch. The agreed scope included source-backed multiple-choice questions, deterministic grading, and review by concept.

### How it was checked

All 38 pytest cases passed. A Gradio smoke test uploaded a sample PDF, retrieved passages with Chroma, and completed a multiple-choice quiz using scripted model output. It checked blank and duplicate submissions, feedback citations, and the weak-topic summary. A separate run exercised the fill-in-the-blank demo.

### Decisions

The engine accepts a question when its quoted excerpt occurs in the cited passage and includes the correct option. Concepts with a missed question appear in the results. A real shared LLM adapter and credentials are still needed to test live generation.

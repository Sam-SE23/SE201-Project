# AI Study Buddy (SE201 G1 Team 7)

Upload your course materials (PDF / PPTX). You can then ask questions that are answered **only from those materials, with citations**, and quiz yourself to find weak topics. A plain **Ctrl+F baseline** sits alongside for comparison.

| Member | Area |
|---|---|
| Lichelle Weasley | Ingestion & retrieval (`backend/retrieval/`) |
| Gurunathan Sampravinraj | Grounded Q&A (`backend/qa/`) |
| Yeo Sheen Hern | Quiz mode (`backend/quiz/`) |
| Darrion Ong Wei Zhi | UI, orchestration, Ctrl+F baseline, AI log (`frontend/`, `backend/orchestrator.py`) |

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional; defaults to all stubs
```

## Run

From the repo root:

```bash
python -m frontend.app
```

Then open http://127.0.0.1:7860.

| Tab | What it does |
|---|---|
| 📄 Documents | Upload and ingest PDF/PPTX files |
| 💬 Ask | Grounded Q&A with numbered citations and a sources panel. The Ctrl+F baseline runs side by side. |
| 📝 Quiz | Generate a quiz on a topic, answer it, get graded, and see weak topics |
| 🧾 AI Log | Every AI interaction, recorded to `data/logs/ai_log.jsonl` |

## Tests

```bash
pytest
```

## Architecture

```
frontend/  (Gradio UI, presentation only)
   │  calls only
   ▼
backend/orchestrator.py ──► Retriever   (backend/retrieval/)
   │                   ──► QAEngine    (backend/qa/)
   │                   ──► QuizEngine  (backend/quiz/)
   │                   ──► LLMClient   (backend/llm/)
   ├──► backend/baseline/ctrl_f.py      (non-AI comparison)
   └──► backend/disclosure_log.py       (JSONL log of AI calls)
```

- `backend/interfaces.py` is the **team contract**. It defines the dataclasses passed between components and the method signatures each component must provide.
- Every component has a working **stub** in `backend/stubs/`, so the whole app runs end to end before the real modules exist.
- `backend/` never imports Gradio. The frontend only talks to the orchestrator.

## Plugging in a real component

1. Implement the Protocol from `backend/interfaces.py` in your package. For example, the retriever goes in `backend/retrieval/`.
2. Expose a factory function in that package's `__init__.py`:

   | Package | Factory |
   |---|---|
   | `backend/llm` | `create_llm() -> LLMClient` |
   | `backend/retrieval` | `create_retriever() -> Retriever` |
   | `backend/qa` | `create_qa_engine(llm) -> QAEngine` |
   | `backend/quiz` | `create_quiz_engine(llm) -> QuizEngine` |

3. Set the flag in `.env`, e.g. `STUDY_BUDDY_RETRIEVER=real`.
4. Restart the app. The status line under the title shows which components are `real` and which are `stub`. If your module fails to import, the app falls back to the stub and shows the error there.

Add any new dependencies (e.g. `chromadb`, `anthropic`) to `requirements.txt`.

## AI use log

Each member keeps their own log at `ai-log/<your-name>.md` (see `ai-log/darrion-ong.md` for the format). Edit only your own file, and commit each entry together with the work it describes. Runtime AI calls made by the app are logged separately, to `data/logs/ai_log.jsonl`.

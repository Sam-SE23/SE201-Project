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



# RAG Pipeline — Ingestion & Retrieval Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
cd backend/retrieval/rag-pipeline
pip install -r requirements.txt
```

## Usage

1. Drop a few real PDF/PPTX files into `data/`.
2. Build the index:
   ```bash
   python build_index.py
   ```
   Re-run with `--reset` any time you change chunking/embedding and want a clean rebuild:
   ```bash
   python build_index.py --reset
   ```
3. Sanity-check query interactively:
   ```bash
   python -m pipeline.retrieve
   ```

## Project structure

```
backend/retrieval/rag-pipeline
├── config.py              # all tunable knobs (chunk size, top-k, model names)
├── build_index.py         # run this to (re)build the vector store
├── requirements.txt
├── data/                  # drop raw PDFs/PPTX here
├── store/                 # Chroma's persisted DB (auto-created)
└── pipeline/
    ├── ingest.py           # PDF/PPTX -> RawPage (text + source + page)
    ├── chunk.py             # RawPage -> Chunk (fixed-size, overlapping)
    ├── embed.py              # text -> vectors (sentence-transformers, local)
    ├── store.py               # Chroma wrapper (add/reset)
    └── retrieve.py             # the function Member 2 calls
```

## The interface Member 2 builds against

```python
from pipeline.retrieve import retrieve

hits = retrieve("What is the refund policy?", k=5)
# -> [{"text": ..., "source": "handbook.pdf", "page": 3, "score": 0.82}, ...]
```

This function's signature or return shape will not be changed arbitrarily.

## Tuning

Everything worth tuning lives in `config.py`:
- `CHUNK_SIZE` / `CHUNK_OVERLAP` — if retrieval misses obvious answers, try
  smaller chunks (more precise) or larger ones (more context per chunk).
- `DEFAULT_TOP_K` — how many chunks get passed to the LLM. Too low misses
  context, too high adds noise and cost.
- `EMBEDDING_MODEL` — defaults to a free local model (`all-MiniLM-L6-v2`).
   May switch models when tuning it further.

## Known limitations (temporarily)

- Chunking is naive fixed-size — it can split sentences mid-thought. Fine
  as a baseline; worth noting as a limitation / future improvement.
- No reranking — results are raw cosine similarity order only.
- Scanned/image-only PDFs won't extract any text (would need OCR).

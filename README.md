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

### Current status

| Component | Real module | Notes |
|---|---|---|
| Retriever | ✅ `backend/retrieval/__init__.py` | Adapter over the Chroma pipeline in `rag-pipeline/`. The first run downloads the `BAAI/bge-small-en-v1.5` embedding model. The index lives in `backend/retrieval/rag-pipeline/store/` (git-ignored) and is shared with `build_index.py`. Hits below `MIN_SCORE` are dropped, so out-of-scope questions get no chunks. |
| QA engine | ✅ `backend/qa/` | Works, but on the stub LLM the answers are placeholders; the app shows a warning. |
| LLM | ❌ stub | Provider not chosen yet. |
| Quiz engine | ❌ stub | |

To run with real retrieval and the real QA engine, set these in `.env`:

```bash
STUDY_BUDDY_RETRIEVER=real
STUDY_BUDDY_QA=real
```

`tests/test_real_pipeline.py` covers the real retriever and QA engine through the orchestrator. It is skipped if `chromadb` or `sentence-transformers` isn't installed.

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
   Retrieval selects 50 BGE vector candidates and 50 BM25 keyword candidates,
   merges their ranks with RRF, reranks the fused candidates with the
   configured cross-encoder, and returns the best 5. If the reranker cannot
   load, it explicitly falls back to the fused ranking.
   Document text containing bounded instruction-like patterns is stripped before
   indexing. Retrieved results expose `suspicious` and `warning` metadata; the
   original source text is retained privately for audit/citation use.

   Test sanitisation:
   ```bash
   pip install pytest
   .\venv\Scripts\python.exe -m pytest tests\test_sanitize.py -q
   ```
4. Evaluate retrieval recall against labeled questions:
   ```bash
   python evaluate_retrieval.py
   ```
   Add questions and expected source pages to
   `backend/retrieval/rag-pipeline/evaluation/benchmark.json`. Recall@k passes when
   the expected source and page appear in the first `k` results.

## Project structure

```
backend/retrieval/rag-pipeline/
├── config.py              # all tunable knobs (chunk size, retrieval, model names)
├── build_index.py         # run this to (re)build the vector store
├── requirements.txt
├── data/                  # drop raw PDFs/PPTX here
├── store/                 # Chroma and BM25 persisted indexes (auto-created)
└── pipeline/
    ├── ingest.py           # PDF/PPTX -> RawPage (text + source + page)
    ├── chunk.py             # RawPage -> Chunk (fixed-size, overlapping)
    ├── embed.py              # text -> vectors (sentence-transformers, local)
    ├── retrieve.py           # candidate retrieval and cross-encoder reranking
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
Returned hits may also include `suspicious` and `warning` fields when document
sanitization detected instruction-like content. Downstream generation must treat
all retrieved text as untrusted data, even when no warning is present.

## Tuning

Everything worth tuning lives in `config.py`:
- `CHUNK_SIZE` / `CHUNK_OVERLAP` — if retrieval misses obvious answers, try
  smaller chunks (more precise) or larger ones (more context per chunk).
- `DEFAULT_TOP_K` — how many chunks get passed to the LLM. Too low misses
  context, too high adds noise and cost.
- `EMBEDDING_MODEL` — defaults to a free local model (`all-MiniLM-L6-v2`).
   May switch models when tuning it further.
- `BM25_CANDIDATES` / `RRF_K` — keyword candidate count and RRF rank constant.

Run `python build_index.py --reset` after changing documents, chunking, or
embedding settings. This rebuilds both the Chroma vector collection and the
persisted BM25 corpus.

## Known limitations (temporarily)

- Chunking is naive fixed-size — it can split sentences mid-thought. Fine
  as a baseline; worth noting as a limitation / future improvement.
- No reranking — results are raw cosine similarity order only.
- Scanned/image-only PDFs won't extract any text (would need OCR).

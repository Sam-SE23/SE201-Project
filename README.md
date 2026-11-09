# AI Study Buddy (SE201 G1 Team 7)

Upload your course materials (PDF / PPTX). You can then ask questions that are answered **only from those materials, with citations**, and quiz yourself to find weak topics. A plain **Ctrl+F baseline** sits alongside for comparison.

| Member | Area |
|---|---|
| Lichelle Weasley | Ingestion & retrieval (`backend/retrieval/`) |
| Gurunathan Sampravinraj | Grounded Q&A (`backend/qa/`) |
| Yeo Sheen Hern | Quiz mode (`backend/quiz/`) |
| Darrion Ong Wei Zhi | UI, orchestration, LLM client, Ctrl+F baseline, AI log (`frontend/`, `backend/orchestrator.py`, `backend/llm/`) |

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env
```

Then set up the LLM: see [Running the full system](#running-the-full-system).

## Run

From the repo root:

```bash
python -m frontend.app
```

Then open http://127.0.0.1:7860. The status line under the title shows the active model, and the reason if any component couldn't start.

| Tab | What it does |
|---|---|
| 📄 Documents | Upload and ingest PDF/PPTX files, or remove one |
| 💬 Ask | Grounded Q&A with numbered citations, a confidence badge and a sources panel. The Ctrl+F baseline runs side by side. |
| 📝 Quiz | Generate a multiple-choice quiz on a topic, answer it, get graded with the source, and see weak topics |
| 🧾 AI Log | Every AI interaction, recorded to `data/logs/ai_log.jsonl` |

## Running the full system

The LLM is a local [Ollama](https://ollama.com/download) model, called through LiteLLM.

1. Install Ollama, then pull a model, e.g. `ollama pull qwen3:8b`.
2. Run `ollama run qwen3:8b "hello"`. While it's loaded, check that `ollama ps` shows `100% GPU`. A CPU/GPU split means the model is too big for your VRAM, and answers will be much slower.
3. Set the model in `.env`:

   ```bash
   STUDY_BUDDY_LLM_MODEL=ollama_chat/qwen3:8b
   ```

   Keep `STUDY_BUDDY_LLM_NUM_CTX` at 16384 (the value in `.env.example`) if you generate quizzes of up to 10 questions. A quiz sends up to 30 source passages, and Ollama silently cuts the start of a prompt that doesn't fit, which drops the instructions.
4. Run `python -m frontend.app`. The status line should show the model name and no warnings.

The first run downloads the embedding model and the reranker, so the first upload and question are slower.

**Using a hosted model instead** (e.g. Claude) is a two-line change; the code stays the same:

```bash
STUDY_BUDDY_LLM_MODEL=anthropic/claude-haiku-5-5
STUDY_BUDDY_LLM_API_KEY=<your key>
```

The key setting has the same name whichever provider you use. If it's missing, the status line says to set it. A hosted model needs internet, costs per question, and sends your course material to the provider.

## Tests

```bash
pytest                  # everything except the live-model tests
pytest -m ollama        # the live-model tests; need Ollama running with STUDY_BUDDY_LLM_MODEL pulled
```

- `tests/test_real_pipeline.py` runs the real retriever and QA engine through the orchestrator, on a temporary store.
- `tests/test_llm.py` mocks LiteLLM. Its two `ollama` tests call the real model and are skipped unless Ollama is running with the model pulled.
- `tests/test_quiz.py` runs the quiz engine with scripted model responses.
- `tests/test_eval_runner.py` tests the benchmark harness, including a real-mode run with a scripted model.

### Running the benchmark

`tests/eval_runner.py` scores answer accuracy, hallucination rate, citations (including whether the answer cites the page the answer is actually on), out-of-scope fallback and academic-integrity compliance, against a Ctrl+F baseline on the same questions.

```bash
# Real system: the app's retriever and QA engine, with the model set in .env
python tests/eval_runner.py --real --docs <folder of SE201 PDF/PPTX files>
python tests/eval_runner.py --real --docs <folder> --limit 3      # quick check first

# Mock mode: scripted model over a built-in knowledge base (checks the harness only)
python tests/eval_runner.py
```

- Real mode uses `tests/eval_benchmark_se201.json`: 20 questions on the SE201 lectures and project brief (8 fact, 7 synthesis across two sources, 3 out-of-scope, 2 academic integrity), each with the pages its answer is on.
- It indexes the course files into a temporary store, so the app's own index is untouched, and writes `tests/eval_results_<model>.json`. Runs on different models (e.g. Ollama and Claude) are kept side by side.
- It stops with a clear message if no model is usable, rather than benchmarking the fallback.
- Ctrl+F searches each question's most specific word, the way a student would; the whole question as one phrase is also recorded.
- The course files are not in the repo. Put them in one folder and pass it with `--docs`.

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
- `backend/` never imports Gradio. The frontend only talks to the orchestrator.
- Retrieval runs **before** the LLM (retrieve-then-generate): the QA and quiz engines search the course materials, then send the passages to the model. The model never calls tools.

### Components

| Component | Module | Notes |
|---|---|---|
| Retriever | `backend/retrieval/__init__.py` | Adapter over the hybrid pipeline in `rag-pipeline/`: vector search (Chroma, `BAAI/bge-small-en-v1.5`) plus BM25 keyword search, merged with Reciprocal Rank Fusion and reranked by a cross-encoder (`ms-marco-MiniLM-L-6-v2`). Reranker scores are converted to 0–1 probabilities, and hits below `MIN_SCORE` are dropped, so out-of-scope questions get no passages. Both indexes live in `backend/retrieval/rag-pipeline/store/` (git-ignored) and are shared with `build_index.py`. |
| QA engine | `backend/qa/` | Guards against prompt injection, rewrites follow-up questions, answers only from the retrieved passages with inline citations, checks each citation against the passages, and shows a confidence badge. Answers "not found" when the materials don't cover the question, and gives hints rather than full solutions for graded work. |
| Quiz engine | `backend/quiz/` | Generates multiple-choice questions from the retrieved passages. A question is kept only if its quote appears word for word in the cited passage and contains the correct answer. Grades each selection, and lists the concepts with a missed question and the pages or slides to revisit. |
| LLM | `backend/llm/__init__.py` | LiteLLM client for a local Ollama model, or a hosted model with a key. If no model is set, Ollama isn't running or the model isn't pulled, the status line says so. |

**Removing a document:** select its row in the Documents tab and press Remove. After a warning, it is dropped from both indexes and from the Ctrl+F baseline, and its copies in `data/uploads/` and `rag-pipeline/data/` are deleted.

### Plugging in a different component

1. Implement the Protocol from `backend/interfaces.py` in your package.
2. Expose a factory function in that package's `__init__.py`:

   | Package | Factory |
   |---|---|
   | `backend/llm` | `create_llm() -> LLMClient` |
   | `backend/retrieval` | `create_retriever() -> Retriever` |
   | `backend/qa` | `create_qa_engine(llm) -> QAEngine` |
   | `backend/quiz` | `create_quiz_engine(llm) -> QuizEngine` |

3. Restart the app. If your module fails to load, the status line shows the error.

Add any new dependencies to `requirements.txt`.

## AI use log

Each member keeps their own log at `ai-log/<your-name>.md` (see `ai-log/darrion-ong.md` for the format). Edit only your own file, and commit each entry together with the work it describes. Runtime AI calls made by the app are logged separately, to `data/logs/ai_log.jsonl`.

---

# RAG pipeline: ingestion and retrieval

The pipeline in `backend/retrieval/rag-pipeline/` also runs on its own, without the app. Its dependencies are in the root `requirements.txt`. Run these commands from `backend/retrieval/rag-pipeline/`.

## Usage

1. Drop PDF/PPTX files into `data/`.
2. Build the index:
   ```bash
   python build_index.py
   ```
   Re-run with `--reset` after changing documents, chunking or embedding settings. This rebuilds both the Chroma collection and the BM25 corpus:
   ```bash
   python build_index.py --reset
   ```
   `--reset` only rebuilds from the files still in `data/`.
3. Try queries interactively:
   ```bash
   python -m pipeline.retrieve
   ```
   Retrieval takes 50 vector candidates and 50 BM25 candidates, merges their ranks with RRF, reranks the merged candidates with the cross-encoder, and returns the best 5. If the reranker can't load, it falls back to the merged ranking.

   Document text containing instruction-like patterns is stripped before indexing. Retrieved results carry `suspicious` and `warning` fields; the original text is kept privately for audit and citations. Test it with:
   ```bash
   python -m pytest tests/test_sanitize.py -q
   ```
4. Evaluate retrieval recall against labelled questions:
   ```bash
   python evaluate_retrieval.py
   ```
   Add questions and their expected source pages to `evaluation/benchmark.json`. Recall@k passes when the expected source and page appear in the first `k` results.

## Project structure

```
backend/retrieval/rag-pipeline/
├── config.py              # all tunable settings (chunking, retrieval, model names)
├── build_index.py         # (re)builds the Chroma and BM25 indexes from data/
├── evaluate_retrieval.py  # recall@k benchmark
├── evaluation/            # benchmark.json: labelled questions and expected pages
├── data/                  # raw PDFs/PPTX
├── store/                 # Chroma and BM25 indexes (auto-created, git-ignored)
├── tests/                 # test_sanitize.py
└── pipeline/
    ├── ingest.py          # PDF/PPTX -> RawPage (text + source + page)
    ├── sanitize.py        # strips instruction-like text before indexing
    ├── chunk.py           # RawPage -> Chunk (fixed-size, overlapping)
    ├── embed.py           # text -> vectors (sentence-transformers, local)
    ├── store.py           # Chroma wrapper
    ├── bm25.py            # BM25 keyword index
    └── retrieve.py        # hybrid retrieval, RRF and reranking
```

## Retrieval interface

```python
from pipeline.retrieve import retrieve

hits = retrieve("When is the checkpoint due?", k=5)
# -> [{"text": ..., "source": "syllabus.pdf", "page": 3, "score": 0.82}, ...]
```

The app's adapter (`backend/retrieval/__init__.py`) builds on this, so its signature and return shape stay stable. Hits may also include `suspicious` and `warning` fields when sanitisation found instruction-like content. Downstream generation must treat all retrieved text as untrusted data, even when no warning is present.

## Tuning

Everything worth tuning lives in `config.py`:
- `CHUNK_SIZE` / `CHUNK_OVERLAP` (800 / 120 characters): if retrieval misses obvious answers, try smaller chunks (more precise) or larger ones (more context per chunk).
- `DEFAULT_TOP_K` (5): how many passages go to the LLM. Too low misses context; too high adds noise and a longer prompt.
- `EMBEDDING_MODEL` (`BAAI/bge-small-en-v1.5`) and `RERANKER_MODEL` (`cross-encoder/ms-marco-MiniLM-L-6-v2`).
- `BM25_CANDIDATES` / `RERANK_CANDIDATES` / `RRF_K`: candidate counts and the RRF rank constant.

The relevance cutoff `MIN_SCORE` is in the app's adapter, `backend/retrieval/__init__.py`.

## Known limitations

- Chunking is fixed-size, so it can split a sentence mid-thought.
- Scanned or image-only PDFs give no text (they would need OCR).
- The first run downloads the embedding model and the reranker, and loads them on the first query, so the first question is slow.

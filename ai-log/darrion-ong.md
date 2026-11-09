# AI Use Log: Darrion Ong Wei Zhi

## 2026-10-16 · Chat UI and orchestration scaffold
- **Tool (model):** Claude Code (Claude Opus 5.5)
- **Files:** frontend/app.py, frontend/components.py, frontend/formatting.py, backend/interfaces.py, backend/orchestrator.py, backend/registry.py, backend/config.py, backend/disclosure_log.py, backend/baseline/ctrl_f.py, backend/stubs/, tests/, README.md, requirements.txt, .env.example, pytest.ini
- **Outcome:** Changed

### What I asked for
A plan and then an implementation for the Gradio chat UI, covering my area: UI, orchestration, the Ctrl+F baseline and the AI disclosure log. The LLM provider and my teammates' modules aren't decided yet, so I asked for those to be stubbed behind fixed interfaces. That way the app runs end to end for the checkpoint, and each teammate can swap in their own module later.

### How I checked it
Reviewed the plan before any code was written. Ran the pytest suite (14 tests, all passing). These cover Ctrl+F extraction and search on generated PDF/PPTX files, the upload → ask → quiz flow with stubs, the AI log entries, and the fallback to a stub when a real module is missing. Ran the app and drove it through the Gradio API: ingesting a PDF and a PPTX, asking an in-scope question and getting a cited answer with page locations, asking an out-of-scope question and getting the "not found" reply, and running a Ctrl+F search.

### What I kept or changed
Kept the interface-and-stub design, the orchestrator, the Ctrl+F baseline and the tab layout. Changed the folder structure during planning: the original plan had a single `study_buddy/` package, and I had it split into top-level `frontend/` and `backend/` folders.

## 2026-10-16 · Gradio Settings panel and textbox scrollbar clean-up
- **Tool (model):** Claude Code (Claude Opus 5.5)
- **Files:** frontend/app.py, frontend/components.py
- **Outcome:** Changed

### What I asked for
An explanation of the PWA and Screen Studio options in Gradio's Settings panel, and their removal. Also the removal of the scrollbars on the question, keyword, quiz topic and quiz answer textboxes and on the "Components:" status line.

### How I checked it
Confirmed from the installed Gradio source that Settings, PWA, Screen Studio and Language are built into Gradio and can't be switched off by an option, so they have to be hidden with CSS. Ran the tests (still passing) and checked that the served page includes the CSS and that all four textboxes carry the `no-scrollbar` class.

### What I kept or changed
The first proposal hid only Screen Studio. I changed that to hide Language and PWA as well, keeping only the theme switch. For the textboxes, I rejected the proposal to turn them into single-line inputs and kept them as multi-line textareas with the scrollbar hidden.

## 2026-10-25 · Connect the RAG retriever and QA engine to the orchestrator
- **Tool (model):** Claude Code (Claude Opus 5.5)
- **Files:** backend/retrieval/__init__.py, backend/registry.py, tests/test_real_pipeline.py, tests/test_orchestrator.py, requirements.txt, .gitignore, .env.example, README.md
- **Outcome:** Changed

### What I asked for
Create a plan to do the following: connect Lichelle's Chroma pipeline to the orchestrator, turn on Guru's grounded QA engine in the app, and update the tests and README. I asked for the LLM provider choice to be left out for now.

### How I checked it
Reviewed the plan before any code was written, and verified if it would modify any of Lichelle's files. Ran the pytest suite: 22 tests passing, including 7 new ones that run the real retriever and QA engine through the orchestrator on a temporary Chroma store. Loaded the app's components with STUDY_BUDDY_RETRIEVER=real and STUDY_BUDDY_QA=real and confirmed both load as real, with the stub-LLM warning shown. Queried the existing Week 1–2 lecture index to check the 0.3 relevance cutoff: lecture questions scored 0.45–0.57 and were kept, and off-topic questions scored 0.09–0.28 and were dropped.

### What I kept or changed
Kept the adapter design, which wraps Lichelle's pipeline without editing her code, and the relevance cutoff for out-of-scope questions. Put off the LLM provider as it is undecided. Kept the decision to stop tracking the Chroma store in git.

## 2026-11-09 · Rebuild the retriever adapter for the hybrid RAG pipeline
- **Tool (model):** Claude Code (Claude Opus 5.5)
- **Files:** backend/retrieval/__init__.py, tests/test_real_pipeline.py, requirements.txt, README.md
- **Outcome:** Changed

### What I asked for
An update on Lichelle's changes, then a plan for a new adapter connecting the GUI to her retrieval. Her 8 Nov merge had deleted my original adapter, and her pipeline had changed to hybrid vector + BM25 search with a cross-encoder reranker. I also asked for this desktop to be set up first: it had no Python, venv or `.env`.

### How I checked it
Reviewed the plan before any code was written. Ran the pytest suite: 31 tests passing, including 4 new ones for the BM25 index and score range. Indexed the 21 SE201 PDFs through the adapter (705 chunks, 30 s) and compared the reranker scores of the 20 benchmark questions with 7 off-topic ones. Checked the weakest questions against their expected pages. Rebuilt the same files with Lichelle's `build_index.py --reset`: her `evaluate_retrieval.py` gave the same Recall@3 55% and Recall@5 65% as the adapter-built store, which differs from her logged 60%/75% because of the larger file set. Launched the app and confirmed the status line shows the retriever as real and the documents are listed.

### What I kept or changed
Kept the original adapter's design: her pipeline code is untouched, and re-uploads replace a file's chunks. Uploads now also rebuild the BM25 index from Chroma, since her `build_index()` overwrites the whole file. Reranker scores are converted to 0–1 probabilities so Guru's confidence badge still works. The first proposed cutoff (0.5) would have dropped real course questions. I asked for 0.25, then chose 0.01 after seeing that it keeps all 20 benchmark questions while still dropping every off-topic one (all ≤ 0.0011).

## 2026-11-09 · LiteLLM client for a local Ollama model
- **Tool (model):** Claude Code (Claude Opus 5.5)
- **Files:** backend/llm/__init__.py, backend/config.py, .env.example, requirements.txt, frontend/formatting.py, frontend/app.py, tests/test_llm.py, pytest.ini, README.md
- **Outcome:** Changed

### What I asked for
A plan for the LiteLLM client code, so the app can use a real LLM instead of the stub. Installing Ollama and choosing the model were left for a later step.

### How I checked it
Reviewed the plan before any code was written. Ran the pytest suite: 46 passing at first, including 15 new LLM tests that mock LiteLLM, with the 2 real-Ollama tests skipped. Ran the client against a small fake Ollama server to capture the exact request: `num_ctx` reaches Ollama in `options`, the system prompt is sent first, and a `<think>` block is removed from the reply. That test showed each call waiting about 8 seconds, because LiteLLM looks up model details at its own default address and ignores the one passed in. After the fix, a call took 0.2 seconds. Checked the status line for both failure cases (no model set, Ollama not running), and that the GUI still builds.

### What I kept or changed
Kept LiteLLM and a model chosen in `.env`, as planned. Added two changes the plan didn't have: the client now points LiteLLM's model lookup at the configured Ollama server, and the default address is 127.0.0.1 rather than localhost, which avoids a slow IPv6 attempt on Windows. Left `tests/eval_runner.py` for Guru to switch over to `create_llm()`. Before committing, I asked whether Claude or Gemini could be used instead. They can, by changing the model in `.env`. I then had a startup check added for a missing API key, and asked for one provider-neutral key setting (`STUDY_BUDDY_LLM_API_KEY`) instead of each provider's own variable, so switching providers only changes `.env` values. Tests: 54 passing, 2 skipped.

## 2026-11-09 · Remove a document from the Documents tab
- **Tool (model):** Claude Code (Claude Opus 5.5)
- **Files:** backend/files.py, backend/retrieval/__init__.py, backend/orchestrator.py, backend/baseline/ctrl_f.py, frontend/components.py, frontend/formatting.py, frontend/app.py, tests/test_real_pipeline.py, tests/test_orchestrator.py, README.md
- **Outcome:** Changed

### What I asked for
An explanation of why right-clicking the ingested-documents table showed an empty popup, then a way to remove a document so retrieval can't use it. The document had to be deleted from `data/` too, and the user had to be warned first.

### How I checked it
Reviewed the plan before any code was written. Ran the pytest suite: 59 passing, 2 skipped, including tests that remove one of two files and check it's gone from both indexes, retrieval and the Ctrl+F search, and from both storage folders, while the other file stays. A further test checks that a name like `../x.pdf` can't delete anything outside the storage folder. Drove the UI handlers on a temporary store: selecting a row enables the button, Remove only shows the warning, Cancel deletes nothing, and confirming deletes all 11 chunks and both copies while the original file stays.

### What I kept or changed
The empty popup is Gradio's cell menu, which only has editing actions, and it can't take a custom Remove action. So I chose a select-then-Remove button with an in-page warning instead, and hid the empty menu with CSS. I asked for the stubs to be left unchanged, since they will be removed soon. So `remove()` exists only on the real retriever for now, and isn't yet part of the shared Retriever interface.

## 2026-11-09 · Run on a local model, fix the double badge and citation names
- **Tool (model):** Claude Code (Claude Opus 5.5)
- **Files:** backend/orchestrator.py, backend/qa/qa_prompts.py, backend/qa/components.py, tests/test_orchestrator.py, tests/test_qa_solid.py, backend/config.py, backend/llm/__init__.py, .env.example, README.md, tests/test_llm.py
- **Outcome:** Changed

### What I asked for
A plan to run the app on one local Ollama model, and then on Claude Haiku if that went well. Gemini was to be removed as an example, since the school doesn't provide it. After the first test run, I asked for the double confidence badge to be fixed and for an explanation of why the benchmark looked poor.

### How I checked it
Installed Ollama 0.40.15 and chose `granite4.1:8b`, a recent 8B model that doesn't use a reasoning step. It runs 100% on the GPU with an 8192-token context, using 6.7 GB of VRAM at about 90 tokens a second, and `pytest -m ollama` passes. Ran the 20 retrieval-benchmark questions through the full app: only 7/20 cited the expected PDF. A diagnosis showed that 11 of the misses had cited the right PDF with a "Source:" or "Citation:" prefix. The citation verifier accepted those but kept the prefix in the stored name, which also showed in the sources panel and the badge. Two more misses come from the benchmark naming `SE201_Week07_MCP_A2A_Accountability.pdf`, a longer Week 7 deck that isn't among the PDFs here. After the fixes, 17/20 cite the expected PDF (17/18 without the Week 7 questions), no citation names carry a prefix, and the follow-up answer has one badge. The one remaining miss is a correct answer with no citations, which the engine rightly marked ungrounded. Ran the full suite: 61 passing. Guru's `test_qa_solid.py` passes, and `eval_runner.py` gives the same 25 metrics and 20 outcomes as the committed results.

### What I kept or changed
The double badge came from earlier answers being sent back to the model as history with the badge still in them, so the orchestrator now strips the badge and the "not found" header from history. With my approval, the citation fix went into Guru's QA code: verified citations now take the retrieved chunk's real file name and location, and the duplicate verification loop in `components.py` now reuses the fixed function. I left Lichelle's `benchmark.json` unchanged and will report the Week 7 file mismatch to her. A test that relied on the local `.env` using the stub LLM now sets that itself.

## 2026-11-09 · AI Log tab updates automatically
- **Tool (model):** Claude Code (Claude Opus 5.5)
- **Files:** frontend/components.py, backend/disclosure_log.py, tests/test_orchestrator.py
- **Outcome:** Changed

### What I asked for
Whether the in-app AI Log tab is required, and whether it was being updated. It isn't required by the briefing, whose disclosure log is the team's development log, but the checkpoint report presents it as a delivered feature, so I kept it. I asked for it to update whenever a new entry is added, instead of only on page load or Refresh.

### How I checked it
A new test drives the polling handler: with no log yet it doesn't reload, after a question is asked the new entry appears, and with nothing new it leaves the table alone. Ran the full suite: 62 passing. Restarted the app and confirmed the page has the 2-second timer wired to the table, with its loading indicator hidden.

### What I kept or changed
The tab checks the log file's size and modification time every 2 seconds and reloads only when they change, so entries from any tab or session appear without flicker. I removed the Refresh button, which is no longer needed.

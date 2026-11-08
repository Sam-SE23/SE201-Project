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

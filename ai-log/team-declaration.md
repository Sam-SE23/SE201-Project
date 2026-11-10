# AI Use Declaration: SE201 G1 Team 7 (AI Study Buddy)

All four members used AI tools to develop this project. Each member's log in this folder records every task in detail.

- **Lichelle Weasley** used Claude Code (Claude Sonnet 5 and 5.5) to scaffold the ingestion and retrieval pipeline and write its tests, and Copilot in VS Code to add BGE embeddings, BM25 keyword search, rank fusion, a reranker and prompt-injection cleaning. She checked the output with ingestion and chunking tests, which found and fixed three chunking bugs, and with a 20-question Recall@K benchmark (Recall@5: 75%).
- **Gurunathan Sampravinraj** used Gemini Notebook and Antigravity to design the grounded Q&A prompts, guardrails and citation verifier, and to build the first evaluation harness. He checked them with unit tests and a manual review of the benchmark questions and results.
- **Yeo Sheen Hern** used Codex (GPT-6) to build quiz mode. He checked it with the test suite and a scripted end-to-end quiz in the app.
- **Darrion Ong** used Claude Code (Claude Opus 5.5) for the interface, orchestration, LLM client, integration of the retriever and Q&A engine, and the real-mode benchmark. He checked the code with the test suite (86 tests), runs on real models, reading failed benchmark answers one by one, and checking each quiz question against its cited page.

All AI-generated code was reviewed and tested before it was merged. The benchmark results were checked by hand where the automatic scores looked wrong, and the corrections are recorded in `tests/eval_review.md`.

**Commit trailers:** none of our commits include the `Assisted-by:` line the policy asks for. We noticed this at submission. Each AI-assisted task has a log entry in this folder that lists the files it changed, so the use can still be traced to the code.

**The app's own AI:** at runtime the app calls Claude Haiku (a local granite4.1:8b model was used for comparison). These calls are part of the product, not development tools, and are logged by the app in `data/logs/ai_log.jsonl`.
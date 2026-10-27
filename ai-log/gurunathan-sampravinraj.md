# AI Use Disclosure Log

**Name**: Gurunathan Sampravinraj
**Role**: Lead Developer — Grounded Q&A (Prompt Design, Citation Formatting, Guardrails, Security & Evaluation Harness)
**Project**: AI Study Buddy (SE201)

---

### Date: October 27, 2026

#### 1. AI Tool(s) Used
* **Tool / Model**: Gemini Notebook (System Architecture & Evaluation Strategy) & Antigravity (Code Execution, Refactoring & Test Automation)
* **Purpose**: System prompt engineering, multi-turn query reformulation, security guardrails, programmatic citation verification, RAGAS evaluation metrics, and non-AI baseline benchmarking.

#### 2. Specific Contributions & Prompts Drafted
* **Grounded Q&A System Prompt & Engine**: Architected `GroundedQAEngine` and `GROUNDED_QA_SYSTEM_PROMPT` in `backend/qa/qa_prompts.py` enforcing strict source grounding, inline citation formatting (`[Source, Slide/Page]`), and fallback handling (`OUT_OF_SCOPE_FALLBACK_TEXT`).
* **Similarity Threshold Calibration (`MIN_SCORE = 0.25`)**: Calibrated similarity threshold in `backend/retrieval/__init__.py` to ensure academic policy queries retain context while keeping out-of-scope queries (`< 0.13`) strictly filtered.
* **Programmatic Citation Verification**: Implemented `verify_citation_against_chunks()` in `backend/qa/qa_prompts.py` to cross-reference inline citations against `chunks_used` metadata, automatically stripping hallucinated slide numbers and flagging ungrounded answers.
* **3-Step Socratic Academic Integrity Guardrail**: Refined Rule 4 of `GROUNDED_QA_SYSTEM_PROMPT` to enforce structured Socratic guiding hints (Conceptual Architecture, Implementation Hints, Pseudocode Framework) for assignment/quiz requests instead of flat refusals or complete code.
* **Multi-Turn Conversational Query Reformulation**: Implemented `contextualize_query()` to rewrite ambiguous follow-up queries using previous chat turns into standalone retrieval queries before calling ChromaDB.
* **Adversarial Jailbreak & Prompt Injection Defense**: Added `sanitize_and_detect_injection()` to detect and intercept prompt override attempts ("ignore previous instructions", "bypass system prompt") and safely return grounded security refusals.
* **Visual Grounding Badge & Quoted Excerpts**: Implemented composite Grounding Confidence scoring (`🟢 Grounding Confidence: 100%`) and attached 1–2 sentence supporting quote excerpts to `Answer.chunks_used` for UI display.
* **Non-AI Baseline & RAGAS Evaluation Harness**: Built and executed `tests/eval_runner.py` to evaluate all 20 benchmark questions side-by-side against `CtrlFBaseline` (+5.00% accuracy, +5.88% citation precision over Ctrl+F), while computing RAGAS Faithfulness (100%) and Context Precision (41.25%) with an automated Failure Taxonomy.

#### 3. Human Review & Verification
* **Code & Integration Audit**: Tested all features end-to-end via `pytest tests/test_real_pipeline.py` and `python -m tests.eval_runner`, confirming zero test failures.
* **Benchmark Results Audit**: Verified `tests/eval_results.json` line-by-line to ensure RAGAS faithfulness scores and citation verification accurately caught edge cases without false positives.
* **Git Commit Organization**: Authored atomic, industry-standard git commits on `feat/grounded-qa-pipeline` (`d0c981b`, `dde6361`, `1b4b2ee`, `cca2a2e`).

---

### Date: October 17, 2026

#### 1. AI Tool(s) Used
* **Tool / Model**: Gemini Notebook (Architect/Strategist) & Antigravity (Code Execution Agent / LLM Client)
* **Purpose**: Assisting in system prompt design, citation extraction logic, benchmark test set creation, and automated judge evaluation scripting.

#### 2. Specific Contributions & Prompts Drafted
* **System Prompt & Guardrail Engineering**: Designed `GROUNDED_QA_SYSTEM_PROMPT` in `backend/qa/qa_prompts.py` incorporating strict negative constraints against general knowledge leaks, explicit inline citation rules (`[Source Title, Section/Slide #]`), academic integrity restrictions for assignment code, and exact fallback string triggers (`OUT_OF_SCOPE_FALLBACK_TEXT`).
* **Evaluation Benchmark Dataset Creation**: Generated a 20-question structured test suite (`tests/eval_benchmark.json`) covering four query categories: `explicit_fact`, `synthesis`, `out_of_scope`, and `academic_integrity`.
* **Automated Evaluation Harness**: Created the `judge_response` logic and test runner (`tests/eval_runner.py`) to measure answer accuracy, hallucination rates, citation validity, and fallback accuracy.

#### 3. Human Review & Verification
* **Code Verification**: Manually inspected `qa_prompts.py` and `backend/qa/__init__.py` to ensure regex citation parsers correctly mapped to `Chunk` metadata datatypes and didn't crash on empty retrieval sets.
* **Benchmark Audit**: Audited the 20 benchmark questions to confirm that all ground-truth keywords accurately reflected the SE201 syllabus and that out-of-scope questions genuinely lacked context in ChromaDB chunks.
* **Output Inspection**: Reviewed `tests/eval_results.json` line-by-line to verify that the LLM judge's 100% accuracy score reflected true grounded answers rather than false positives in evaluation.
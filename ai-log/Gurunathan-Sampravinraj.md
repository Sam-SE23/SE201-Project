# AI Use Disclosure Log

**Name**: Gurunathan Sampravinraj
**Role**: Lead Developer — Grounded Q&A (Architecture, Prompt Design, Guardrails, Security & Evaluation Harness)
**Project**: AI Study Buddy (SE201)

---

### Date: October 27, 2026

#### 1. AI Tool(s) Used
* **Tool / Model**: Gemini Notebook (System Architecture & Evaluation Strategy) & Antigravity (Code Execution, Refactoring & Test Automation)
* **Purpose**: Applying SOLID design principles, prompt engineering, multi-turn query reformulation, security guardrails, programmatic citation verification, RAGAS metrics, and baseline benchmarking.

#### 2. Specific Contributions & Prompts Drafted
* **SOLID Architecture Refactoring (`backend/qa/components.py`)**: Refactored monolithic Q&A pipeline into decoupled, single-responsibility components (`RegexQueryGuard`, `ConversationalQueryReformulator`, `StrictCitationVerifier`, `DefaultGroundingEvaluator`, `QAPipelineMetrics`) adhering to SRP, OCP, LSP, ISP, and DIP.
* **Performance Optimization & Telemetry**: Implemented query-cue short-circuiting and LRU caching in query reformulation, along with fine-grained step profiling (`engine.last_metrics`) to capture latency across pipeline stages.
* **Similarity Threshold Calibration (`MIN_SCORE = 0.25`)**: Calibrated similarity threshold in `backend/retrieval/__init__.py` so policy/syllabus queries retain context while keeping out-of-scope queries (`< 0.13`) strictly filtered.
* **Programmatic Citation Verification**: Built anti-hallucination verification cross-referencing inline citations `[Source, Slide/Page]` against `chunks_used` metadata to strip hallucinated slide numbers.
* **3-Step Socratic Academic Integrity Guardrail**: Refined system prompts to enforce structured Socratic guiding hints (Conceptual Architecture, Implementation Hints, Pseudocode Framework) for assignment/quiz requests instead of flat refusals or complete code.
* **Adversarial Jailbreak & Security Defense**: Implemented `RegexQueryGuard` to intercept prompt override attempts ("ignore previous instructions", "bypass system prompt") and safely return grounded security refusals.
* **Non-AI Baseline & RAGAS Evaluation Harness**: Built and executed `tests/eval_runner.py` to benchmark 20 test cases against `CtrlFBaseline` (+5.00% accuracy, +5.88% citation precision over Ctrl+F), computing RAGAS Faithfulness (100%) and Context Precision (41.25%).

#### 3. Human Review & Verification
* **Code Audit**: Verified unit tests (`pytest tests/test_qa_solid.py`) and full regression tests (`test_real_qa_engine_end_to_end`).
* **Git Commit Management**: Authored atomic commit `2115d98` on branch `feat/qa-solid-refactor`.

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
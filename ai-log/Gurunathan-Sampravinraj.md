# AI Use Disclosure Log 

**Name**: Gurunathan Sampravinraj 
**Role**: Grounded Q&A (Prompt Design, Citation Formatting, Answer Generation & Evaluation) 
**Project**: AI Study Buddy (SE201)

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
* **Benchmark Audit**: Audited the 20 benchmark questions to confirm that all ground-truth keywords accurately reflected the SE201 syllabus and that out-of-scope questions genuinely lacked context in ChromaDB chunks. * **Output Inspection**: Reviewed `tests/eval_results.json` line-by-line to verify that the LLM judge's 100% accuracy score reflected true grounded answers rather than false positives in evaluation.
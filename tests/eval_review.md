# Benchmark review: granite4.1:8b (local) and Claude Haiku (hosted) on the SE201 materials

- **Raw results:** `tests/eval_results_ollama-chat-granite4-1-8b.json`
- **Command:** `python tests/eval_runner.py --real --docs data/benchmark_corpus`
- **Date:** 9 Nov 2026
- **Corpus:** the 11 files the benchmark names (10 lectures plus `SE201_2026T1_project_v1.02.pdf`)
- **Questions:** 20 (8 fact, 7 synthesis, 3 out-of-scope, 2 academic integrity)

## Update: after improvements 1–4 (current results file)

| Run | Accuracy | Hallucination | Avg time |
|---|---|---|---|
| Original run | 45% (9/20) | 58.8% | 5.1 s |
| 1. Harness judges faithfulness against the full chunks the model saw, not the display excerpts; se07 also accepts spec p.2, where the date is too | 70% (14/20)* | 35.3% | 4.7 s |
| 4. Temperature 0 for the local model (repeatable: same 8 failures in two runs, 17/20 identical answers) | 60% (12/20) | 41.2% | 4.5 s |
| 2. QA engine retrieves 8 passages instead of 4, so two-lecture questions see both | 65% (13/20) | 35.3% | 4.7 s |
| 3. Stricter system prompt: no facts beyond the context, cite every sentence, answer each part of a multi-part question from its own source, under ~150 words | **75% (15/20)** | **23.5%** | **3.3 s** |

\* At the default temperature granite's answers vary between runs, so the 70% came from a favourable draw. The temperature-0 runs that follow are repeatable.

- **Unchanged throughout:** out-of-scope fallback 100%, academic integrity 100%, citation presence 94%.
- **Remaining failures (5):**
  - **se04:** retrieval miss. The temperature slide, Week05 p.16, isn't retrieved.
  - **se10, se12, se14:** granite still adds material that isn't on the retrieved pages.
  - **se09:** correct and faithful, but cites pages outside the expected list.
- **Conclusion:** the remaining gap to ≥85% is mainly the 8B model's adherence to its sources. The next lever is a stronger model, which needs only a `.env` change.
- **Caveat:** steps 2 and 3 were tuned against these same 20 questions.

## Comparison: Claude Haiku (step 5, `tests/eval_results_anthropic-claude-haiku-5-5.json`)
Same corpus, harness and code as the granite row above. Only the model differs (`anthropic/claude-haiku-5-5`, set in `.env`).

| Metric | granite4.1:8b (local) | Claude Haiku (hosted) | Target |
|---|---|---|---|
| Answer accuracy | 75% (15/20) | **90% (18/20)** | ≥85% |
| Hallucination / ungrounded | 23.5% | **5.9%** | <10% |
| Citation presence | 94% | 100% | ≥90% |
| Correct page cited | 87% | 93% | reported |
| Out-of-scope fallback | 100% | 100% | 100% |
| Academic integrity | 100% | 100% | 100% |
| Avg time per question | 3.3 s | 4.5 s | — |

- **Haiku's failures:**
  - **se04:** the same temperature-slide retrieval miss as granite, so it's a retrieval problem, not a model one.
  - **se12:** its RAG/attention answer went beyond the retrieved text on this run. Haiku isn't run at temperature 0, so this varies between runs: the first run passed se12.
- **Harness fix found by this run:** the academic-integrity check only recognised refusals worded "cannot". Haiku's "I can't write your weekly reflection, since it's graded…" is a correct refusal and was being scored as a failure. The check now also accepts "can't", "won't" and "unable to", and has a test. granite's results are unaffected, since both of its integrity answers already passed.
- **Trade-offs of the hosted model:**
  - It needs internet and an API key.
  - It costs a little per question; the whole 20-question run is well under US$1.
  - It sends lecture excerpts to Anthropic.
  - granite is free, offline and private, but reaches only 75%.

The sections below describe the **original run**, before the improvements.

## Automatic metrics (as reported by the harness, original run)

| Metric | granite | Target | Ctrl+F baseline |
|---|---|---|---|
| Answer accuracy | 45% | ≥85% ❌ | 80% |
| Hallucination / ungrounded rate | 58.8% | <10% ❌ | — |
| Citation presence (in-scope) | 94.1% | ≥90% ✅ | 100% |
| Correct source cited (expected page) | 86.7% | reported | — |
| Out-of-scope fallback | 100% | 100% ✅ | 33% |
| Academic-integrity compliance | 100% | 100% ✅ | — |
| Average time per question | 5.1 s | | |

- **The whole question as one Ctrl+F phrase:** 0 hits on 100% of questions.

## Why the automatic accuracy is low
In-scope accuracy needs three things: **faithfulness** (≥50% of the answer's meaningful words appear in the retrieved text), **keyword completeness** and **a valid citation**. Most failures are on faithfulness alone. Reading every answer shows three causes.

1. **Measurement artifact (2 questions: se02, se13).**
   - The harness checks faithfulness against `answer.chunks_used`.
   - The QA engine shortens those to a 1–2 sentence display excerpt (`extract_supporting_excerpt`), while the model saw the full chunks.
   - Re-scoring the saved answers against the full chunks with the harness's own `judge_response` turns both into passes. Scoring against the excerpts reproduces all 20 saved faithfulness verdicts.
2. **Benchmark label too narrow (1 question: se07).**
   - The answer ("18 October (Sunday) at 23:59") is correct and cites spec p.2.
   - The benchmark lists only p.1, but the date appears on both pages.
3. **Real model weakness: synthesis across two lectures (6 questions: se09, se10, se11, se12, se14, se15).**
   - The answers are broadly correct, but they cite only one of the two lectures, and granite pads them with general knowledge that isn't on the slides (e.g. LaTeX formulas, generic descriptions).
   - The overlap check rightly penalises that padding.
4. **Retrieval miss (1 question: se04, temperature).**
   - The expected page (Week05 p.16) wasn't retrieved, and the answer is generic rather than from the slides.

## Hand-checked result (first pass, to be confirmed)
An answer counts if it is correct **and** every part cites a correct source.

| Category | Correct and cited |
|---|---|
| Explicit fact | 7/8 (se04 missed) |
| Synthesis | 1/7 (se13). The other 6 are partial: one lecture cited, padded with outside knowledge. |
| Out-of-scope | 3/3 |
| Academic integrity | 2/2 |
| **Total** | **13/20 (65%)** against the ≥85% target ❌ |

## Takeaways for the evaluation slide
- granite answers **single-fact questions well (7/8)**, with citations to the right page. It always declines off-topic questions (3/3) and never gives a full assignment solution (2/2).
- It is **weak at synthesis**: it cites one source and fills the gap from general knowledge. A stronger model is the most likely fix, and the client supports a hosted model through `.env` alone.
- The RAG system beats Ctrl+F where it matters: off-topic questions (100% vs 33%), and whole questions as one phrase (Ctrl+F finds nothing for any of them). Ctrl+F's 80% accuracy comes from searching the question's single most specific word, which often finds the right page but gives the student no answer.

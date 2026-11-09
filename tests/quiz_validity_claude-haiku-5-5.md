# Quiz validity spot check: `anthropic/claude-haiku-5-5`

- **Target (from the proposal):** ≥90% validity for a set of 10 generated quiz questions, checked by hand.
- **Date:** 9 Nov 2026.
- **Setup:** the app's real quiz engine (`backend/quiz/`, `GroundedQuiz`) with Claude Haiku, over the 11 benchmark PDFs in `data/benchmark_corpus/` (the 10 lectures named in `tests/eval_benchmark_se201.json` plus `SE201_2026T1_project_v1.02.pdf`).
  - The index was built in a temporary store.
  - The engine was asked for 2 questions per topic until 10 were kept.
  - It used the same script and topic list as the granite check (`tests/quiz_validity_granite4.1-8b.md`).

## Generation

| | Claude Haiku | granite4.1:8b (for comparison) |
|---|---|---|
| Model calls | 8 (8 topics) | 27 (20 topics) |
| Questions proposed | 15 | 52 |
| Kept by the engine's own checks | 10 (67%) | 10 (19%) |
| Invalid-JSON replies / timeouts | 0 / 0 | 0 / 0 in the final run (one of each in earlier attempts) |

- **What the engine checks:** a question is kept only if its quote appears word for word in a retrieved chunk, it has 4 distinct choices, and the answer appears in the quote.

## Criteria
A question is **valid** only if all four hold:
- **(a)** it's answerable from the cited page alone
- **(b)** the answer key is correct
- **(c)** no distractor is also correct
- **(d)** the citation points to the right file and page

## Questions

| # | Question (abridged) | Key | Source | Verdict | Reason |
|---|---|---|---|---|---|
| 1 | What does back-propagation compute in a neural network? | It computes the gradient for all weights | Week03_Training p.23 | ✅ | p.23: "It computes the gradient for all weights" |
| 2 | In the blame-assignment view, what is working out each weight's share of the error called? | back-propagation | Week03_Training p.31 | ✅ | p.31: "Computing that is called back-propagation" |
| 3 | How many attention heads does GPT-2 small use? | 12 heads | Week04_Transformers p.51 | ✅ | p.51: "12 heads in GPT-2 small". Valid, but pure recall. |
| 4 | What is RAG's proposed solution to the selection problem? | Insert only those passages into the prompt | Week06_RAG p.19 | ✅ | A listed step of the solution on p.19, and every distractor is wrong. The key is only the last of the four steps, so the question is a little narrow. |
| 5 | Why can't a model report which documents it was trained on? | The weights hold a distribution over next tokens | Week06_RAG p.7 | ✅ | p.7: "…NOT a list of what was read" |
| 6 | The judge picks the same letter whichever implementation is in that slot: which bias? | Position bias | Week11_Code_review p.15 | ✅ | p.15: "The same letter both times is position bias". No distractor is a synonym. |
| 7 | Where do temperature, top-k and top-p sit? | Settings in the code around the weights | Week05_Generation p.57 | ✅ | p.57: "settings in the code around the weights" |
| 8 | In the tool-calling example, what does temperature 0 give for the same question? | The same call | Week06_RAG p.46 | ✅ | p.46: "At temperature 0 the same question gives the same call" |
| 9 | In mutation testing, what is a "survivor"? | A mutant the tests still pass | Week10_Checkpoint p.29 | ✅ | p.29: "A mutant the tests still pass is a survivor" |
| 10 | Which statement assigns the runtime that runs and controls the agent's steps? | LangGraph: the runtime… | Week09_LangChain p.6 | ✅ | p.6: "LangGraph: the runtime that runs and controls the steps" |

## Result
- **First pass: 10/10 valid (100%)** against the ≥90% target. ✅
- **Compared with granite** (8/10, two questions with a distractor that was also correct): Haiku's distractors are clearly wrong. It also needed far fewer attempts, since two thirds of its proposed questions passed the engine's checks, against one fifth of granite's.
- **Caveat:** the questions are mostly single-fact recall from one slide. That suits a validity check, but isn't evidence of deeper questioning.

**Reviewed by:** _(Darrion: confirm or overrule each verdict, then sign here)_

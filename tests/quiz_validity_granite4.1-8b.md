# Quiz validity spot check: `ollama_chat/granite4.1:8b`

- **Target (from the proposal):** ≥90% validity for a set of 10 generated quiz questions, checked by hand.
- **Date:** 9 Nov 2026.
- **Setup:** the app's real quiz engine (`backend/quiz/`, `GroundedQuiz`) with granite, over the 11 benchmark PDFs in `data/benchmark_corpus/` (the 10 lectures named in `tests/eval_benchmark_se201.json` plus `SE201_2026T1_project_v1.02.pdf`).
  - The index was built in a temporary store.
  - The engine was asked for 2 questions per topic until 10 were kept.

## Generation

| | |
|---|---|
| Model calls | 27, over 20 topics |
| Questions proposed by the model | 52 |
| Kept by the engine's own checks | 10 (19%) |
| Invalid-JSON replies / timeouts in this run | 0 / 0 |

- **What the engine checks:** a question is kept only if its quote appears word for word in a retrieved chunk, it has 4 distinct choices, and the answer appears in the quote. Most of granite's questions failed these checks, so the 81% rejection rate shows a weak model being filtered, not invalid questions reaching students.
- **Two failures seen during earlier attempts, not this run:**
  - A reply that wasn't valid JSON: the engine raised "invalid quiz data, try again".
  - A request that ran past the 120-second timeout.

## Criteria
A question is **valid** only if all four hold:
- **(a)** it's answerable from the cited page alone
- **(b)** the answer key is correct
- **(c)** no distractor is also correct
- **(d)** the citation points to the right file and page

## Questions

| # | Question (abridged) | Key | Source | Verdict | Reason |
|---|---|---|---|---|---|
| 1 | Which mathematical principle underlies the efficiency of back-propagation? | Chain rule from calculus | Week03_Training p.30 | ✅ | p.30: "It is the chain rule from calculus" |
| 2 | Which step in RAG compares fingerprints to find relevant passages? | Compare the fingerprints to find relevant passages | Week06_RAG p.19 | ✅ | Listed step on p.19. Easy, since the answer restates the question. |
| 3 | What bias makes the LLM judge prefer the buggy implementation regardless of order? | Verbosity bias | Week11_Code_review p.15 | ✅ | p.15: "the buggy one preferred in either order is verbosity bias" |
| 4 | What does LangChain abstract in LLM applications? | Model-specific interfaces | Week09_LangChain p.2 | ✅ | p.2: "Abstract model-specific interfaces" |
| 5 | How do facts reach the model (MCP)? | Through the context window | Week07_MCP_A2A p.33 | ✅ | p.33: "Facts and actions reach the model through the context window" |
| 6 | Which A2A method sends a message between agents? | SendMessage | Week07_MCP_A2A p.27 | ✅ | p.27 lists SendMessage, GetTask, CancelTask, SubscribeToTask |
| 7 | % of automated review comments labelled resolved in an industrial deployment? | 73.8% | Week10_Checkpoint p.23 | ✅ | p.23: "73.8% … labelled resolved" |
| 8 | Which concept does back-propagation rely on to compute gradients efficiently? | Chain rule from calculus | Week03_Training p.30 | ✅ | Valid, but **tests the same fact as Q1** |
| 9 | What bias is shown when the same letter is picked in both orders? | Position bias | Week11_Code_review p.15 | ❌ | (c): the distractor **"Order bias"** means the same as position bias. The question wording is also muddled. |
| 10 | What does a surviving mutant indicate? | The change made no difference, or no test looked at that line | Week10_Checkpoint p.29 | ❌ | (c): the distractor **"The generated tests are insufficient"** is arguably also correct, since "no test looked at that line" |

## Result
- **First pass: 8/10 valid (80%)** against the ≥90% target. ❌
- **Observations:**
  - The valid questions are mostly single-fact recall.
  - The two invalid ones both have a distractor that is also correct, which the engine's word-for-word checks can't detect.
  - One near-duplicate (Q1/Q8) shows the engine removes exact duplicates but not ones with the same meaning.

**Reviewed by:** _(Darrion: confirm or overrule each verdict, then sign here)_

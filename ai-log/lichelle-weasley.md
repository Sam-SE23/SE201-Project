# AI Use Log: Lichelle Weasley

## 2026-10-16 · RAG pipeline scaffold for ingestion and retrieval
• **Tool (model):** Claude Code (Claude Sonnet 5)
• **Files:** config.py, build_index.py, test_retrieval.py, README.md, requirements.txt, pipeline/init.py, pipeline/ingest.py, pipeline/chunk.py, pipeline/embed.py, pipeline/store.py, pipeline/retrieve.py
• **Outcome:** Changed

### What I asked for
 After letting Claude know my scope: PDF and PPTX parsing, chunking, embeddings and the vector store, I confimed the final layout and built it as plain Python with a free local embedding model (all-MiniLM-L6-v2) and a Chroma vector store, so that retriev (query, k) returns text, source, page and score for the other members to call.

## How I checked it
In Claude's environment, ingest.py and chunk.py ran on a PDF Claude generated. embed.py, store.py, retrieve.py and build_index.py could not be run there because the package install did not finish. On 17 Oct I ran retrieval myself on SE201_Week01_From_Text_to_Tokens.pdf with the question "what is an llm". It returned ranked chunks with source, page and score (top scores 0.46-0.54), but none of the top results defined an LLM.

## What I kept or changed
Kept the folder layout, the retrieve() return shape and the free local model. Later changes are in the entries below (pdfplumber, skipped-file messages, chunking fixes).

## 2026-10-17 · pdfplumber switch, skipped-file messages and ingest tests
• **Tool (model):** Claude Code (Claude Sonnet 5.5)
• **Files:** pipeline/ingest.py, requirements.txt, test_ingest.py
• **Outcome:** Changed

## What I asked for
Three changes: use pdfplumber instead of pypdf, print a message for every file that gets skipped instead of skipping silently, and generate test files to check the ingestion code.

## How I checked it
Ran the new ingest.py on a generated PDF, then wrote test_ingest.py, which builds its own test files (a 3-page PDF with a blank page, a 3-slide PPTX with speaker notes and a table, an unsupported .txt, a corrupt PDF and a subfolder). All 11 checks passed in Claude's environment.

## What I kept or changed
The skipped-file reporting was kept. The PPTX table text is deliberately not extracted for now, and the test records that as a known limitation. Also noted that hidden files such as .gitkeep are reported as skipped.

## 2026-10-17 · Chunking tests and three bug fixes
• **Tool (model):** Claude Code (Claude Sonnet 5.5)
• **Files:** pipeline/chunk.py, test_chunk.py
• **Outcome:** Changed

## What I asked for
A full test of the chunking code, after checking that only a short-text run had been done.

## How I checked it
Wrote test_chunk.py (20 checks) and ran it against the original chunk.py. Three checks failed: a very long word made the chunker loop forever, an overlap equal to or larger than the chunk size made it loop forever, and chunks could start in the middle of a word. All three were fixed, then 20 of 20 checks passed. Ran a one-off random stress test of 3,000 combinations of text, chunk size and overlap with no hangs, oversized chunks or lost words; that script was not kept.

## What I kept or changed
Kept the fixed chunk.py. The overlap is now capped at half a chunk, which is a behaviour change from the original settings. Tested it by querying the same question (what is an LLM).
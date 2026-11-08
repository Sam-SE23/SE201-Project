"""
Run this once (and again any time docs/chunking change) to build the
vector store from scratch.

Usage:
    python build_index.py            # builds from whatever's in data/
    python build_index.py --reset    # wipes the old store first
"""

import argparse

from pipeline.ingest import load_documents
from pipeline.chunk import chunk_pages
from pipeline.embed import embed
from pipeline.store import add_chunks, reset_collection
from config import DATA_DIR


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="wipe the existing store first")
    args = parser.parse_args()

    if args.reset:
        reset_collection()

    print(f"[build] loading documents from {DATA_DIR} ...")
    pages = load_documents()
    if not pages:
        print("[build] Nothing to index. Add PDF/PPTX files to the data/ folder and re-run.")
        return

    print("[build] chunking ...")
    chunks = chunk_pages(pages)
    print(f"[build] {len(pages)} pages/slides -> {len(chunks)} chunks")

    print("[build] embedding (this loads the model on first run, may take a moment) ...")
    texts = [c.text for c in chunks]
    vectors = embed(texts)

    print("[build] writing to vector store ...")
    add_chunks(chunks, vectors)

    print(f"\n[build] Done. {len(chunks)} chunks indexed and ready for retrieval.py")


if __name__ == "__main__":
    main()
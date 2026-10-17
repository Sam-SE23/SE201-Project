"""
Step 2: Chunking.

Naive fixed-size chunking with overlap. Deliberately simple for now, I will
tune CHUNK_SIZE/CHUNK_OVERLAP in config.py once I test more on the data.
"""

from dataclasses import dataclass
from pathlib import Path
import sys
 
sys.path.append(str(Path(__file__).parent.parent))
from config import CHUNK_SIZE, CHUNK_OVERLAP
from pipeline.ingest import RawPage, load_documents
 
 
@dataclass
class Chunk:
    id: str            # unique id, e.g. "lecture1.pdf-p3-c0"
    text: str
    source: str
    page: int
 
 
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping fixed-size windows, breaking on whitespace
    near the boundary where possible so words aren't sliced in half."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    if len(text) <= chunk_size:
        return [text]
 
    # Cap the overlap at half a chunk so every step moves forward; an overlap
    # >= chunk_size would otherwise make the loop repeat the same window forever.
    overlap = max(0, min(overlap, chunk_size // 2))
 
    n = len(text)
    chunks = []
    start = 0
    while start < n:
        end = min(start + chunk_size, n)
        if end < n:
            # Prefer to break at the last space/newline before the hard cutoff.
            # The break must fall beyond the overlap region so the next chunk
            # still starts after this one did (guarantees forward progress).
            # If there is no such break (a huge word, or text with no spaces)
            # cut at the hard limit instead.
            ws = max(text.rfind(" ", start, end), text.rfind("\n", start, end))
            if ws > start + overlap:
                end = ws
 
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
 
        # Next chunk starts `overlap` characters back, nudged forward to the
        # start of the next word so a chunk never begins mid-word.
        next_start = end - overlap
        if next_start > 0 and not text[next_start - 1].isspace():
            j = next_start
            while j < end and not text[j].isspace():
                j += 1
            if j + 1 < end:
                next_start = j + 1
        start = next_start
    return chunks
 
 
def chunk_pages(pages: list[RawPage]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        pieces = chunk_text(page.text)
        for i, piece in enumerate(pieces):
            chunk_id = f"{page.source}-p{page.page}-c{i}"
            chunks.append(Chunk(id=chunk_id, text=piece, source=page.source, page=page.page))
    return chunks
 
 
if __name__ == "__main__":
    pages = load_documents()
    chunks = chunk_pages(pages)
    print(f"[chunk] {len(pages)} pages -> {len(chunks)} chunks")
    if chunks:
        print("\n--- sample chunk ---")
        print(f"id={chunks[0].id}")
        print(chunks[0].text[:300])
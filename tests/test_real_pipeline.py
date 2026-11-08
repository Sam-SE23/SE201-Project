"""Real retriever (Chroma) and real QA engine, wired through the orchestrator.

Skipped when the RAG dependencies (chromadb, sentence-transformers) aren't installed.
The first run downloads the embedding model.
"""

import json

import pytest

pytest.importorskip("chromadb")
pytest.importorskip("sentence_transformers")
pytest.importorskip("rank_bm25")

from backend import registry
from backend.interfaces import ChatTurn, Retriever
from backend.orchestrator import Orchestrator
from backend.qa import create_qa_engine
from backend.retrieval import ChromaRetriever
from backend.stubs import FakeQuiz


class ScriptedLLM:
    """Answers like a well-behaved grounded model would, without an API call."""
    model_name = "scripted"

    def complete(self, system: str, messages: list[ChatTurn], tools=None) -> str:
        return "The checkpoint is due on 18 October at 23:59 [syllabus.pdf, p.2]."


@pytest.fixture
def store_dir(tmp_path):
    # Point Lichelle's Chroma and BM25 indexes at a temp dir so tests never touch the real store.
    return tmp_path / "store"


@pytest.fixture
def retriever(store_dir):
    return ChromaRetriever(store_dir=store_dir)


def _bm25_record_count(store_dir) -> int:
    return len(json.loads((store_dir / "bm25_corpus.json").read_text(encoding="utf-8")))


def test_real_retriever_satisfies_the_team_contract(retriever):
    assert isinstance(retriever, Retriever)


def test_ingest_and_list_documents(retriever, sample_pdf, sample_pptx):
    added = retriever.ingest([sample_pdf, sample_pptx])
    docs = retriever.list_documents()
    assert added > 0
    assert set(docs) == {"syllabus.pdf", "lecture.pptx"}
    assert sum(docs.values()) == added


def test_reupload_replaces_chunks(retriever, sample_pdf):
    first = retriever.ingest([sample_pdf])
    retriever.ingest([sample_pdf])
    assert retriever.list_documents() == {"syllabus.pdf": first}


def test_retrieve_returns_cited_chunk(retriever, sample_pdf, sample_pptx):
    retriever.ingest([sample_pdf, sample_pptx])
    top = retriever.retrieve("When is the checkpoint due?", 3)[0]
    assert top.source_file == "syllabus.pdf"
    assert top.location == "p.2"
    assert top.score is not None


def test_pptx_locations_are_slides(retriever, sample_pptx):
    retriever.ingest([sample_pptx])
    top = retriever.retrieve("What does hallucination rate measure?", 1)[0]
    assert top.location == "slide 2"


def test_out_of_scope_query_returns_nothing(retriever, sample_pdf):
    retriever.ingest([sample_pdf])
    assert retriever.retrieve("Explain photosynthesis in plants", 3) == []


def test_ingest_builds_bm25_index(retriever, store_dir, sample_pdf, sample_pptx):
    retriever.ingest([sample_pdf, sample_pptx])
    assert _bm25_record_count(store_dir) == sum(retriever.list_documents().values())


def test_reupload_keeps_bm25_in_sync(retriever, store_dir, sample_pdf):
    retriever.ingest([sample_pdf])
    retriever.ingest([sample_pdf])
    assert _bm25_record_count(store_dir) == sum(retriever.list_documents().values())


def test_missing_bm25_index_is_rebuilt(retriever, store_dir, sample_pdf):
    retriever.ingest([sample_pdf])
    (store_dir / "bm25_corpus.json").unlink()
    fresh = ChromaRetriever(store_dir=store_dir)
    assert (store_dir / "bm25_corpus.json").exists()
    assert fresh.retrieve("When is the checkpoint due?", 3)[0].location == "p.2"


def test_scores_are_probabilities(retriever, sample_pdf, sample_pptx):
    retriever.ingest([sample_pdf, sample_pptx])
    hits = retriever.retrieve("When is the checkpoint due?", 5)
    assert hits
    assert all(0.0 <= h.score <= 1.0 for h in hits)


def test_real_qa_engine_end_to_end(retriever, sample_pdf, sample_pptx, tmp_path):
    llm = ScriptedLLM()
    components = registry.Components(llm, retriever, create_qa_engine(llm), FakeQuiz(),
                                     status={"llm": "real", "retriever": "real",
                                             "qa": "real", "quiz": "stub"})
    orch = Orchestrator(components, upload_dir=tmp_path / "uploads",
                        log_path=tmp_path / "logs" / "ai_log.jsonl")
    assert orch.upload([sample_pdf, sample_pptx]).ok

    answer = orch.ask("When is the checkpoint due?", [])
    assert answer.grounded
    assert answer.citations[0].source_file == "syllabus.pdf"
    assert answer.citations[0].location == "p.2"
    assert "18 October" in answer.citations[0].quote

    entry = json.loads(orch.log.path.read_text().splitlines()[0])
    assert entry["mode"] == "qa"
    assert entry["backend"]["model"] == "scripted"

"""Real retriever (Chroma) and real QA engine, wired through the orchestrator.

Skipped when the RAG dependencies (chromadb, sentence-transformers) aren't installed.
The first run downloads the embedding model.
"""

import json

import pytest

pytest.importorskip("chromadb")
pytest.importorskip("sentence_transformers")

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
def retriever(tmp_path, monkeypatch):
    r = ChromaRetriever()
    # Point Lichelle's store at a temp dir so tests never touch the real index.
    monkeypatch.setattr(r._store, "STORE_DIR", tmp_path / "store")
    return r


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

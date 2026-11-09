import json

import pytest

from backend import config, llm, registry
from backend.orchestrator import Orchestrator
from backend.quiz import create_quiz_engine
from backend.stubs import FakeQuiz, FakeRetriever


class ScriptedLLM:
    model_name = "scripted-quiz"

    def __init__(self, response: str) -> None:
        self.response = response
        self.requests = []

    def complete(self, system, messages, tools=None):
        self.requests.append(json.loads(messages[-1].content))
        return self.response


def checkpoint_question(**overrides):
    return {
        "question": "When is the checkpoint due?",
        "subtopic": "Checkpoint deadlines",
        "choices": ["2 October", "5 October", "18 October", "26 October"],
        "answer_index": 2,
        "chunk_id": "syllabus.pdf:p.2:0",
        "quote": "The checkpoint is due on 18 October at 23:59.",
    } | overrides


@pytest.fixture
def indexed_retriever(sample_pdf):
    retriever = FakeRetriever()
    retriever.ingest([sample_pdf])
    return retriever


@pytest.mark.parametrize("overrides", [
    {"chunk_id": "fabricated.pdf:p.2:0"},
    {"quote": "The checkpoint is due on 26 October at 23:59."},
    {"answer_index": 3},
    {"answer_index": True},
    {"choices": ["2 October", " 2 october ", "18 October", "26 October"]},
    {"subtopic": " "},
])
def test_generate_drops_invalid_questions(indexed_retriever, overrides):
    model = ScriptedLLM(json.dumps([checkpoint_question(**overrides)]))
    assert create_quiz_engine(model).generate("checkpoint", 3, indexed_retriever) == []


def test_generate_skips_model_call_when_topic_has_no_sources(indexed_retriever):
    model = ScriptedLLM("[]")
    assert create_quiz_engine(model).generate("photosynthesis", 3, indexed_retriever) == []
    assert model.requests == []


@pytest.mark.parametrize("response", ["Here are your questions!", "{}"])
def test_invalid_model_response_has_a_clear_error(indexed_retriever, response):
    with pytest.raises(ValueError, match="invalid quiz data"):
        create_quiz_engine(ScriptedLLM(response)).generate("checkpoint", 3, indexed_retriever)


def test_real_quiz_through_registry_and_orchestrator(monkeypatch, sample_pdf, tmp_path):
    checkpoint = checkpoint_question()
    proposal = {
        "question": "When is the proposal due?",
        "subtopic": "Proposal deadlines",
        "choices": ["18 October", "2 October", "20 October", "30 October"],
        "answer_index": 1,
        "chunk_id": "syllabus.pdf:p.1:0",
        "quote": "The project proposal is due on 2 October at 23:59.",
    }
    payload = json.dumps([checkpoint, checkpoint, proposal])
    model = ScriptedLLM(f"```json\n{payload}\n```")
    monkeypatch.setattr(llm, "create_llm", lambda: model, raising=False)
    monkeypatch.setattr(config, "BACKENDS", {
        "llm": "real", "retriever": "stub", "qa": "stub", "quiz": "real",
    })
    orch = Orchestrator(upload_dir=tmp_path / "uploads", log_path=tmp_path / "quiz.jsonl")
    assert orch.status["quiz"] == "real"
    assert orch.upload([sample_pdf]).ok

    session, message = orch.start_quiz("  checkpoint proposal  ", 3)
    assert session is not None
    assert "Generated 2" in message
    assert [q.id for q in session.questions] == ["q1", "q2"]
    assert session.current.choices == checkpoint["choices"]
    assert session.current.source.quote == checkpoint["quote"]
    assert model.requests[0]["topic"] == "checkpoint proposal"
    assert {source["id"] for source in model.requests[0]["sources"]} == {
        checkpoint["chunk_id"], proposal["chunk_id"],
    }

    assert orch.submit_answer(session, " 18  OCTOBER ").score == 1
    wrong = orch.submit_answer(session, "18 October")
    assert not wrong.correct and wrong.score == 0
    assert "2 October" in wrong.feedback
    summary = orch.quiz_summary(session)
    assert (summary.correct, summary.total) == (1, 2)
    assert summary.weak_topics == ["Proposal deadlines"]
    assert [(source.source_file, source.location) for source in summary.review] == [
        ("syllabus.pdf", "p.1"),
    ]
    assert len(model.requests) == 1


def test_real_quiz_uses_demo_when_llm_is_stub(monkeypatch):
    monkeypatch.setattr(config, "BACKENDS", {
        "llm": "stub", "retriever": "stub", "qa": "stub", "quiz": "real",
    })
    components = registry.build()
    assert isinstance(components.quiz, FakeQuiz)
    assert components.status["quiz"] == "stub"
    assert any("quiz" in warning and "real LLM" in warning for warning in components.warnings)

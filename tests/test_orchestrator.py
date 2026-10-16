import json

from backend import config, registry
from backend.interfaces import QAEngine, QuizEngine, Retriever, LLMClient
from backend.stubs import FakeLLM, FakeQA, FakeQuiz, FakeRetriever


def test_stubs_satisfy_the_team_contract():
    assert isinstance(FakeRetriever(), Retriever)
    assert isinstance(FakeQA(), QAEngine)
    assert isinstance(FakeQuiz(), QuizEngine)
    assert isinstance(FakeLLM(), LLMClient)


def test_ask_before_upload_is_handled(orch):
    answer = orch.ask("When is the checkpoint due?", [])
    assert not answer.grounded
    assert "Documents" in answer.text


def test_upload_then_ask_returns_cited_answer(orch, sample_pdf, sample_pptx):
    result = orch.upload([sample_pdf, sample_pptx])
    assert result.ok
    assert set(result.documents) == {"syllabus.pdf", "lecture.pptx"}

    answer = orch.ask("When is the checkpoint due?", [])
    assert answer.grounded
    assert answer.citations[0].source_file == "syllabus.pdf"
    assert answer.citations[0].location == "p.2"


def test_out_of_scope_question_is_ungrounded(orch, sample_pdf):
    orch.upload([sample_pdf])
    answer = orch.ask("Explain photosynthesis", [])
    assert not answer.grounded
    assert answer.citations == []


def test_unsupported_files_are_rejected(orch, tmp_path):
    txt = tmp_path / "notes.txt"
    txt.write_text("hello")
    result = orch.upload([txt])
    assert not result.ok


def test_quiz_flow_flags_weak_topics(orch, sample_pdf, sample_pptx):
    orch.upload([sample_pdf, sample_pptx])
    session, msg = orch.start_quiz("checkpoint proposal", 3)
    assert session is not None, msg
    assert session.questions

    while not session.finished:
        orch.submit_answer(session, "wrong answer")
    summary = orch.quiz_summary(session)
    assert summary.correct == 0
    assert summary.weak_topics == ["checkpoint proposal"]
    assert len(summary.review) == summary.total


def test_quiz_correct_answer_is_graded_correct(orch, sample_pdf):
    orch.upload([sample_pdf])
    session, _ = orch.start_quiz("checkpoint", 3)
    grade = orch.submit_answer(session, session.current.answer_key.upper())
    assert grade.correct


def test_ai_calls_are_logged(orch, sample_pdf):
    orch.upload([sample_pdf])
    orch.ask("When is the checkpoint due?", [])
    session, _ = orch.start_quiz("checkpoint", 3)
    orch.submit_answer(session, "x")

    entries = [json.loads(l) for l in orch.log.path.read_text().splitlines()]
    assert [e["mode"] for e in entries] == ["qa", "quiz_generate", "quiz_grade"]
    assert entries[0]["citations"][0]["location"] == "p.2"


def test_registry_falls_back_to_stub_when_real_module_missing(monkeypatch):
    monkeypatch.setitem(config.BACKENDS, "retriever", "real")
    components = registry.build()
    assert isinstance(components.retriever, FakeRetriever)
    assert components.status["retriever"] == "stub"
    assert any("retriever" in w for w in components.warnings)

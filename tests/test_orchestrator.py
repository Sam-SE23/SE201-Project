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
    # backend.quiz has no create_quiz_engine yet, so loading it fails
    monkeypatch.setitem(config.BACKENDS, "quiz", "real")
    components = registry.build()
    assert isinstance(components.quiz, FakeQuiz)
    assert components.status["quiz"] == "stub"
    assert any("quiz" in w for w in components.warnings)


def test_registry_warns_when_real_qa_uses_stub_llm(monkeypatch):
    monkeypatch.setitem(config.BACKENDS, "llm", "stub")   # independent of the local .env
    monkeypatch.setitem(config.BACKENDS, "qa", "real")
    components = registry.build()
    assert components.status["qa"] == "real"
    assert any("stub LLM" in w for w in components.warnings)


def test_remove_needs_the_real_retriever(orch, sample_pdf):
    orch.upload([sample_pdf])
    result = orch.remove("syllabus.pdf")
    assert not result.ok
    assert "STUDY_BUDDY_RETRIEVER=real" in result.message
    assert "syllabus.pdf" in orch.documents()


def test_stored_copy_delete_stays_inside_its_folder(tmp_path):
    from backend.files import delete_stored_copy

    folder = tmp_path / "uploads"
    folder.mkdir()
    (folder / "notes.pdf").write_bytes(b"x")
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"x")

    assert not delete_stored_copy(folder, "../outside.pdf")
    assert outside.exists()
    assert delete_stored_copy(folder, "notes.pdf")
    assert not (folder / "notes.pdf").exists()
    assert not delete_stored_copy(folder, "notes.pdf")   # already gone


def test_ui_decoration_is_stripped_from_history(tmp_path, sample_pdf):
    """Badges and the GUI's "not found" header must not reach the LLM as history."""
    from backend.interfaces import Answer, ChatTurn
    from backend.orchestrator import Orchestrator

    class RecordingQA:
        def answer(self, question, retriever, history):
            self.history = history
            return Answer("ok", grounded=True)

    qa = RecordingQA()
    components = registry.Components(FakeLLM(), FakeRetriever(), qa, FakeQuiz(),
                                     status={"llm": "stub", "retriever": "stub",
                                             "qa": "real", "quiz": "stub"})
    orch = Orchestrator(components, upload_dir=tmp_path / "uploads",
                        log_path=tmp_path / "logs" / "ai_log.jsonl")
    orch.upload([sample_pdf])
    history = [
        ChatTurn("user", "What is RAG?"),
        ChatTurn("assistant", "🟢 Grounding Confidence: 95% [Grounded in a.pdf]\n\n"
                              "RAG retrieves first [a.pdf, p.2]."),
        ChatTurn("user", "And photosynthesis?"),
        ChatTurn("assistant", "🔍 **Not found in your materials**\n\n"
                              "🔴 Grounding Confidence: 0% (Low Grounding / Fallback)\n\n"
                              "I cannot find information regarding this topic."),
    ]
    orch.ask("Why does it help?", history)

    sent = [(t.role, t.content) for t in qa.history]
    assert sent == [
        ("user", "What is RAG?"),
        ("assistant", "RAG retrieves first [a.pdf, p.2]."),
        ("user", "And photosynthesis?"),
        ("assistant", "I cannot find information regarding this topic."),
    ]


def test_ai_log_tab_reloads_only_when_an_entry_is_added(orch, sample_pdf):
    import gradio as gr
    from frontend.app import build_app

    app = build_app(orch)
    poll = next(f.fn for f in app.fns.values() if f.name == "poll")

    unchanged, seen = poll(None)                # no log file yet: nothing to reload
    assert unchanged == gr.skip() and seen is None

    orch.upload([sample_pdf])
    orch.ask("When is the checkpoint due?", [])
    rows, seen = poll(seen)                     # a new entry was written
    assert [r[1:3] for r in rows] == [["qa", "When is the checkpoint due?"]]

    unchanged, same = poll(seen)                # nothing new: leave the table alone
    assert same == seen
    assert unchanged == gr.skip()

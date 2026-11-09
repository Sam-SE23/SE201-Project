"""The evaluation harness: page-level citation checks, the Ctrl+F baseline and real mode."""

import json
import shutil

import pytest

import eval_runner
from backend import config
from backend.interfaces import ChatTurn
from backend.qa.qa_prompts import OUT_OF_SCOPE_FALLBACK_TEXT

EXPECTED = [{"source": "SE201_Week05_Generation_and_Evaluation.pdf", "pages": [16, 50]}]


@pytest.mark.parametrize("location", ["p.16", "Page 16", "slide 50", "pp. 15-16"])
def test_cites_expected_page(location):
    assert eval_runner.cites_expected(
        [("SE201_Week05_Generation_and_Evaluation.pdf", location)], EXPECTED)


def test_cites_expected_accepts_the_name_without_extension():
    assert eval_runner.cites_expected([("SE201_Week05_Generation_and_Evaluation", "p.50")], EXPECTED)


@pytest.mark.parametrize("citation", [
    ("SE201_Week05_Generation_and_Evaluation.pdf", "p.17"),   # wrong page
    ("SE201_Week04_Transformers_and_Attention.pdf", "p.16"),  # wrong file
])
def test_cites_expected_rejects_wrong_source(citation):
    assert not eval_runner.cites_expected([citation], EXPECTED)


def test_ctrl_f_searches_a_word_from_the_question():
    assert eval_runner.ctrl_f_term("When is the project checkpoint due?") == "checkpoint"
    assert eval_runner.ctrl_f_term("What does the temperature setting do during text generation?") \
        == "temperature"


def test_full_code_block_breaks_academic_integrity():
    code = "```python\n" + "\n".join(f"line_{i} = {i}" for i in range(10)) + "\n```"
    hints = "Here are some hints and steps to guide you [syllabus.pdf, p.2]."
    assert eval_runner.has_full_code_block(code)
    assert not eval_runner.has_full_code_block(hints)

    judged = eval_runner.judge_response("Write my project code", "Here are hints.\n" + code,
                                        [], ["hints"], "academic_integrity")
    assert judged["faithfulness"] == 0


def test_declining_graded_work_is_compliant():
    judged = eval_runner.judge_response("Write my reflection for me", OUT_OF_SCOPE_FALLBACK_TEXT,
                                        [], ["hints"], "academic_integrity")
    assert judged["overall_pass"]


def test_mock_mode_still_runs(tmp_path):
    out = tmp_path / "results.json"
    data = eval_runner.main(["--out", str(out), "--limit", "3"])
    assert out.exists()
    assert data["summary"]["total_questions"] == 3
    assert data["summary"]["model"] == eval_runner.BenchmarkLLMClient.model_name
    assert data["summary"]["metrics"]["correct_source_citation_pct"] is None


def test_real_mode_stops_without_a_model(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LLM_MODEL", "")
    with pytest.raises(SystemExit, match="STUDY_BUDDY_LLM_MODEL"):
        eval_runner.main(["--real", "--docs", str(tmp_path)])


class ScriptedLLM:
    model_name = "scripted"

    def complete(self, system: str, messages: list[ChatTurn], tools=None) -> str:
        return "The checkpoint is due on 18 October at 23:59 [syllabus.pdf, p.2]."


def test_real_mode_end_to_end(monkeypatch, tmp_path, sample_pdf):
    pytest.importorskip("chromadb")
    pytest.importorskip("sentence_transformers")
    pytest.importorskip("rank_bm25")
    import backend.llm
    monkeypatch.setattr(backend.llm, "create_llm", lambda: ScriptedLLM())

    docs = tmp_path / "docs"
    docs.mkdir()
    shutil.copy(sample_pdf, docs / sample_pdf.name)
    bench = tmp_path / "bench.json"
    bench.write_text(json.dumps([
        {"id": "t1", "category": "explicit_fact", "question": "When is the checkpoint due?",
         "ground_truth_keywords": ["18 October", "23:59"], "is_in_scope": True,
         "expected_sources": [{"source": "syllabus.pdf", "pages": [2]}]},
        {"id": "t2", "category": "out_of_scope", "question": "Explain photosynthesis in plants",
         "ground_truth_keywords": [], "is_in_scope": False},
    ]), encoding="utf-8")
    out = tmp_path / "results.json"

    data = eval_runner.main(["--real", "--docs", str(docs), "--benchmark", str(bench),
                             "--out", str(out)])

    summary, results = data["summary"], data["test_results"]
    assert summary["model"] == "scripted"
    assert summary["corpus_files"] == ["syllabus.pdf"]
    assert results[0]["cited_expected_page"] is True
    assert results[0]["passed"] is True
    assert results[0]["ctrl_f_phrase_hits"] == 0
    assert summary["metrics"]["correct_source_citation_pct"] == 100.0
    assert summary["metrics"]["fallback_accuracy_pct"] == 100.0
    assert json.loads(out.read_text(encoding="utf-8"))["summary"]["model"] == "scripted"

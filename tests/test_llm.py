"""LiteLLM client (backend/llm).

The unit tests mock LiteLLM and the Ollama server, so they run anywhere.
The `ollama` tests call a real local model and are skipped unless Ollama is
running with STUDY_BUDDY_LLM_MODEL pulled. Run them with: pytest -m ollama
"""

from types import SimpleNamespace

import pytest

pytest.importorskip("litellm")

import backend.llm as llm_module
from backend import config, registry
from backend.interfaces import ChatTurn, LLMClient
from backend.llm import LiteLLMClient, create_llm
from backend.stubs import FakeLLM
from frontend.formatting import status_line

MODEL = "ollama_chat/qwen3:8b"


def _reply(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


@pytest.fixture
def calls(monkeypatch):
    """Replace litellm.completion with a fake that records each call's kwargs."""
    recorded = []

    def fake_completion(**kwargs):
        recorded.append(kwargs)
        return _reply("The checkpoint is due on 18 October [syllabus.pdf, p.2].")

    monkeypatch.setattr(llm_module.litellm, "completion", fake_completion)
    return recorded


@pytest.fixture
def client():
    return LiteLLMClient(MODEL, "http://127.0.0.1:11434", num_ctx=8192, timeout=30)


@pytest.fixture
def ollama_config(monkeypatch):
    monkeypatch.setattr(config, "LLM_MODEL", MODEL)
    monkeypatch.setattr(config, "OLLAMA_API_BASE", "http://127.0.0.1:11434")


# --- LiteLLMClient.complete ---------------------------------------------------

def test_client_satisfies_the_team_contract(client):
    assert isinstance(client, LLMClient)
    assert client.model_name == MODEL


def test_complete_sends_system_prompt_first_and_keeps_roles(client, calls):
    history = [ChatTurn("user", "What is due?"), ChatTurn("assistant", "Which one?")]
    text = client.complete("Only answer from the sources.", history + [ChatTurn("user", "The checkpoint")])

    assert text == "The checkpoint is due on 18 October [syllabus.pdf, p.2]."
    sent = calls[0]
    assert sent["model"] == MODEL
    assert sent["messages"] == [
        {"role": "system", "content": "Only answer from the sources."},
        {"role": "user", "content": "What is due?"},
        {"role": "assistant", "content": "Which one?"},
        {"role": "user", "content": "The checkpoint"},
    ]


def test_complete_sends_ollama_settings_but_no_sampling_params(client, calls):
    client.complete("sys", [ChatTurn("user", "hi")])
    sent = calls[0]
    assert sent["api_base"] == "http://127.0.0.1:11434"
    assert sent["num_ctx"] == 8192
    assert sent["timeout"] == 30
    assert "temperature" not in sent


def test_hosted_models_get_no_ollama_settings(calls):
    LiteLLMClient("claude-sonnet-5-5", "http://127.0.0.1:11434", 8192, 30).complete(
        "sys", [ChatTurn("user", "hi")])
    assert "api_base" not in calls[0] and "num_ctx" not in calls[0]


def test_hosted_model_gets_the_universal_api_key(calls):
    LiteLLMClient("anthropic/claude-sonnet-5-5", "http://127.0.0.1:11434", 8192, 30,
                  api_key="sk-test").complete("sys", [ChatTurn("user", "hi")])
    assert calls[0]["api_key"] == "sk-test"


def test_ollama_gets_no_api_key(calls):
    LiteLLMClient(MODEL, "http://127.0.0.1:11434", 8192, 30, api_key="sk-test").complete(
        "sys", [ChatTurn("user", "hi")])
    assert "api_key" not in calls[0]


def test_rejected_api_key_says_to_check_it(monkeypatch):
    def reject(**kwargs):
        raise llm_module.litellm.AuthenticationError(
            message="invalid x-api-key", llm_provider="anthropic", model="claude-sonnet-5-5")

    monkeypatch.setattr(llm_module.litellm, "completion", reject)
    client = LiteLLMClient("anthropic/claude-sonnet-5-5", "", 8192, 30, api_key="wrong")
    with pytest.raises(RuntimeError, match="STUDY_BUDDY_LLM_API_KEY"):
        client.complete("sys", [ChatTurn("user", "hi")])


def test_reasoning_block_is_stripped(client, monkeypatch):
    monkeypatch.setattr(llm_module.litellm, "completion",
                        lambda **kw: _reply("<think>\nLet me check p.2.\n</think>\n\nDue 18 October."))
    assert client.complete("sys", [ChatTurn("user", "hi")]) == "Due 18 October."


def test_empty_reply_becomes_empty_string(client, monkeypatch):
    monkeypatch.setattr(llm_module.litellm, "completion", lambda **kw: _reply(None))
    assert client.complete("sys", [ChatTurn("user", "hi")]) == ""


def test_tools_are_rejected(client):
    with pytest.raises(NotImplementedError):
        client.complete("sys", [ChatTurn("user", "hi")], tools=[{"name": "search"}])


def test_connection_error_says_ollama_is_unreachable(client, monkeypatch):
    def refuse(**kwargs):
        raise llm_module.litellm.APIConnectionError(
            message="Connection refused", llm_provider="ollama", model=MODEL)

    monkeypatch.setattr(llm_module.litellm, "completion", refuse)
    with pytest.raises(RuntimeError, match="Can't reach Ollama at http://127.0.0.1:11434"):
        client.complete("sys", [ChatTurn("user", "hi")])


# --- create_llm ---------------------------------------------------------------

def test_create_llm_needs_a_model(monkeypatch):
    monkeypatch.setattr(config, "LLM_MODEL", "")
    with pytest.raises(ValueError, match="STUDY_BUDDY_LLM_MODEL"):
        create_llm()


def test_create_llm_reports_unreachable_ollama(ollama_config, monkeypatch):
    def unreachable(api_base):
        raise OSError("Connection refused")

    monkeypatch.setattr(llm_module, "_ollama_models", unreachable)
    with pytest.raises(RuntimeError, match="Can't reach Ollama"):
        create_llm()


def test_create_llm_reports_model_not_pulled(ollama_config, monkeypatch):
    monkeypatch.setattr(llm_module, "_ollama_models", lambda api_base: {"llama3.1:latest"})
    with pytest.raises(RuntimeError, match=r"ollama pull qwen3:8b"):
        create_llm()


def test_create_llm_returns_client_when_model_is_pulled(ollama_config, monkeypatch):
    monkeypatch.setattr(llm_module, "_ollama_models", lambda api_base: {"qwen3:8b"})
    llm = create_llm()
    assert isinstance(llm, LiteLLMClient)
    assert llm.model_name == MODEL


def test_tag_without_version_means_latest(monkeypatch):
    monkeypatch.setattr(config, "LLM_MODEL", "ollama_chat/llama3.1")
    monkeypatch.setattr(llm_module, "_ollama_models", lambda api_base: {"llama3.1:latest"})
    assert create_llm().model_name == "ollama_chat/llama3.1"


HOSTED = ["anthropic/claude-haiku-5-5"]
PROVIDER_KEYS = ["ANTHROPIC_API_KEY"]


@pytest.fixture
def no_provider_keys(monkeypatch):
    for name in PROVIDER_KEYS:
        monkeypatch.delenv(name, raising=False)

    def no_ollama_check(api_base):
        raise AssertionError("hosted models must not check Ollama")

    monkeypatch.setattr(llm_module, "_ollama_models", no_ollama_check)


@pytest.mark.parametrize("model", HOSTED)
def test_hosted_model_needs_an_api_key(model, no_provider_keys, monkeypatch):
    monkeypatch.setattr(config, "LLM_MODEL", model)
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    with pytest.raises(ValueError, match="STUDY_BUDDY_LLM_API_KEY"):
        create_llm()


@pytest.mark.parametrize("model", HOSTED)
def test_hosted_model_with_universal_key(model, no_provider_keys, monkeypatch):
    monkeypatch.setattr(config, "LLM_MODEL", model)
    monkeypatch.setattr(config, "LLM_API_KEY", "sk-test")
    llm = create_llm()
    assert llm.model_name == model


def test_provider_variable_still_works_as_a_fallback(no_provider_keys, monkeypatch):
    monkeypatch.setattr(config, "LLM_MODEL", "anthropic/claude-sonnet-5-5")
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert create_llm().model_name == "anthropic/claude-sonnet-5-5"


# --- App wiring ---------------------------------------------------------------

def test_registry_falls_back_to_stub_llm_without_a_model(monkeypatch):
    monkeypatch.setitem(config.BACKENDS, "llm", "real")
    monkeypatch.setattr(config, "LLM_MODEL", "")
    components = registry.build()
    assert isinstance(components.llm, FakeLLM)
    assert components.status["llm"] == "stub"
    assert any("STUDY_BUDDY_LLM_MODEL" in w for w in components.warnings)


def test_status_line_shows_the_model_when_llm_is_real():
    line = status_line({"llm": "real", "qa": "real"}, [], MODEL)
    assert f"llm: `real` ({MODEL})" in line
    assert MODEL not in status_line({"llm": "stub"}, [], "stub")


# --- Real Ollama (pytest -m ollama) -------------------------------------------

def _ollama_ready() -> bool:
    if not config.LLM_MODEL.startswith("ollama"):
        return False
    try:
        return llm_module._ollama_tag(config.LLM_MODEL) in llm_module._ollama_models(config.OLLAMA_API_BASE)
    except Exception:  # noqa: BLE001 - any failure means "not available here"
        return False


needs_ollama = pytest.mark.skipif(
    not _ollama_ready(), reason="needs Ollama running with STUDY_BUDDY_LLM_MODEL pulled")


@pytest.mark.ollama
@needs_ollama
def test_real_model_replies():
    reply = create_llm().complete("Answer in one short sentence.", [ChatTurn("user", "Say hello.")])
    assert reply.strip()


@pytest.mark.ollama
@needs_ollama
def test_real_model_gives_a_grounded_cited_answer(tmp_path, sample_pdf):
    pytest.importorskip("chromadb")
    from backend.qa import create_qa_engine
    from backend.retrieval import ChromaRetriever

    retriever = ChromaRetriever(store_dir=tmp_path / "store")
    retriever.ingest([sample_pdf])
    answer = create_qa_engine(create_llm()).answer("When is the checkpoint due?", retriever, [])

    assert answer.grounded
    assert any(c.source_file == "syllabus.pdf" for c in answer.citations)

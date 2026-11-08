"""Real LLM client, called through LiteLLM.

Provides:
    create_llm() -> LLMClient   # see backend/interfaces.py

The model comes from STUDY_BUDDY_LLM_MODEL in .env. "ollama_chat/<tag>" uses a
local Ollama model; a hosted model such as "anthropic/claude-sonnet-5-5" or
"gemini/<model>" uses that provider instead, with its key in
STUDY_BUDDY_LLM_API_KEY. Switching needs no code change.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

# Use LiteLLM's bundled price list instead of fetching it from GitHub on import,
# which is slow and fails offline.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

import litellm  # noqa: E402

from backend import config  # noqa: E402
from backend.interfaces import ChatTurn, LLMClient  # noqa: E402

litellm.suppress_debug_info = True

# Reasoning models (qwen3, deepseek-r1, ...) can put their reasoning before the
# answer. It would confuse the QA engine's citation parser, so it is removed.
_THINK_BLOCK = re.compile(r"^\s*<think>.*?</think>\s*", re.DOTALL)


def _is_ollama(model: str) -> bool:
    return model.startswith("ollama")


def _ollama_tag(model: str) -> str:
    """'ollama_chat/qwen3:8b' -> 'qwen3:8b'; a tag without a version means ':latest'."""
    tag = model.split("/", 1)[1] if "/" in model else model
    return tag if ":" in tag else f"{tag}:latest"


def _ollama_models(api_base: str) -> set[str]:
    """Return the tags of the models pulled into the Ollama server at api_base."""
    with urllib.request.urlopen(f"{api_base.rstrip('/')}/api/tags", timeout=3) as response:
        data = json.load(response)
    return {m["name"] for m in data.get("models", [])}


class LiteLLMClient:
    def __init__(self, model: str, api_base: str, num_ctx: int, timeout: float,
                 api_key: str = "") -> None:
        self.model_name = model
        self.api_base = api_base
        self.num_ctx = num_ctx
        self.timeout = timeout
        self._api_key = api_key
        if _is_ollama(model):
            # On every call LiteLLM also looks up the model's details at
            # OLLAMA_API_BASE (env var), ignoring the api_base argument. Point it
            # at the same server, or each call waits ~8 s on a refused connection.
            os.environ["OLLAMA_API_BASE"] = api_base

    def complete(self, system: str, messages: list[ChatTurn],
                 tools: list[dict] | None = None) -> str:
        if tools:
            raise NotImplementedError("LiteLLMClient doesn't support tools; no caller uses them yet")

        kwargs = {}
        if _is_ollama(self.model_name):
            # Ollama-only settings. No temperature or other sampling parameters,
            # so the same call also works for hosted models that reject them.
            kwargs = {"api_base": self.api_base, "num_ctx": self.num_ctx}
        elif self._api_key:
            # One provider-neutral key; without it LiteLLM reads the provider's own variable.
            kwargs = {"api_key": self._api_key}
        try:
            response = litellm.completion(
                model=self.model_name,
                messages=[{"role": "system", "content": system}]
                + [{"role": t.role, "content": t.content} for t in messages],
                timeout=self.timeout,
                **kwargs,
            )
        except (litellm.APIConnectionError, litellm.Timeout) as e:
            if _is_ollama(self.model_name):
                raise RuntimeError(f"Can't reach Ollama at {self.api_base}. Is Ollama running?") from e
            raise RuntimeError(f"Can't reach the LLM provider for {self.model_name}: {e}") from e
        except litellm.AuthenticationError as e:
            raise RuntimeError(f"The provider rejected the API key for {self.model_name}. "
                               "Check STUDY_BUDDY_LLM_API_KEY in .env.") from e

        text = response.choices[0].message.content or ""
        return _THINK_BLOCK.sub("", text, count=1)


def create_llm() -> LLMClient:
    model = config.LLM_MODEL.strip()
    if not model:
        raise ValueError("Set STUDY_BUDDY_LLM_MODEL in .env (e.g. ollama_chat/qwen3:8b)")

    if _is_ollama(model):
        # Check now, so a problem shows in the status line at startup rather
        # than on the first question.
        try:
            pulled = _ollama_models(config.OLLAMA_API_BASE)
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise RuntimeError(f"Can't reach Ollama at {config.OLLAMA_API_BASE}. "
                               "Start Ollama, then restart the app.") from e
        tag = _ollama_tag(model)
        if tag not in pulled:
            raise RuntimeError(f"Model '{tag}' isn't pulled. Run: ollama pull {tag}")
    elif not config.LLM_API_KEY:
        # Hosted model with no STUDY_BUDDY_LLM_API_KEY: only fine if the
        # provider's own variable (e.g. ANTHROPIC_API_KEY) is set.
        env = litellm.validate_environment(model)
        if not env.get("keys_in_environment") and env.get("missing_keys"):
            raise ValueError(f"Set STUDY_BUDDY_LLM_API_KEY in .env (the API key for {model})")

    return LiteLLMClient(model, config.OLLAMA_API_BASE, config.LLM_NUM_CTX, config.LLM_TIMEOUT,
                         api_key=config.LLM_API_KEY)

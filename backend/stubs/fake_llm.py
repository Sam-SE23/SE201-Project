"""Stub LLM client. Replace with a Claude or GPT client behind the same interface."""

from __future__ import annotations

from backend.interfaces import ChatTurn


class FakeLLM:
    model_name = "stub"

    def complete(self, system: str, messages: list[ChatTurn],
                 tools: list[dict] | None = None) -> str:
        last = messages[-1].content if messages else ""
        return f"[STUB LLM] You said: {last}"

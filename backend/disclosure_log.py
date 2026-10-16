"""Append-only JSONL log of every AI interaction.

Each line records what was asked, what was retrieved, and what the AI said.
This keeps AI use transparent, and it is the raw data for the accuracy and
hallucination evaluation.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DisclosureLog:
    def __init__(self, path: Path) -> None:
        self.path = path

    def record(self, mode: str, backend: dict[str, str], **fields: Any) -> None:
        """mode: "qa", "quiz_generate" or "quiz_grade"."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "mode": mode,
            "backend": backend,
            **{k: _plain(v) for k, v in fields.items()},
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def tail(self, n: int = 20) -> list[dict]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()[-n:]
        return [json.loads(line) for line in lines]


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value

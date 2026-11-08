"""Bounded sanitization for instruction-like document text."""

import re
from dataclasses import dataclass


_SUSPICIOUS_PATTERNS = (
    re.compile(
        r"\b(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above)\s+"
        r"(instructions?|rules?|context)",
        re.IGNORECASE,
    ),
    re.compile(r"\b(system|developer)\s+message\s*:", re.IGNORECASE),
    re.compile(
        r"\b(reveal|print|show|disclose)\b.{0,80}\b(prompt|instructions?|"
        r"secrets?|credentials?|keys?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(you are now|act as|pretend to be)\b", re.IGNORECASE),
    re.compile(
        r"\b(run|execute)\s+(this|the following)\s+(command|script|code)\b",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True)
class SanitizedText:
    text: str
    original_text: str
    suspicious: bool
    warning: str | None = None


def sanitize_text(text: str) -> SanitizedText:
    """Remove suspicious instruction-like lines without broad text rewriting."""
    original_text = text
    kept_lines = []
    removed = 0
    for line in text.splitlines():
        if any(pattern.search(line) for pattern in _SUSPICIOUS_PATTERNS):
            removed += 1
            continue
        kept_lines.append(line)

    sanitized = "\n".join(kept_lines).strip()
    warning = (
        f"Removed {removed} instruction-like line(s) from indexed content."
        if removed
        else None
    )
    return SanitizedText(sanitized, original_text, bool(removed), warning)

"""Snapshot post-processing: line-aware truncation."""

from __future__ import annotations


def truncate_snapshot(text: str, max_chars: int = 8000) -> str:
    """Truncate a snapshot by whole lines so element rows aren't split mid-token.

    Returns ``text`` unchanged when within budget; otherwise keeps as many full
    lines as fit under ``max_chars`` and appends a count of omitted lines.
    """
    if len(text) <= max_chars:
        return text
    lines = text.split("\n")
    result: list[str] = []
    chars = 0
    for line in lines:
        if chars + len(line) + 1 > max_chars - 80:
            break
        result.append(line)
        chars += len(line) + 1
    omitted = len(lines) - len(result)
    result.append(f"\n[... {omitted} lines truncated ...]")
    return "\n".join(result)

"""Shared helpers for the schema render scaffold: optional-float coercion
and the Chinese i18n gloss (canonical English token preserved for parsers)."""

from __future__ import annotations


# LLMs sometimes write a placeholder string ("None", "N/A", ...) into an optional
# numeric field instead of omitting it. Coerce those to None so the structured
# call validates instead of erroring (#1058). Pydantic still parses real numeric
# strings ("189.5") to float.
_NULLISH_FLOAT = {"", "none", "n/a", "na", "null", "nil", "-", "tbd", "unknown"}


def _coerce_optional_float(value):
    if isinstance(value, str) and value.strip().lower() in _NULLISH_FLOAT:
        return None
    return value


# Chinese display labels for the deterministic render scaffold. The canonical
# ENGLISH enum values still travel in each report's header (e.g. "Bullish",
# "High"), appended after the Chinese label so the scoring parsers in rating.py
# keep matching; these maps add a Chinese gloss for the reader.
_DIRECTION_CN = {
    "Bullish": "看涨", "Mildly Bullish": "温和看涨", "Neutral": "中性",
    "Mixed": "分化", "Mildly Bearish": "温和看跌", "Bearish": "看跌",
}


_CONF_CN = {"low": "低", "medium": "中", "high": "高"}


def _dir_cn(value: str) -> str:
    """`Bullish` -> `看涨 Bullish` (keeps the English token for the parsers)."""
    cn = _DIRECTION_CN.get(value)
    return f"{cn} {value}" if cn else value


def _conf_cn(value: str) -> str:
    """`high` -> `高 High`."""
    cn = _CONF_CN.get((value or "").lower())
    return f"{cn} {value.capitalize()}" if cn else value.capitalize()


def _coerce_str_list(v):
    """Coerce a list[dict|str|other] to list[str].

    DeepSeek's response_format sometimes emits ``list[dict]`` for ``list[str]``
    fields — e.g. key_evidence/risks come back as
    ``[{'description': ..., 'type': 'string'}]`` instead of ``[str]``, which
    fails Pydantic validation and forces the agent loop to degrade to free
    text. It also sometimes JSON-encodes a list as a STRING
    (``'["a", "b"]'``) — parse that first. Coerce each item: dict -> its
    'description' (or first str value), anything else -> str(item). Non-list
    values pass through unchanged so Pydantic still catches a genuinely wrong
    type.
    """
    if isinstance(v, str):
        # LLM JSON-encoded a list as a string: '["a", "b"]' -> ["a", "b"].
        import json

        try:
            parsed = json.loads(v)
        except (json.JSONDecodeError, ValueError):
            parsed = None
        if isinstance(parsed, list):
            v = parsed
    if not isinstance(v, list):
        return v
    out = []
    for item in v:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            s = item.get("description") or next(
                (x for x in item.values() if isinstance(x, str)), None
            )
            out.append(s if s else str(item))
        else:
            out.append(str(item))
    return out

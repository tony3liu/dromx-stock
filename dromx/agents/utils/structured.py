"""Shared helpers for invoking an agent with structured output and a graceful fallback.

The Portfolio Manager, Trader, and Research Manager all follow the same
canonical pattern:

1. At agent creation, wrap the LLM with ``with_structured_output(Schema)``
   so the model returns a typed Pydantic instance. If the provider does
   not support structured output (rare; mostly older Ollama models), the
   wrap is skipped and the agent uses free-text generation instead.
2. At invocation, run the structured call and render the result back to
   markdown. If the structured call itself fails for any reason
   (malformed JSON from a weak model, transient provider issue), fall
   back to a plain ``llm.invoke`` so the pipeline never blocks.

Centralising the pattern here keeps the agent factories small and ensures
all three agents log the same warnings when fallback fires.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def bind_structured(llm: Any, schema: type[T], agent_name: str) -> Any | None:
    """Return ``llm.with_structured_output(schema)`` or ``None`` if unsupported.

    Logs a warning when the binding fails so the user understands the agent
    will use free-text generation for every call instead of one-shot fallback.
    """
    try:
        return llm.with_structured_output(schema)
    except (NotImplementedError, AttributeError) as exc:
        logger.warning(
            "%s: provider does not support with_structured_output (%s); "
            "falling back to free-text generation",
            agent_name, exc,
        )
        return None


def _strip_code_fence(text: str) -> str:
    """Strip a leading/trailing ```json … ``` fence if the model wrapped its output."""
    s = text.strip()
    m = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```$", s, re.DOTALL)
    return m.group(1).strip() if m else s


def _extract_json_blob(text: str) -> str | None:
    """Return the outermost {...} / [...] JSON substring in ``text``, or None.

    A free-text fallback often returns the JSON the structured call wanted —
    sometimes wrapped in prose or a code fence. We pull the first balanced
    object/array so it can be re-parsed instead of shown to the user raw.
    """
    s = _strip_code_fence(text)
    start = next((i for i, c in enumerate(s) if c in "{["), -1)
    if start == -1:
        return None
    open_ch = s[start]
    close_ch = "}" if open_ch == "{" else "]"
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


def _recover_from_freetext(
    text: str,
    schema: type[T] | None,
    render: Callable[[T], str],
    agent_name: str,
) -> str | None:
    """Try to turn a free-text JSON dump back into proper rendered markdown.

    Weak models, when they miss the structured-output tool, frequently emit the
    schema's JSON as plain text. Showing that raw is the bug behind "the report
    is a wall of JSON". If the fallback text contains the schema's JSON, validate
    and render it the normal way; failing that, pretty-print any JSON object as
    readable markdown rather than a one-line blob. Returns None if nothing
    JSON-like is present (so the caller keeps the prose as-is).
    """
    blob = _extract_json_blob(text)
    if blob is None:
        return None

    if schema is not None:
        try:
            return render(schema.model_validate_json(blob))
        except (ValidationError, ValueError) as exc:
            logger.warning("%s: free-text JSON did not match schema (%s); "
                           "pretty-printing instead", agent_name, exc)

    try:
        data = json.loads(blob)
    except (json.JSONDecodeError, ValueError):
        return None
    return _json_to_markdown(data)


def _json_to_markdown(data: Any, depth: int = 0) -> str:
    """Schema-agnostic readable markdown for an arbitrary parsed-JSON value."""
    pad = "  " * depth
    if isinstance(data, dict):
        lines = []
        for k, v in data.items():
            label = str(k).replace("_", " ")
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}- **{label}:**")
                lines.append(_json_to_markdown(v, depth + 1))
            else:
                lines.append(f"{pad}- **{label}:** {v}")
        return "\n".join(lines)
    if isinstance(data, list):
        return "\n".join(_json_to_markdown(item, depth) for item in data)
    return f"{pad}{data}"


def invoke_structured_or_freetext(
    structured_llm: Any | None,
    plain_llm: Any,
    prompt: Any,
    render: Callable[[T], str],
    agent_name: str,
    schema: type[T] | None = None,
) -> str:
    """Run the structured call and render to markdown; fall back to free-text on any failure.

    ``prompt`` is whatever the underlying LLM accepts (a string for chat
    invocations, a list of message dicts for chat models that take that
    shape). The same value is forwarded to the free-text path so the
    fallback sees the same input the structured call did.

    When ``schema`` is given, the free-text fallback additionally tries to
    recover a JSON dump (a common weak-model failure) back into properly
    rendered markdown, so the user never sees a raw-JSON report.
    """
    if structured_llm is not None:
        # A thinking model (DeepSeek) sometimes answers in plain text instead of
        # calling the structured tool, leaving the parser with None. Retry ONCE on
        # that specific miss before falling back to free text — the second call
        # usually does call the tool.
        for _attempt in (1, 2):
            try:
                result = structured_llm.invoke(prompt)
            except Exception as exc:
                logger.warning(
                    "%s: structured-output invocation failed (%s); falling back to free text",
                    agent_name, exc,
                )
                break  # exception -> free-text fallback below
            if result is not None:
                return render(result)
            if _attempt == 1:
                logger.info(
                    "%s: structured output returned no parsed result; retrying once",
                    agent_name,
                )
        else:
            # loop completed with no return and no break -> None twice
            logger.warning(
                "%s: structured output returned no parsed result after retry; using free text",
                agent_name,
            )

    response = plain_llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)

    recovered = _recover_from_freetext(content, schema, render, agent_name)
    if recovered is not None:
        logger.info("%s: recovered structured content from a free-text JSON dump", agent_name)
        return recovered
    return content

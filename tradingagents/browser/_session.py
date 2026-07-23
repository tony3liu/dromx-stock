"""Browser session management: one browser instance per task_id."""

from __future__ import annotations

import uuid

_sessions: dict[str, str] = {}


def get_or_create_session(task_id: str = "default") -> str:
    """Return a stable agent-browser session name for ``task_id``.

    The same task_id reuses the same session (so consecutive navigate/snapshot
    calls hit one Chromium instead of relaunching). Different task_ids isolate.
    """
    tid = task_id or "default"
    if tid not in _sessions:
        _sessions[tid] = f"ta_{uuid.uuid4().hex[:10]}"
    return _sessions[tid]

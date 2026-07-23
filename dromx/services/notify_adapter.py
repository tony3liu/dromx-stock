"""System-native notification adapter (ported from TickFlow).

Pushes an alert to the OS notification center so it shows even when the app
window is minimised / backgrounded (independent of any web UI):

  - macOS:   osascript (built in, no extra dependency)
  - Linux:   notify-send (freedesktop standard)
  - Windows: winotify (optional; degrades silently if absent)

Design: failures degrade silently and never raise — a notification is an
auxiliary channel and must not block the alert's primary path (persist / SSE).
"""
from __future__ import annotations

import logging
import subprocess
import sys

logger = logging.getLogger(__name__)

_MAX_LEN = 200  # per-notification cap (avoid platform truncation errors)
_backend_cache: str | None = None


def _detect_backend() -> str | None:
    """Detect the available notification backend for this platform (cached)."""
    global _backend_cache
    if _backend_cache is not None:
        return _backend_cache if _backend_cache != "none" else None

    backend: str | None = None
    if sys.platform == "win32":
        try:
            import winotify  # type: ignore[import-not-found]  # noqa: F401

            backend = "winotify"
        except ImportError:
            backend = None
    elif sys.platform == "darwin":
        backend = "osascript"
    elif sys.platform.startswith("linux"):
        backend = "notify-send"

    _backend_cache = backend or "none"
    return backend


def _truncate(text: str) -> str:
    text = (text or "").strip()
    return text[:_MAX_LEN] + ("…" if len(text) > _MAX_LEN else "")


def is_available() -> bool:
    """Whether a system-notification backend exists on this platform."""
    return _detect_backend() is not None


def notify(title: str, message: str) -> bool:
    """Push one system notification. True on success; False (silent) otherwise."""
    title = _truncate(title)
    message = _truncate(message)
    if not title:
        return False

    backend = _detect_backend()
    if backend is None:
        return False

    try:
        if backend == "winotify":
            return _notify_winotify(title, message)
        if backend == "osascript":
            return _notify_osascript(title, message)
        if backend == "notify-send":
            return _notify_notify_send(title, message)
    except Exception as e:  # noqa: BLE001 — auxiliary channel, never raise
        logger.debug("system notify failed (%s): %s", backend, e)
        return False
    return False


def _notify_winotify(title: str, message: str) -> bool:
    from winotify import Notifier  # type: ignore[import-not-found]

    Notifier().create_notification(title=title, msg=message, duration="short").show()
    return True


def _notify_osascript(title: str, message: str) -> bool:
    safe_title = title.replace('"', '\\"')
    safe_msg = message.replace('"', '\\"')
    script = f'display notification "{safe_msg}" with title "{safe_title}"'
    result = subprocess.run(  # noqa: S603, S607
        ["osascript", "-e", script], capture_output=True, timeout=5,
    )
    return result.returncode == 0


def _notify_notify_send(title: str, message: str) -> bool:
    result = subprocess.run(  # noqa: S603
        ["notify-send", title, message], capture_output=True, timeout=5,
    )
    return result.returncode == 0

"""agent-browser CLI discovery + subprocess invocation.

Mirrors Hermes ``tools/browser_tool.py`` (_find_agent_browser L1751,
_run_browser_command L1875). The one non-obvious thing — and the reason this
isn't a plain ``subprocess.run(capture_output=True)`` — is that agent-browser
spawns a background daemon that inherits the CLI's stdio file descriptors. With
pipes, the daemon holds the pipe fds open after the CLI exits, so the parent's
read never sees EOF and blocks until the timeout. We therefore redirect stdout/
stderr to TEMP FILES and read them back after the process exits.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

_INSTALL_HINT = (
    "agent-browser CLI not found. Install Node.js, then run: "
    "npx agent-browser install --with-deps"
)


def find_agent_browser() -> str:
    """Locate the agent-browser CLI.

    Order: PATH → repo-local node_modules/.bin → ``npx agent-browser`` fallback.
    Raises FileNotFoundError (with an install hint) when nothing works.
    """
    path = shutil.which("agent-browser")
    if path:
        return path

    # repo root = three levels up from this file (tradingagents/browser/_cli.py)
    local_bin = Path(__file__).resolve().parents[2] / "node_modules" / ".bin" / "agent-browser"
    if local_bin.exists():
        return str(local_bin)

    if shutil.which("npx"):
        return "npx agent-browser"

    raise FileNotFoundError(_INSTALL_HINT)


def _build_cmd(browser_bin: str, session: str, command: str, args: list[str]) -> list[str]:
    """Build: <bin> --session <name> --json <command> [args...].

    Local mode uses ``--session`` (launches a local headless Chromium); we do
    not use cloud ``--cdp`` here.
    """
    if browser_bin == "npx agent-browser":
        prefix = [shutil.which("npx") or "npx", "agent-browser"]
    else:
        prefix = [browser_bin]
    return prefix + ["--session", session, "--json", command] + args


def run_browser_command(
    session: str,
    command: str,
    args: list[str] | None = None,
    timeout: int = 30,
) -> dict:
    """Run one agent-browser command and return the parsed JSON dict.

    Never raises — on any failure (CLI missing, timeout, non-JSON, empty) it
    returns ``{"success": False, "error": ...}`` so callers degrade gracefully.
    Uses temp files for stdout/stderr (see module docstring on why not pipes).
    """
    args = args or []
    try:
        browser_bin = find_agent_browser()
    except FileNotFoundError as exc:
        return {"success": False, "error": str(exc)}

    cmd = _build_cmd(browser_bin, session, command, args)
    tmpdir = tempfile.mkdtemp(prefix="tabrowser-")
    stdout_p = os.path.join(tmpdir, "stdout")
    stderr_p = os.path.join(tmpdir, "stderr")

    try:
        stdout_fd = os.open(stdout_p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        stderr_fd = os.open(stderr_p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            proc = subprocess.Popen(
                cmd, stdout=stdout_fd, stderr=stderr_fd, stdin=subprocess.DEVNULL
            )
        finally:
            os.close(stdout_fd)
            os.close(stderr_fd)

        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            return {"success": False, "error": f"Browser command '{command}' timed out ({timeout}s)"}

        with open(stdout_p, encoding="utf-8") as f:
            stdout = f.read().strip()

        if not stdout:
            with open(stderr_p, encoding="utf-8") as f:
                stderr = f.read().strip()
            return {
                "success": False,
                "error": f"Browser command '{command}' returned no output"
                + (f": {stderr[:300]}" if stderr else ""),
            }

        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return {"success": False, "error": f"Non-JSON output from '{command}': {stdout[:300]}"}
    except Exception as exc:  # noqa: BLE001 — browser is best-effort, never raise
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

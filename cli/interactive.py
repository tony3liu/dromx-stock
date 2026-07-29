"""Interactive follow-up loop after an analysis completes.

Once the graph has produced a final state, the user can ask follow-up questions
about the report without re-running the pipeline. The full state is summarized
ONCE (deterministic, no LLM), then each question is one quick-LLM call against
that summary. History is kept but trimmed so context stays bounded.

Skips itself automatically when stdin is not a TTY (cron / piped / headless), so
a non-interactive run never blocks.
"""

from __future__ import annotations

import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from dromx.core.report_summarizer import summarize_state
from cli.qa_agent import answer_question

console = Console()

_EXIT_WORDS = {"exit", "quit", "q", ":q", "bye", "退出"}
_MAX_TURNS = 8  # keep at most this many prior Q/A pairs in context


def _is_interactive() -> bool:
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except Exception:  # noqa: BLE001
        return False


def _ensure_utf8_stdio() -> None:
    """Best-effort: reconfigure stdout (and stdin if it takes) to UTF-8.

    This helps rich render non-ASCII output. Input itself is read at the byte
    level by ``_read_question`` below, which is robust even when reconfigure()
    has no effect on the wrapped stdin stream.
    """
    for stream in (sys.stdin, sys.stdout):
        try:
            enc = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
            if enc not in ("utf8", "utf8mb4") and hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 — never block Q&A over stdio tweaks
            pass


def _read_question(prompt: str) -> str | None:
    """Read one line, decoding UTF-8 ourselves so Chinese never crashes.

    Python's text-mode stdin decodes with the locale encoding; on a non-UTF-8
    terminal that raises UnicodeDecodeError on Chinese input, and stream
    reconfigure() doesn't always take. We instead read RAW BYTES from the stdin
    file descriptor and decode UTF-8 with errors="replace" — locale-independent.
    Returns the line (without trailing newline), or None on EOF.
    """
    # Print the prompt via rich so styling/encoding on the output side is handled.
    console.print(prompt, end="")
    # Prefer the underlying binary buffer; fall back to os.read on the fd.
    buf = getattr(sys.stdin, "buffer", None)
    try:
        if buf is not None:
            raw = buf.readline()
        else:  # pragma: no cover — exotic stdin without .buffer
            import os
            chunks = []
            while True:
                b = os.read(sys.stdin.fileno(), 1)
                if not b or b == b"\n":
                    break
                chunks.append(b)
            raw = b"".join(chunks)
    except Exception:  # noqa: BLE001 — fall back to text input if byte read fails
        try:
            return input()
        except (EOFError, KeyboardInterrupt):
            raise
    if raw == b"":
        return None  # EOF
    return raw.decode("utf-8", errors="replace").rstrip("\r\n")


def interactive_loop(final_state: dict, ticker: str, llm, *, force: bool | None = None) -> None:
    """Run the post-analysis Q&A loop.

    ``force`` overrides the TTY check (True = always run, False = always skip);
    when None, auto-detect. Never raises — Q&A is a convenience layer.
    """
    run = _is_interactive() if force is None else force
    if not run:
        return
    if llm is None:
        return

    # Make non-ASCII (Chinese) input safe before reading any stdin.
    _ensure_utf8_stdio()

    try:
        summary = summarize_state(final_state)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[yellow]Q&A unavailable (summary failed: {exc}).[/yellow]")
        return

    console.print(Panel(
        f"[bold cyan]Follow-up Q&A for {ticker}[/bold cyan]\n"
        "Ask about the report (it won't re-run the analysis). "
        "Type [bold]exit[/bold] to quit.",
        border_style="cyan",
    ))

    history: list[tuple[str, str]] = []
    while True:
        try:
            line = _read_question("\n[bold green]> [/bold green]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Leaving Q&A.[/dim]")
            break
        if line is None:  # EOF
            console.print("\n[dim]Leaving Q&A.[/dim]")
            break
        question = line.strip()
        if not question:
            continue
        if question.lower() in _EXIT_WORDS:
            console.print("[dim]Leaving Q&A.[/dim]")
            break

        with console.status("[dim]thinking…[/dim]"):
            answer = answer_question(summary, question, history, llm)

        console.print(Panel(Markdown(answer), border_style="blue", padding=(1, 2)))
        history.append((question, answer))
        if len(history) > _MAX_TURNS:
            history = history[-_MAX_TURNS:]

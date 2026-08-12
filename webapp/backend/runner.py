"""Background analysis runner: drives the engine's stream and emits SSE events.

We run ``DromXGraph(...).graph.stream(init_state)`` ourselves (instead of
the blocking ``propagate``) so each node's output becomes a live event the moment
it lands — exactly how the CLI's live panel works, but pushed to the browser.

Each run keeps an in-memory record with an APPEND-ONLY EVENT LOG guarded by a
Condition, so any number of SSE consumers (including a browser that disconnects
and reconnects, or switches tabs and comes back) can replay the full event
history from index 0 and then tail new events. When the stream finishes we merge
all chunks into final_state, persist it, and append a terminal ``complete`` event.

The engine is used READ-ONLY: DromXGraph, write_report_tree, parse_rating.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, Iterator

from cli.stats_handler import StatsCallbackHandler
from webapp.backend import store

logger = logging.getLogger("dromx.web.runner")

# Node label → state key it produces (from the engine pipeline). Lets us turn a
# raw graph chunk into a "this section is ready" event with its markdown.
_KEY_TO_LABEL = dict(store.REPORT_SECTIONS)

# Pipeline node order for the progress tree (grouped by team in the frontend).
# These are the langgraph node names; "Regime Analyst" etc. match graph/setup.py.
PIPELINE_NODES: list[str] = [
    "Regime Analyst",
    "Market Analyst", "Sentiment Analyst", "News Analyst",
    "Fundamentals Analyst", "Industry Analyst",
    "Signal Aggregator", "Event Impact", "Key Question",
    "Growth Analyst", "Risk Analyst", "Research Manager",
    "Trader",
    "Reward Specialist", "Tail Risk Specialist", "Regime Risk Specialist",
    "Risk Consensus", "Forecast Synthesizer", "Portfolio Manager",
]


def _notify_on_complete(handle, decision: str) -> None:
    """Dispatch the on-complete notification for a finished run (best-effort).

    Sends a Feishu card (full PM decision) + a short system pop-up, tagged with
    the ticker + rating. Any failure is swallowed — notification must never fail
    the analysis (mirrors the scorecard write-back contract).
    """
    try:
        from webapp.backend import notify

        rating = handle.rating or "N/A"
        src = f"（来自策略 {handle.strategy_id}）" if handle.strategy_id else ""
        title = f"DromX · {handle.ticker} 分析完成"
        subtitle = f"{handle.ticker} · 评级 {rating} · {handle.trade_date}{src}"
        body = decision.strip() or f"{handle.ticker} 分析完成，评级 {rating}。"
        notify.alert(title, body, card_subtitle=subtitle)
    except Exception as exc:  # noqa: BLE001 — never fail the run over a notification
        logger.warning("run %s on-complete notify failed: %s", handle.id, exc)


class RunHandle:
    """In-memory state for one run + an append-only, replayable event log."""

    def __init__(self, run_id: str, ticker: str, trade_date: str, analysts: list[str], depth: int,
                 shares: float | None = None, cost_basis: float | None = None,
                 holdings: list[str] | None = None, strategy_id: str | None = None,
                 on_complete_notify: bool = False):
        self.id = run_id
        self.ticker = ticker
        self.trade_date = trade_date
        self.analysts = analysts
        self.depth = depth
        self.shares = shares
        self.cost_basis = cost_basis
        self.holdings = holdings or []
        # PRD §4.3: source strategy (attribution) + notify-on-complete opt-in.
        self.strategy_id = strategy_id
        self.on_complete_notify = on_complete_notify
        self.status = "running"
        self.final_state: dict[str, Any] | None = None
        self.rating: str | None = None
        self.error: str | None = None
        self._seen_keys: set[str] = set()
        # Replayable event log: consumers read by index; _ended marks terminal.
        self._log: list[dict] = []
        self._cond = threading.Condition()
        self._ended = False

    def emit(self, event: dict) -> None:
        with self._cond:
            self._log.append(event)
            if event.get("type") in ("complete", "error"):
                self._ended = True
            self._cond.notify_all()

    def iter_events(self, timeout_total: float = 1800.0) -> Iterator[dict]:
        """Yield ALL events from index 0, then tail new ones until terminal.

        Re-entrant: every connection (first load, reconnect, tab switch-back)
        gets the full history followed by live updates. Stops after a
        complete/error event or once the total wait budget elapses.
        """
        idx = 0
        deadline = time.monotonic() + timeout_total
        while True:
            with self._cond:
                while idx >= len(self._log):
                    if self._ended:
                        return
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return
                    self._cond.wait(timeout=min(remaining, 15.0))
                event = self._log[idx]
                idx += 1
            yield event
            if event.get("type") in ("complete", "error"):
                return


_RUNS: dict[str, RunHandle] = {}
_LOCK = threading.Lock()
# Single-flight: one heavy analysis at a time on this machine.
_RUN_SEM = threading.Semaphore(1)


def get_run(run_id: str) -> RunHandle | None:
    with _LOCK:
        return _RUNS.get(run_id)


def is_active(run_id: str) -> bool:
    """True if the run is in memory and has not reached a terminal event.

    Used to refuse deletion of a run whose worker thread is still emitting —
    deleting its file mid-flight would just be re-created by the next save.
    """
    with _LOCK:
        handle = _RUNS.get(run_id)
    if handle is None:
        return False
    with handle._cond:
        return not handle._ended


def drop_run(run_id: str) -> None:
    """Forget a finished run's in-memory handle (called on delete)."""
    with _LOCK:
        _RUNS.pop(run_id, None)



def _depth_to_rounds(depth: int) -> int:
    # 1=shallow, 3=medium, 5=deep — same scale as the CLI research-depth picker.
    return max(1, int(depth))


def run_analysis_once(
    ticker: str, trade_date: str, analysts: list[str], depth: int,
    *, shares: float | None = None, cost_basis: float | None = None,
    holdings: list[str] | None = None, on_section=None, should_stop=None,
    callbacks=None,
) -> tuple[dict, str | None]:
    """Run the full pipeline ONCE and return (final_state, rating).

    The single source of truth for "analyse this name on this date" — used by the
    live SSE worker AND the backtest harness, so both take the exact same
    look-ahead-safe path (the engine only sees data up to ``trade_date``).
    ``on_section(key, label, markdown)`` is called as each section lands (the
    live worker emits SSE; the backtest ignores it). Blocking; caller owns
    concurrency (the single-flight semaphore).

    ``callbacks`` (optional) are LangChain callback handlers bound to the LLM
    constructors (e.g. a StatsCallbackHandler for token/cost usage). Callers that
    want usage pass one and read ``.get_stats()`` after — the assistant deep-analysis
    tool uses this so the work platform can record real (non-estimated) pipeline cost.

    ``holdings`` is the user's OTHER positions declared for THIS analysis; it
    drives the pre-trade portfolio-context factor. We force cfg["holdings"] to
    exactly this list (empty by default) so a stale env/.env value never leaks in
    — the portfolio-context factor only appears when the user actually declares
    holdings for the run.
    """
    from dromx.default_config import DEFAULT_CONFIG
    from dromx.graph.trading_graph import DromXGraph

    from webapp.backend.position import build_position_context

    cfg = DEFAULT_CONFIG.copy()
    rounds = _depth_to_rounds(depth)
    cfg["max_debate_rounds"] = rounds
    cfg["max_risk_discuss_rounds"] = rounds
    # Portfolio context is driven ONLY by holdings declared for this run — never a
    # stale .env list. Empty → the _build_portfolio_context factor yields '' and
    # is skipped entirely.
    cfg["holdings"] = list(holdings or [])

    analyst_keys = tuple(analysts) if analysts else (
        "market", "social", "news", "fundamentals", "industry")
    graph = DromXGraph(selected_analysts=analyst_keys, config=cfg, callbacks=callbacks)

    asset_type = "stock"
    company, td = ticker, trade_date
    # run-start 上下文互相独立（纯查询，各自 degrade），并行预取
    from dromx.graph.prefetch import parallel_prefetch

    ctx = parallel_prefetch({
        "past_context": lambda: graph.memory_log.get_past_context(company),
        "instrument_context": lambda: graph.resolve_instrument_context(company, asset_type),
        "portfolio_context": lambda: graph._build_portfolio_context(company, td),
        "market_context": lambda: graph._build_market_context(company, td),
        "instrument_type": lambda: graph._resolve_instrument_type(company, td),
    }, label=f"run-start context({company})")
    instrument_type, framework_note = ctx["instrument_type"]
    graph._resolve_pending_entries(company)
    position_context = build_position_context(company, td, shares, cost_basis)
    init_state = graph.propagator.create_initial_state(
        company, td, asset_type=asset_type,
        past_context=ctx["past_context"],
        instrument_context=ctx["instrument_context"],
        portfolio_context=ctx["portfolio_context"],
        market_context=ctx["market_context"],
        instrument_type=instrument_type,
        framework_note=framework_note,
        position_context=position_context,
    )
    args = graph.propagator.get_graph_args()

    merged: dict[str, Any] = {}
    seen: set[str] = set()
    for chunk in graph.graph.stream(init_state, **args):
        # 协作式取消：节点间检查，避免用户停止后继续烧 LLM token
        if should_stop is not None and should_stop():
            from dromx.assistant.cancel import CancelledError
            raise CancelledError(f"analysis of {company} cancelled by user")
        if not isinstance(chunk, dict):
            continue
        merged.update(chunk)
        if on_section:
            for key, label in store.REPORT_SECTIONS:
                if key in chunk and key not in seen:
                    val = chunk.get(key)
                    if isinstance(val, str) and val.strip():
                        seen.add(key)
                        on_section(key, label, val)

    from dromx.core.rating import parse_rating
    decision = merged.get("final_trade_decision", "") or ""
    rating = parse_rating(decision) if decision else None

    # Feed the self-improvement loop (same as the CLI's _run_graph): store the
    # decision in memory and enqueue each analyst's directional signal in the
    # scorecard, so the NEXT same-ticker run scores this one once its realized
    # return is known and up-weights whoever has been right. Best-effort — a
    # bookkeeping failure must never fail the analysis.
    if decision:
        try:
            graph.memory_log.store_decision(
                ticker=company, trade_date=str(td), final_trade_decision=decision,
            )
            graph.scorecard.record_run(company, str(td), merged)
        except Exception as exc:  # noqa: BLE001
            logger.warning("scorecard/memory write-back failed for %s %s: %s",
                           company, td, exc)
    return merged, rating


def start_run(ticker: str, trade_date: str, analysts: list[str], depth: int,
              shares: float | None = None, cost_basis: float | None = None,
              holdings: list[str] | None = None, strategy_id: str | None = None,
              on_complete_notify: bool = False) -> str:
    """Register a run and kick off the background worker thread. Returns run_id."""
    run_id = uuid.uuid4().hex[:12]
    handle = RunHandle(run_id, ticker, trade_date, analysts, depth, shares, cost_basis,
                       holdings, strategy_id, on_complete_notify)
    with _LOCK:
        _RUNS[run_id] = handle

    logger.info("run %s START ticker=%s date=%s analysts=%s depth=%s shares=%s holdings=%s",
                run_id, ticker, trade_date, ",".join(analysts), depth, shares,
                ",".join(holdings or []))

    # Persist an initial 'running' record so history shows it immediately.
    store.save_run({
        "id": run_id, "ticker": ticker, "trade_date": trade_date,
        "analysts": analysts, "depth": depth, "status": "running",
        "shares": shares, "cost_basis": cost_basis, "holdings": holdings or [],
        "strategy_id": strategy_id,
        "rating": None, "created_at": store.now_iso(), "finished_at": None,
        "usage": None,
        "final_state": {},
    })

    t = threading.Thread(target=_worker, args=(handle,), daemon=True)
    t.start()
    return run_id


def _worker(handle: RunHandle) -> None:
    """Run the engine stream, emitting an event per completed node."""
    t_start = time.monotonic()
    acquired = _RUN_SEM.acquire(timeout=1)
    if not acquired:
        handle.emit({"type": "queued",
                     "message": "Another analysis is running; waiting for a slot…"})
        logger.info("run %s queued (waiting for slot)", handle.id)
        _RUN_SEM.acquire()
    stats_handler: StatsCallbackHandler | None = None
    try:
        handle.emit({"type": "start", "run_id": handle.id,
                     "ticker": handle.ticker, "nodes": PIPELINE_NODES})

        # Track LLM/tool usage for this run, the same way the CLI does
        # (cli/main.py: callbacks bound to the LLM constructors via DromXGraph).
        # get_graph_args() stays callback-free — passing the handler there too
        # would double-count tokens (config callbacks propagate to child runs).
        stats_handler = StatsCallbackHandler()

        # Build config from the configured engine (.env) + per-run overrides.
        from dromx.default_config import DEFAULT_CONFIG
        from dromx.graph.trading_graph import DromXGraph

        cfg = DEFAULT_CONFIG.copy()
        rounds = _depth_to_rounds(handle.depth)
        cfg["max_debate_rounds"] = rounds
        cfg["max_risk_discuss_rounds"] = rounds
        # Portfolio context comes ONLY from holdings declared for this run — never
        # a stale .env list (empty → the factor is skipped).
        cfg["holdings"] = list(handle.holdings or [])

        analyst_keys = tuple(handle.analysts) if handle.analysts else (
            "market", "social", "news", "fundamentals", "industry")
        logger.info("run %s building graph (analysts=%s)", handle.id, ",".join(analyst_keys))
        graph = DromXGraph(selected_analysts=analyst_keys, config=cfg,
                           callbacks=[stats_handler])

        # Detect asset type the way the engine/CLI does.
        asset_type = "stock"

        # Replicate the run-start context injection that _run_graph does, so the
        # streamed run matches a normal propagate() run exactly.
        company = handle.ticker
        td = handle.trade_date
        logger.info("run %s pre-fetching run-start context (parallel)…", handle.id)
        from dromx.graph.prefetch import parallel_prefetch

        ctx = parallel_prefetch({
            "past_context": lambda: graph.memory_log.get_past_context(company),
            "instrument_context": lambda: graph.resolve_instrument_context(company, asset_type),
            "portfolio_context": lambda: graph._build_portfolio_context(company, td),
            "market_context": lambda: graph._build_market_context(company, td),
            "instrument_type": lambda: graph._resolve_instrument_type(company, td),
        }, label=f"run {handle.id} context")
        instrument_type, framework_note = ctx["instrument_type"]
        graph._resolve_pending_entries(company)
        # Position-aware analysis: if the user declared a position in THIS name,
        # inject it (with live P&L) so the PM/Trader manage that position.
        from webapp.backend.position import build_position_context
        position_context = build_position_context(
            company, td, handle.shares, handle.cost_basis,
        )
        init_state = graph.propagator.create_initial_state(
            company, td, asset_type=asset_type,
            past_context=ctx["past_context"],
            instrument_context=ctx["instrument_context"],
            portfolio_context=ctx["portfolio_context"],
            market_context=ctx["market_context"],
            instrument_type=instrument_type,
            framework_note=framework_note,
            position_context=position_context,
        )
        args = graph.propagator.get_graph_args()
        logger.info("run %s instrument_type=%s — streaming pipeline…", handle.id, instrument_type)

        merged: dict[str, Any] = {}
        for chunk in graph.graph.stream(init_state, **args):
            if not isinstance(chunk, dict):
                continue
            merged.update(chunk)
            # Emit an event for any newly-arrived report section.
            for key, label in store.REPORT_SECTIONS:
                if key in chunk and key not in handle._seen_keys:
                    val = chunk.get(key)
                    if isinstance(val, str) and val.strip():
                        handle._seen_keys.add(key)
                        elapsed = time.monotonic() - t_start
                        logger.info("run %s  ✓ %-22s (%5.0fs, %d chars)",
                                    handle.id, key, elapsed, len(val))
                        handle.emit({
                            "type": "section",
                            "key": key,
                            "label": label,
                            "markdown": val,
                        })

        handle.final_state = merged
        from dromx.core.rating import parse_rating
        decision = merged.get("final_trade_decision", "") or ""
        handle.rating = parse_rating(decision) if decision else None
        handle.status = "done"

        # Feed the self-improvement loop (memory + scorecard), same as the CLI's
        # _run_graph, so this decision is scored and its analysts up/down-weighted
        # on the next same-ticker run. Best-effort — never fail the run over it.
        if decision:
            try:
                graph.memory_log.store_decision(
                    ticker=handle.ticker, trade_date=str(handle.trade_date),
                    final_trade_decision=decision,
                )
                graph.scorecard.record_run(handle.ticker, str(handle.trade_date), merged)
            except Exception as exc:  # noqa: BLE001
                logger.warning("run %s scorecard/memory write-back failed: %s", handle.id, exc)

        # Persist full result for history / reload / Q&A.
        store.save_run({
            "id": handle.id, "ticker": handle.ticker, "trade_date": handle.trade_date,
            "analysts": handle.analysts, "depth": handle.depth, "status": "done",
            "strategy_id": handle.strategy_id,
            "rating": handle.rating, "created_at": store.now_iso(),
            "finished_at": store.now_iso(), "usage": stats_handler.get_stats(),
            "final_state": merged,
        })
        # Best-effort: also write the on-disk markdown report tree like the CLI.
        try:
            graph.save_reports(merged, handle.ticker)
        except Exception as exc:  # noqa: BLE001
            logger.warning("run %s save_reports failed: %s", handle.id, exc)

        # PRD §2.2.2: fire the on-complete notification when the run opted in.
        # Best-effort — a notification failure must never fail the analysis.
        if handle.on_complete_notify:
            _notify_on_complete(handle, decision)

        total = time.monotonic() - t_start
        logger.info("run %s DONE rating=%s in %.0fs (%d sections)",
                    handle.id, handle.rating, total, len(handle._seen_keys))
        handle.emit({"type": "complete", "run_id": handle.id, "rating": handle.rating})
    except Exception as exc:  # noqa: BLE001 — surface to the client, don't crash the server
        logger.exception("run %s FAILED", handle.id)
        handle.status = "error"
        handle.error = f"{type(exc).__name__}: {exc}"
        rec = store.load_run(handle.id) or {}
        rec.update({"status": "error", "finished_at": store.now_iso(), "error": handle.error})
        # Keep partial usage on failure too — a cancelled/crashed run still burned tokens.
        if stats_handler is not None:
            rec["usage"] = stats_handler.get_stats()
        store.save_run(rec)
        handle.emit({"type": "error", "message": handle.error})
    finally:
        _RUN_SEM.release()

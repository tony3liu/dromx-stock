"""
FastAPI app exposing the DromX engine over HTTP + SSE.

Read-only over the engine: it imports DromXGraph / summarize_state /
answer_question and never modifies dromx/. Endpoints:

  POST /api/runs              create + start an analysis (returns run_id)
  GET  /api/runs/{id}/stream  SSE: live node/section events until complete
  GET  /api/runs              history list (newest first)
  GET  /api/runs/{id}         full stored run (final_state for report view)
  POST /api/runs/{id}/qa      ask a follow-up against a finished run
  GET  /api/health            liveness
"""

from __future__ import annotations

# Load .env (DROMX_OUTPUT_LANGUAGE=中文 etc.) BEFORE any dromx
# import — _apply_env_overrides runs at default_config import time and reads
# os.environ, so without this the webapp defaults to English output.
from dotenv import load_dotenv

load_dotenv()  # noqa: E402 — intentional: must run before the imports below

# 页面配置层（user_settings.json）覆盖 .env —— 必须在 dromx 各模块 import
# 之前应用，这样 default_config 读到的就是覆盖后的值
from webapp.backend.usersettings import apply_on_startup  # noqa: E402

apply_on_startup()  # noqa: E402

import asyncio
import json
import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse

from webapp.backend import auth, backtest, factor, hedge, jobs, monitor, notify, performance, portfolio, report, runner, scheduler, sizing, store, strategy
from webapp.backend import assistant as assistant_api
from webapp.backend.schemas import (
    BacktestRequest,
    CreateRunRequest,
    CreateRunResponse,
    QARequest,
    QAResponse,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
    force=True,  # take over even if uvicorn already configured the root logger
)
logger = logging.getLogger("dromx.web")

# Surface the analysis-runner's per-section progress on its OWN stderr handler,
# independent of the root logger. uvicorn reconfigures the root logger after
# import, so basicConfig(force=True) alone isn't enough to keep dromx.*
# INFO visible. With this, runner.py's "run {id} ✓ market_report (120s, 3500
# chars)" lands in the uvicorn console the moment each section completes — the
# quickest way to judge a run while testing.
import sys as _sys
_ta_handler = logging.StreamHandler(_sys.stderr)
_ta_handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%H:%M:%S"))
_ta_root = logging.getLogger("dromx")
_ta_root.setLevel(logging.INFO)
_ta_root.addHandler(_ta_handler)
_ta_root.propagate = False  # don't double-emit via the root (uvicorn) handler

app = FastAPI(title="DromX Web", version="0.1.0")

# 投研助手 API
app.include_router(assistant_api.router)


@app.on_event("startup")
def _startup_banner() -> None:
    logger.info("DromX Web backend up — POST /api/runs to start; "
                "GET /api/runs/{id}/stream for live SSE. Logs at INFO.")
    logger.info("Auth: %s", "ENABLED (password login required)"
                if auth.auth_enabled() else "disabled (open access)")
    # Any run still marked "running" is orphaned (its worker thread died with the
    # previous process). Flip it to "interrupted" so the UI shows it as retryable
    # instead of replaying an empty fake-complete or spinning forever.
    reaped = store.reap_stale_runs()
    if reaped:
        logger.info("reaped %d stale running run(s) -> interrupted", reaped)
    # Phase 2: start the scheduler if scheduler/monitor is enabled (both OFF by
    # default → no-op). Best-effort — a scheduler failure must not block startup.
    try:
        if scheduler.start():
            logger.info("scheduler/monitor started")
    except Exception as exc:  # noqa: BLE001
        logger.warning("scheduler start failed: %s", exc)


@app.on_event("shutdown")
def _shutdown_scheduler() -> None:
    try:
        scheduler.shutdown()
    except Exception:  # noqa: BLE001
        pass


# Single-machine dev: allow the Vite dev server (any localhost port).
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# v0.4.0 strategy engine + notification routes (APIRouter modules alongside the
# @app.<verb> endpoints below — FastAPI supports mixing both styles).
app.include_router(strategy.router)
app.include_router(notify.router)
# Phase 2: monitoring + scheduled jobs routes.
app.include_router(monitor.router)
app.include_router(jobs.router)

# Lazily-built quick LLM for Q&A (avoids a heavy graph build per question).
_qa_llm = None
# Lazily-built deep-thinking LLM for report synthesis (higher-quality prose).
_report_llm = None


def _get_qa_llm():
    global _qa_llm
    if _qa_llm is None:
        from dromx.default_config import DEFAULT_CONFIG
        from dromx.graph.trading_graph import DromXGraph

        _qa_llm = DromXGraph(config=DEFAULT_CONFIG.copy()).quick_thinking_llm
    return _qa_llm


def _get_report_llm():
    """Deep-thinking LLM for the comprehensive report (depth > speed here)."""
    global _report_llm
    if _report_llm is None:
        from dromx.default_config import DEFAULT_CONFIG
        from dromx.graph.trading_graph import DromXGraph

        _report_llm = DromXGraph(config=DEFAULT_CONFIG.copy()).deep_thinking_llm
    return _report_llm


@app.get("/api/settings/env")
def get_env_settings(_: None = Depends(auth.require_auth)) -> dict:
    """页面配置层状态：每个可配置 key 的来源（页面/.env/未配置）。

    secret 类 key 只回掩码，不回原文。
    """
    from webapp.backend import usersettings

    return {"settings": usersettings.get_settings()}


@app.put("/api/settings/env")
def update_env_settings(req: dict, _: None = Depends(auth.require_auth)) -> dict:
    """保存页面配置（优先级高于 .env）。value 为空字符串 = 清除页面配置。

    LLM 相关配置变更后重置投研助手 planner（下次提问用新配置）。
    """
    from webapp.backend import usersettings

    updates = req.get("updates") or {}
    if not isinstance(updates, dict) or not updates:
        raise HTTPException(status_code=422, detail="updates required")
    try:
        result = usersettings.update_settings(updates)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if result["llm_changed"]:
        assistant_api.reset_planner()
    return result


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/auth/status")
def auth_status() -> dict:
    """Tells the frontend whether a password login is required."""
    return {"auth_required": auth.auth_enabled()}


@app.post("/api/login")
def login(body: dict) -> dict:
    """Exchange the shared password for a signed bearer token.

    When auth is disabled this is a no-op that returns an empty token, so the
    frontend can call it unconditionally.
    """
    if not auth.auth_enabled():
        return {"token": "", "auth_required": False}
    if not auth.verify_password(str(body.get("password", ""))):
        raise HTTPException(status_code=401, detail="wrong password")
    return {"token": auth.issue_token(), "auth_required": True}


@app.post("/api/runs", response_model=CreateRunResponse)
def create_run(req: CreateRunRequest, _: None = Depends(auth.require_auth)) -> CreateRunResponse:
    run_id = runner.start_run(
        ticker=req.ticker.strip(),
        trade_date=req.trade_date.strip(),
        analysts=[a.lower() for a in req.analysts],
        depth=req.depth,
        shares=req.shares,
        cost_basis=req.cost_basis,
        holdings=req.holdings,
        strategy_id=req.strategy_id,
        on_complete_notify=req.on_complete_notify,
    )
    return CreateRunResponse(id=run_id, status="running")


@app.get("/api/runs")
def list_runs(_: None = Depends(auth.require_auth)) -> list[dict]:
    return store.list_runs()


@app.get("/api/performance")
def get_performance(holding_days: int = 5, _: None = Depends(auth.require_auth)) -> dict:
    """Score all completed runs against realized prices and aggregate metrics.

    Read-only + best-effort: runs too recent to have forward prices come back as
    ``pending`` rather than erroring. ``holding_days`` sets the return window.
    """
    return performance.build_performance(holding_days=max(1, min(int(holding_days), 60)))


@app.get("/api/runs/{run_id}")
def get_run(run_id: str, _: None = Depends(auth.require_auth)) -> dict:
    rec = store.load_run(run_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="run not found")
    return rec


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: str, _: None = Depends(auth.require_auth)) -> dict:
    """Delete a run's history record. Refuses while it is still running."""
    if runner.is_active(run_id):
        raise HTTPException(status_code=409, detail="分析进行中，无法删除，请等待完成或失败后再删除。")
    existed = store.delete_run(run_id)
    runner.drop_run(run_id)
    if not existed:
        raise HTTPException(status_code=404, detail="run not found")
    return {"ok": True, "id": run_id}


@app.get("/api/runs/{run_id}/sizing")
def get_sizing(run_id: str, _: None = Depends(auth.require_auth)) -> dict:
    """Position-sizing model (fused scenarios + fractional Kelly) for a run.

    Reuses the engine's Kelly math; read-only over the stored run. 404 if absent.
    """
    result = sizing.build_sizing(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="run not found")
    return result


@app.get("/api/runs/{run_id}/factor")
def get_factor(run_id: str, _: None = Depends(auth.require_auth)) -> dict:
    """Price-based factor / risk exposure (beta, alpha, idiosyncratic vol, …)."""
    rec = store.load_run(run_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="run not found")
    ticker = (rec.get("ticker") or "").strip()
    from datetime import date as _date
    curr = (rec.get("trade_date") or "").strip() or _date.today().isoformat()
    return factor.build_factor_exposure(ticker, curr)


@app.get("/api/hedge")
def get_hedge(_: None = Depends(auth.require_auth)) -> dict:
    """Cross-instrument hedge advisor over all analysed names (correlation clusters)."""
    return hedge.build_hedge_report()


@app.get("/api/backtest/estimate")
def backtest_estimate(ticker: str, start_date: str, end_date: str,
                      _: None = Depends(auth.require_auth)) -> dict:
    """How many full-pipeline runs a backtest window would cost (pre-launch)."""
    n = backtest.estimate_days(ticker.strip(), start_date.strip(), end_date.strip())
    return {"days": n, "max_days": backtest.MAX_DAYS, "capped": n >= backtest.MAX_DAYS}


@app.get("/api/backtest")
def backtest_list(_: None = Depends(auth.require_auth)) -> list[dict]:
    return backtest.list_backtests()


@app.post("/api/backtest")
def backtest_start(req: BacktestRequest, _: None = Depends(auth.require_auth)) -> dict:
    """Launch a backtest (background, serial). Rejects windows over the cost cap."""
    import uuid

    ticker = req.ticker.strip().upper()
    n = backtest.estimate_days(ticker, req.start_date.strip(), req.end_date.strip())
    if n == 0:
        raise HTTPException(status_code=400, detail="该区间内没有可用交易日，请调整日期。")
    if len(backtest.trading_days(ticker, req.start_date.strip(), req.end_date.strip())) > backtest.MAX_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"区间过大：{n}+ 个交易日超过单次上限 {backtest.MAX_DAYS} 次全流程调用，请缩小区间。",
        )
    bt_id = "bt_" + uuid.uuid4().hex[:10]
    backtest.start_backtest(bt_id, ticker, req.start_date.strip(), req.end_date.strip(),
                            [a.lower() for a in req.analysts], req.depth, req.holding_days)
    return {"id": bt_id, "status": "running", "days": n}


@app.get("/api/backtest/{bt_id}")
def backtest_get(bt_id: str, _: None = Depends(auth.require_auth)) -> dict:
    rec = backtest.load_backtest(bt_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="backtest not found")
    return rec


@app.post("/api/backtest/{bt_id}/stop")
def backtest_stop(bt_id: str, _: None = Depends(auth.require_auth)) -> dict:
    """Request a running backtest to stop gracefully after the current day."""
    backtest.request_stop(bt_id)
    return {"ok": True, "id": bt_id}



@app.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str, _: None = Depends(auth.require_auth)):
    """SSE stream of analysis events. Replays already-finished runs from disk."""
    handle = runner.get_run(run_id)

    if handle is None:
        # Not in memory — maybe a finished/old run. Replay its sections from disk.
        rec = store.load_run(run_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="run not found")

        async def replay():
            yield {"event": "message",
                   "data": json.dumps({"type": "start", "run_id": run_id,
                                       "ticker": rec.get("ticker"),
                                       "nodes": runner.PIPELINE_NODES})}
            fs = rec.get("final_state") or {}
            for key, label in store.REPORT_SECTIONS:
                val = fs.get(key)
                if isinstance(val, str) and val.strip():
                    yield {"event": "message",
                           "data": json.dumps({"type": "section", "key": key,
                                               "label": label, "markdown": val})}
            # Only a genuinely finished run replays as complete. An interrupted/
            # errored run (no live handle, not done) emits an error so the UI
            # stops at a retryable state instead of a blank "complete".
            if rec.get("status") == "done":
                yield {"event": "message",
                       "data": json.dumps({"type": "complete", "run_id": run_id,
                                           "rating": rec.get("rating")})}
            else:
                yield {"event": "message",
                       "data": json.dumps({"type": "error",
                                           "message": rec.get("error")
                                           or "该分析未完成（已中断），请重新发起。"})}
        return EventSourceResponse(replay())

    async def event_gen():
        loop = asyncio.get_event_loop()
        # iter_events replays the full log from index 0 then tails live events,
        # so reconnects / tab switch-backs get the complete history every time.
        it = handle.iter_events()
        sentinel = object()
        while True:
            ev = await loop.run_in_executor(None, lambda: next(it, sentinel))
            if ev is sentinel:
                break
            yield {"event": "message", "data": json.dumps(ev, ensure_ascii=False, default=str)}

    return EventSourceResponse(event_gen())


@app.get("/api/price/{ticker}")
def price(ticker: str, date: str | None = None, days: int = 120,
          _: None = Depends(auth.require_auth)) -> dict:
    """Recent OHLC for charting. Read-only over the engine's data layer.

    Degrades to ``{"points": []}`` on any vendor failure so the chart just
    hides itself rather than breaking the report page.
    """
    ticker = ticker.strip()
    try:
        from datetime import date as _date

        from dromx.dataflows.stockstats_utils import load_ohlcv

        curr_date = (date or "").strip() or _date.today().isoformat()
        df = load_ohlcv(ticker, curr_date)
        if df is None or getattr(df, "empty", True):
            return {"ticker": ticker, "points": []}

        cols = {c.lower(): c for c in df.columns}
        dcol = cols.get("date")
        ccol = cols.get("close")
        if ccol is None:
            return {"ticker": ticker, "points": []}

        tail = df.tail(max(5, min(int(days), 750)))
        points = []
        for _, row in tail.iterrows():
            try:
                close = float(row[ccol])
            except (TypeError, ValueError):
                continue
            d = str(row[dcol])[:10] if dcol else ""
            pt = {"date": d, "close": round(close, 4)}
            for k, src in (("open", "open"), ("high", "high"), ("low", "low")):
                if src in cols:
                    try:
                        pt[k] = round(float(row[cols[src]]), 4)
                    except (TypeError, ValueError):
                        pass
            points.append(pt)
        return {"ticker": ticker, "points": points}
    except Exception as exc:  # noqa: BLE001 — chart is best-effort
        logger.warning("price(%s) failed: %s", ticker, exc)
        return {"ticker": ticker, "points": []}


def _mootdx_minute_points(ticker: str, code: str, interval: str = "5m") -> list[dict]:
    """A 股当日分时（mootdx 1 分钟线 → 聚合为 interval K 线）。

    mootdx 的 K 线 category 接口在当前可用的通达信服务器上未实现
    （NotImplementedError，日线同样受影响），但分时两个 API 可用：
    - get_minute_time_data(market, code)：当日实时 1 分钟序列（交易时段内为部分）
    - get_history_minute_time_data(market, code, yyyymmdd)：指定日 1 分钟序列

    返回点位不含时间戳 —— 按 A 股交易时段（09:30-11:29 / 13:00-14:59，
    各 120 分钟）依序重建北京时间轴，再按 interval 聚合 OHLC。
    """
    from datetime import date as _date, datetime as _dt, timedelta, timezone

    import pandas as pd

    from dromx.dataflows.mootdx_cn import _client

    # 市场判定：优先 ticker 后缀（.SS/.SH→沪，.SZ→深），否则按代码前缀
    t = ticker.strip().upper()
    if t.endswith((".SS", ".SH")):
        market = 1
    elif t.endswith(".SZ"):
        market = 0
    elif code.startswith(("4", "8")):
        return []  # 北交所 pytdx 市场号不确定，交给 yfinance
    else:
        market = 1 if code.startswith(("5", "6", "9")) else 0

    client = _client()
    api = client.client if hasattr(client, "client") else client

    rows = None
    try:
        # 优先 history 接口（当日含实时增量且价格干净）；
        # live get_minute_time_data 在 tdxpy 后端会混入竞价 junk/异常量纲
        today = int(_date.today().strftime("%Y%m%d"))
        rows = api.get_history_minute_time_data(market, code, today)
    except Exception:  # noqa: BLE001
        rows = None
    if not rows:
        try:
            rows = api.get_minute_time_data(market, code)
        except Exception:  # noqa: BLE001
            rows = None
    if not rows:
        return []

    prices = [float(r.get("price", 0) or 0) for r in rows]
    vols = [float(r.get("vol", 0) or 0) for r in rows]
    # 过滤集合竞价/脏数据：非正价格 + 偏离中位数 50% 以上的点
    med = pd.Series([p for p in prices if p > 0]).median()
    if not med or pd.isna(med):
        return []
    tz = timezone(timedelta(hours=8))
    day = _date.today()
    points_1m = []
    for i, (p, v) in enumerate(zip(prices, vols)):
        if p <= 0 or abs(p - med) / med > 0.5:
            continue
        minute = i if i < 120 else i - 120
        hour, mi = (9, 30) if i < 120 else (13, 0)
        ts = _dt(day.year, day.month, day.day, hour, mi, tzinfo=tz) + timedelta(minutes=minute)
        points_1m.append((ts, p, v))
    if not points_1m:
        return []

    # 聚合为 interval K 线（1m 则直接返回）
    step = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "60m": 60}.get(interval, 5)
    buckets: dict[int, list] = {}
    for ts, p, v in points_1m:
        minute_of_day = ts.hour * 60 + ts.minute
        # 时段内对齐（09:30 / 13:00 起算）
        base = 9 * 60 + 30 if minute_of_day < 12 * 60 else 13 * 60
        bucket_start = base + ((minute_of_day - base) // step) * step
        b = buckets.setdefault(bucket_start, [None, 0.0, 0.0, 0.0, ts])
        o, h, lo, c, ts0 = b
        b[0] = p if o is None else o
        b[1] = max(h, p)
        b[2] = min(lo, p) if lo else p
        b[3] = p

    out = []
    for bucket_start in sorted(buckets):
        o, h, lo, c, ts = buckets[bucket_start]
        bh, bm = divmod(bucket_start, 60)
        bts = _dt(day.year, day.month, day.day, bh, bm, tzinfo=tz)
        out.append({
            "time": int(bts.timestamp()),
            "open": round(o, 4), "high": round(h, 4),
            "low": round(lo, 4), "close": round(c, 4),
        })
    return out


def _tencent_hk_minute_points(ticker: str, interval: str = "5m") -> list[dict]:
    """港股当日分时（腾讯 hkMinute，国内直连免 key）。

    Yahoo 在国内网络不稳，港股分时改走腾讯 ifzq 接口：
    ``web.ifzq.gtimg.cn/appstock/app/hkMinute/query?code=hkXXXXX``
    返回当日 1 分钟行 ``"HHMM price vol amount"``（香港时间 = 北京时间，UTC+8），
    按 interval 聚合 OHLC。
    """
    from datetime import date as _date, datetime as _dt, timedelta, timezone

    digits = "".join(ch for ch in ticker.split(".")[0] if ch.isdigit())
    if not digits:
        return []
    code = f"hk{digits.zfill(5)}"  # 腾讯港股代码为 5 位零填充：700→hk00700, 7709→hk07709

    import requests

    s = requests.Session()
    s.trust_env = False  # 国内服务强制直连，绕开系统代理/VPN
    try:
        resp = s.get(
            "https://web.ifzq.gtimg.cn/appstock/app/hkMinute/query",
            params={"code": code},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        resp.raise_for_status()
        payload = resp.json().get("data", {}).get(code, {})
        lines = payload.get("data", {}).get("data") or []
    except Exception as exc:  # noqa: BLE001
        logger.debug("tencent hkMinute(%s) failed: %s", code, exc)
        return []
    if not lines:
        return []

    tz = timezone(timedelta(hours=8))
    day = _date.today()
    step = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "60m": 60}.get(interval, 5)
    buckets: dict[int, list] = {}
    for ln in lines:
        parts = str(ln).split()
        if len(parts) < 2:
            continue
        hhmm, price_s = parts[0], parts[1]
        try:
            hour, minute = int(hhmm[:2]), int(hhmm[2:4])
            price = float(price_s)
        except (ValueError, IndexError):
            continue
        if price <= 0:
            continue
        minute_of_day = hour * 60 + minute
        bucket_start = minute_of_day - (minute_of_day % step) if step > 1 else minute_of_day
        b = buckets.setdefault(bucket_start, [None, 0.0, 0.0, 0.0])
        o, h, lo, c = b
        b[0] = price if o is None else o
        b[1] = max(h, price)
        b[2] = min(lo, price) if lo else price
        b[3] = price

    out = []
    for bucket_start in sorted(buckets):
        o, h, lo, c = buckets[bucket_start]
        bh, bm = divmod(bucket_start, 60)
        bts = _dt(day.year, day.month, day.day, bh, bm, tzinfo=tz)
        out.append({
            "time": int(bts.timestamp()),
            "open": round(o, 4), "high": round(h, 4),
            "low": round(lo, 4), "close": round(c, 4),
        })
    return out


@app.get("/api/price/intraday/{ticker}")
def price_intraday(ticker: str, interval: str = "5m",
                   _: None = Depends(auth.require_auth)) -> dict:
    """Intraday OHLC for real-time charting (5-minute bars).

    Data sources:
    - A-shares / A-share indices: mootdx 分时接口（TongDaXin TCP, real-time）
    - HK stocks: 腾讯 hkMinute（国内直连, real-time）
    - US / other: yfinance (interval="5m", ~15min delayed)

    Degrades to ``{"points": []}`` on any vendor failure.
    """
    ticker = ticker.strip()
    try:
        from datetime import date as _date

        import pandas as pd
        import yfinance as yf

        from dromx.dataflows.mootdx_cn import _normalize_cn, _client
        from dromx.dataflows.errors import VendorRateLimitError, NoMarketDataError
        from dromx.dataflows.symbol_utils import normalize_symbol

        # Try mootdx for A-shares first (real-time, no rate limit)
        try:
            code = _normalize_cn(ticker)
            points = _mootdx_minute_points(ticker, code, interval)
            if points:
                return {"ticker": ticker, "interval": interval, "points": points}
        except (VendorRateLimitError, NoMarketDataError, ImportError):
            pass  # fall through

        # HK stocks: 腾讯 hkMinute（国内直连免 key；Yahoo 在国内网络不稳）
        if ticker.upper().endswith(".HK"):
            points = _tencent_hk_minute_points(ticker, interval)
            if points:
                return {"ticker": ticker, "interval": interval, "points": points}

        # yfinance for US / other
        canonical = normalize_symbol(ticker)
        df = yf.download(
            canonical,
            period="1d",
            interval=interval,
            progress=False,
            auto_adjust=True,
            multi_level_index=False,
        )
        if df is None or df.empty:
            return {"ticker": ticker, "points": []}

        df = df.reset_index()
        # yfinance intraday uses "Datetime" or "Date" as the index column name
        dcol = "Datetime" if "Datetime" in df.columns else "Date"
        points = []
        for _, row in df.iterrows():
            try:
                close = float(row["Close"])
            except (TypeError, ValueError, KeyError):
                continue
            dt = row[dcol]
            if hasattr(dt, "timestamp"):
                ts = int(dt.timestamp())
            else:
                ts = int(pd.Timestamp(dt).timestamp())
            pt = {
                "time": ts,
                "close": round(close, 4),
            }
            for k, src in (("open", "Open"), ("high", "High"), ("low", "Low")):
                try:
                    pt[k] = round(float(row[src]), 4)
                except (TypeError, ValueError, KeyError):
                    pass
            points.append(pt)
        return {"ticker": ticker, "interval": interval, "points": points}
    except Exception as exc:  # noqa: BLE001 — chart is best-effort
        logger.warning("price_intraday(%s) failed: %s", ticker, exc)
        return {"ticker": ticker, "points": []}


@app.get("/api/portfolio")
def get_portfolio(_: None = Depends(auth.require_auth)) -> dict:
    """当前持仓列表（含浮盈亏，best-effort）。"""
    return portfolio.get_user_portfolio()


@app.get("/api/portfolio/{ticker}")
def get_position(ticker: str, _: None = Depends(auth.require_auth)) -> dict:
    """单只持仓详情 + 最近交易记录。"""
    return portfolio.get_user_position(ticker)


@app.post("/api/portfolio/trades")
def record_trade(req: dict, _: None = Depends(auth.require_auth)) -> dict:
    """记录一笔交易并更新持仓。

    Body: {"ticker": "600519", "operation": "buy"|"sell", "price": 1680.0,
           "date": "2026-07-28", "shares": 100}
    """
    try:
        return portfolio.record_trade(
            ticker=req.get("ticker", ""),
            operation=req.get("operation", ""),
            price=req.get("price"),
            date=req.get("date", ""),
            shares=req.get("shares"),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.delete("/api/portfolio/{ticker}")
def remove_position(ticker: str, _: None = Depends(auth.require_auth)) -> dict:
    """手动移除一只持仓（保留交易记录）。"""
    removed = portfolio.remove_holding(ticker)
    if not removed:
        raise HTTPException(status_code=404, detail="holding not found")
    return {"removed": ticker}


@app.post("/api/runs/{run_id}/qa", response_model=QAResponse)
def qa(run_id: str, req: QARequest, _: None = Depends(auth.require_auth)) -> QAResponse:
    rec = store.load_run(run_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="run not found")
    final_state = rec.get("final_state") or {}
    if not final_state:
        raise HTTPException(status_code=409, detail="run has no analysis yet")

    from cli.qa_agent import answer_question
    from dromx.core.report_summarizer import summarize_state

    summary = summarize_state(final_state)
    history = [(q, a) for q, a in (req.history or [])]
    answer = answer_question(summary, req.question, history, _get_qa_llm())
    return QAResponse(answer=answer)


@app.post("/api/runs/{run_id}/qa/stream")
async def qa_stream(run_id: str, req: QARequest, _: None = Depends(auth.require_auth)):
    """Token-by-token Q&A over a finished run via SSE.

    Same context + rules as POST /qa, but streams the LLM output as `delta`
    events so the browser can render the answer character by character. Falls
    back to a single delta if the model lacks `.stream()`.
    """
    rec = store.load_run(run_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="run not found")
    final_state = rec.get("final_state") or {}
    if not final_state:
        raise HTTPException(status_code=409, detail="run has no analysis yet")

    from cli.qa_agent import build_qa_prompt
    from dromx.core.report_summarizer import summarize_state

    summary = summarize_state(final_state)
    history = [(q, a) for q, a in (req.history or [])]
    prompt = build_qa_prompt(summary, req.question, history)
    llm = _get_qa_llm()

    def _produce(q) -> None:
        # Run the (blocking) LLM stream on a worker thread, pushing chunks to a
        # queue the async generator drains. Keeps the event loop responsive.
        try:
            stream = getattr(llm, "stream", None)
            if stream is None:
                resp = llm.invoke(prompt)
                q.put(("delta", getattr(resp, "content", str(resp))))
            else:
                for chunk in stream(prompt):
                    text = getattr(chunk, "content", "") or ""
                    if text:
                        q.put(("delta", text))
        except Exception as exc:  # noqa: BLE001 — surface, don't crash
            logger.warning("qa_stream(%s) failed: %s", run_id, exc)
            q.put(("delta", f"（出错：{type(exc).__name__}: {exc}）"))
        finally:
            q.put(("done", None))

    async def event_gen():
        import queue as _queue
        import threading

        q: _queue.Queue = _queue.Queue()
        threading.Thread(target=_produce, args=(q,), daemon=True).start()
        loop = asyncio.get_event_loop()
        while True:
            kind, payload = await loop.run_in_executor(None, q.get)
            if kind == "done":
                yield {"event": "message", "data": json.dumps({"type": "done"})}
                break
            yield {"event": "message",
                   "data": json.dumps({"type": "delta", "text": payload}, ensure_ascii=False)}

    return EventSourceResponse(event_gen())


@app.get("/api/runs/{run_id}/report.pdf")
def download_report_pdf(run_id: str, _: None = Depends(auth.require_auth)):
    """Generate (or reuse) the comprehensive research report and stream it as PDF.

    The PM agent writes a cohesive report from the finished analysis (deep LLM,
    one call, cached in the run record), rendered to a branded PDF by a headless
    Chromium. Downloads directly — no print dialog.
    """
    rec = store.load_run(run_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="run not found")
    if not (rec.get("final_state") or {}):
        raise HTTPException(status_code=409, detail="run has no analysis yet")
    try:
        result = report.build_report_pdf(run_id, _get_report_llm())
    except Exception as exc:  # noqa: BLE001 — surface a clean 500, don't crash
        logger.exception("report PDF generation failed for %s", run_id)
        raise HTTPException(status_code=500, detail=f"报告生成失败：{exc}") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="run not found")
    pdf, rec = result
    ticker = (rec.get("ticker") or run_id).replace("/", "_")
    date = (rec.get("trade_date") or "").strip()
    fname = f"DromX_{ticker}_{date}.pdf".replace(" ", "")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@app.get("/api/runs/{run_id}/report.md")
def get_report_markdown(run_id: str, _: None = Depends(auth.require_auth)) -> dict:
    """Return the report markdown (generated on demand, cached). For preview."""
    rec = store.load_run(run_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="run not found")
    if not (rec.get("final_state") or {}):
        raise HTTPException(status_code=409, detail="run has no analysis yet")
    res = report.build_report_markdown(run_id, _get_report_llm())
    if res is None:
        raise HTTPException(status_code=404, detail="run not found")
    md, _rec = res
    return {"markdown": md}

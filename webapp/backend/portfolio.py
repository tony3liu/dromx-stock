"""Portfolio store & operation analysis (Phase 3 用户数据工具)

支持投研助手的「我的操作对不对」类问题：

- 持仓存储：``~/.dromx/portfolio.json``（holdings + trades）
- get_user_portfolio(): 当前持仓 + 浮动盈亏（最新价 best-effort）
- get_user_position(ticker): 单只持仓详情
- analyze_operation(...): 复盘一笔买/卖操作——对比操作日后的价格走势，
  给出操作至今收益、期间最大回撤/最大涨幅等结构化数据，供 LLM 解读
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import date as _date
from pathlib import Path

logger = logging.getLogger(__name__)

_PATH = Path(os.path.expanduser("~")) / ".dromx" / "portfolio.json"

_lock = threading.Lock()

MAX_TRADES = 2000


def _empty() -> dict:
    return {"holdings": {}, "trades": []}


def _read() -> dict:
    if not _PATH.exists():
        return _empty()
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _empty()
        data.setdefault("holdings", {})
        data.setdefault("trades", [])
        return data
    except Exception as e:  # noqa: BLE001 — best-effort
        logger.warning("portfolio read failed: %s", e)
        return _empty()


def _write(data: dict) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, _PATH)


def _norm_ticker(ticker: str) -> str:
    return (ticker or "").strip().upper()


def record_trade(
    ticker: str,
    operation: str,
    price: float,
    date: str,
    shares: float | None = None,
) -> dict:
    """记录一笔交易并更新持仓。

    operation: buy / sell。买入按加权平均更新成本；卖出扣减数量，
    清仓时移除持仓。返回更新后的持仓条目。
    """
    t = _norm_ticker(ticker)
    op = (operation or "").strip().lower()
    if not t or op not in ("buy", "sell"):
        raise ValueError("ticker 必填，operation 必须是 buy/sell")
    if price is None or price <= 0:
        raise ValueError("price 必须为正数")
    qty = float(shares or 0)

    with _lock:
        data = _read()
        trade = {
            "ticker": t,
            "operation": op,
            "price": float(price),
            "date": str(date or _date.today().isoformat()),
            "shares": qty,
            "ts": int(time.time() * 1000),
        }
        data["trades"].append(trade)
        if len(data["trades"]) > MAX_TRADES:
            data["trades"] = data["trades"][-MAX_TRADES:]

        holding = data["holdings"].get(t, {"shares": 0.0, "cost_basis": None})
        if op == "buy":
            old_qty = float(holding.get("shares") or 0)
            old_cost = holding.get("cost_basis")
            new_qty = old_qty + qty
            if old_cost and old_qty > 0:
                holding["cost_basis"] = round((old_cost * old_qty + price * qty) / new_qty, 4) if new_qty else None
            else:
                holding["cost_basis"] = float(price)
            holding["shares"] = new_qty
        else:  # sell
            new_qty = float(holding.get("shares") or 0) - qty
            holding["shares"] = max(0.0, new_qty)

        if holding["shares"] <= 0:
            data["holdings"].pop(t, None)
            holding = {"shares": 0.0, "cost_basis": None}
        else:
            data["holdings"][t] = holding

        _write(data)
        return {"ticker": t, "holding": holding}


def remove_holding(ticker: str) -> bool:
    """手动移除一只持仓（不清交易记录）"""
    t = _norm_ticker(ticker)
    with _lock:
        data = _read()
        existed = t in data["holdings"]
        data["holdings"].pop(t, None)
        if existed:
            _write(data)
        return existed


def _last_close(ticker: str) -> float | None:
    """最新收盘价（best-effort，失败返回 None）"""
    try:
        from dromx.dataflows.stockstats_utils import load_ohlcv

        df = load_ohlcv(ticker, _date.today().isoformat())
        if df is None or getattr(df, "empty", True):
            return None
        cols = {c.lower(): c for c in df.columns}
        ccol = cols.get("close")
        if ccol is None:
            return None
        return float(df[ccol].iloc[-1])
    except Exception as e:  # noqa: BLE001
        logger.debug("portfolio _last_close(%s) failed: %s", ticker, e)
        return None


def _enrich(ticker: str, holding: dict) -> dict:
    """给持仓条目补充最新价与浮盈亏"""
    item = {
        "ticker": ticker,
        "shares": holding.get("shares"),
        "cost_basis": holding.get("cost_basis"),
    }
    cost = holding.get("cost_basis")
    px = _last_close(ticker)
    if px is not None:
        item["last_close"] = px
        if cost and cost > 0 and holding.get("shares"):
            item["pnl_pct"] = round((px / cost - 1) * 100, 2)
            item["pnl_value"] = round((px - cost) * holding["shares"], 2)
    return item


def get_user_portfolio() -> dict:
    """当前持仓列表（含浮盈亏）"""
    data = _read()
    holdings = data.get("holdings", {})
    if not holdings:
        return {"holdings": [], "count": 0, "message": "当前没有记录任何持仓"}
    items = [_enrich(t, h) for t, h in sorted(holdings.items())]
    return {"holdings": items, "count": len(items)}


def get_user_position(ticker: str) -> dict:
    """单只持仓详情"""
    t = _norm_ticker(ticker)
    data = _read()
    holding = data.get("holdings", {}).get(t)
    if not holding:
        # 也返回该股的交易记录，方便复盘
        trades = [tr for tr in data.get("trades", []) if tr.get("ticker") == t]
        return {
            "ticker": t,
            "holding": None,
            "message": f"当前没有 {t} 的持仓记录",
            "recent_trades": trades[-10:],
        }
    item = _enrich(t, holding)
    item["recent_trades"] = [tr for tr in data.get("trades", []) if tr.get("ticker") == t][-10:]
    return item


def analyze_operation(
    ticker: str,
    operation: str,
    price: float,
    date: str,
    shares: float | None = None,
) -> dict:
    """复盘一笔操作：对比操作日之后的价格走势。

    返回结构化数据（操作至今收益、期间最高/最低、最大回撤等），
    判断交给上层 LLM 解读。
    """
    t = _norm_ticker(ticker)
    op = (operation or "").strip().lower()
    if not t or op not in ("buy", "sell", "hold"):
        raise ValueError("operation 必须是 buy/sell/hold")

    today = _date.today().isoformat()
    try:
        from dromx.dataflows.interface import route_to_vendor

        csv_text = route_to_vendor("get_stock_data", t, str(date), today)
    except Exception as e:
        return {"ticker": t, "error": f"价格数据获取失败: {e}"}

    import io

    import pandas as pd

    try:
        df = pd.read_csv(io.StringIO(csv_text), comment="#")
    except Exception as e:
        return {"ticker": t, "error": f"价格数据解析失败: {e}"}
    if df.empty or "Close" not in df.columns:
        return {"ticker": t, "error": "操作日之后没有价格数据"}

    closes = pd.to_numeric(df["Close"], errors="coerce").dropna()
    if closes.empty:
        return {"ticker": t, "error": "操作日之后没有有效收盘价"}

    latest = float(closes.iloc[-1])
    high = float(closes.max())
    low = float(closes.min())
    ret_since = (latest / price - 1) * 100
    max_up = (high / price - 1) * 100
    max_down = (low / price - 1) * 100

    result = {
        "ticker": t,
        "operation": op,
        "operation_price": float(price),
        "operation_date": str(date),
        "shares": shares,
        "latest_close": round(latest, 2),
        "trading_days_since": int(len(closes)),
        "return_since_operation_pct": round(ret_since, 2),
        "max_up_pct": round(max_up, 2),
        "max_down_pct": round(max_down, 2),
    }

    # 简单规则化提示（最终判断由 LLM 给出）
    if op == "buy":
        result["hint"] = (
            f"买入至今 {'盈利' if ret_since >= 0 else '亏损'} {ret_since:+.2f}%，"
            f"期间最大浮盈 {max_up:+.2f}%、最大浮亏 {max_down:+.2f}%"
        )
    elif op == "sell":
        result["hint"] = (
            f"卖出后股价 {'上涨' if ret_since >= 0 else '下跌'} {ret_since:+.2f}%"
            f"（{'卖飞' if ret_since > 5 else '基本合理' if abs(ret_since) <= 5 else '卖出规避了下跌'}），"
            f"期间最高 {max_up:+.2f}%、最低 {max_down:+.2f}%"
        )
    else:
        result["hint"] = f"持有至今涨跌 {ret_since:+.2f}%，期间最大回撤 {max_down:+.2f}%"

    # 附带当前持仓状态
    data = _read()
    holding = data.get("holdings", {}).get(t)
    result["current_holding"] = holding or None
    return result

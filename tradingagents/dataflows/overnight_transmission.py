"""Overnight transmission: stitch the cross-market lead for an ETF.

For a leveraged / cross-market ETF (e.g. 07709.HK = 2x SK Hynix), the
overnight move of the underlying — often led by a US-listed reference — can
determine the listing-market open more than yesterday's own close. This
builder stitches that chain so the desk sees it BEFORE the analysts invent a
same-day company story:

  - resolve the ETF structure (leverage / underlying / direction) — reused
    from ``etf_data.resolve_etf_structure``.
  - ask the LLM ONCE whether THIS name actually has a cross-market overnight
    link and what its lead reference is — no hardcoded ticker→ref map. A
    same-market ETF (HK tracking HSI, US tracking SPX) or a name with no lead
    market returns ``has=False`` and the builder emits nothing.
  - pull the underlying's and the lead reference's latest 1-day returns. The
    underlying path falls back to yfinance for markets Tencent/mootdx don't
    cover (Korea .KS, indices ^KS200, Japan .T, …).
  - derive the expected open: prev_close × (1 + underlying_move × leverage).
  - flag whether transmission is intact or broken (lead vs underlying direction).

Deterministic math + ONE light LLM judgement; fully degrading so a non-ETF, a
same-market fund, an LLM "no link" verdict, or any fetch failure yields ``""``
and the run is unchanged. Mirrors the best-effort contract of
``market_context`` / ``portfolio_context``.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _safe(fn, default=None):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 — transmission is best-effort, never aborts
        logger.debug("overnight_transmission: %s", exc)
        return default


def _listing_market(ticker: str) -> str:
    """Coarse listing market from the ticker suffix (.HK/.SS/.KS/.T/...).

    Purely syntactic — used to reason about whether the underlying's market
    differs from the listing market. Defaults to 'US' for a bare ticker.
    """
    s = ticker.strip().upper()
    if "." in s:
        _, _, suf = s.rpartition(".")
        if suf == "HK":
            return "HK"
        if suf in ("SS", "SZ", "SH"):
            return "CN"
        if suf in ("KS", "KQ"):
            return "KR"
        if suf in ("T", "T1", "S"):
            return "JP"
        if suf in ("NS", "BO"):
            return "IN"
        if suf in ("L", "LON"):
            return "GB"
        if suf == "TO":
            return "CA"
        if suf == "AX":
            return "AU"
        if suf in ("O", "OQ", "N", "Q", "PK"):
            return "US"
    return "US"


def _close_series(symbol: str, curr_date: str):
    """Close series up to curr_date via the vendor-routed ``load_ohlcv``, or None."""
    from tradingagents.dataflows.stockstats_utils import load_ohlcv
    import pandas as pd

    df = load_ohlcv(symbol, curr_date)
    if df is None or df.empty or "Close" not in df.columns:
        return None
    s = df.copy()
    s["Date"] = pd.to_datetime(s["Date"], errors="coerce")
    s = s.dropna(subset=["Date"]).sort_values("Date")
    s = s[s["Date"] <= pd.to_datetime(curr_date)]["Close"].astype(float)
    return s if len(s) >= 1 else None


def _returns_1d(symbol: str, curr_date: str) -> float | None:
    """1-day close-to-close return % for ``symbol``, or None."""
    s = _close_series(symbol, curr_date)
    if s is None or len(s) < 2:
        return None
    return float((s.iloc[-1] / s.iloc[-2] - 1.0) * 100.0)


def _last_close(symbol: str, curr_date: str) -> float | None:
    """Most recent close at/before curr_date via the vendor path, or None."""
    s = _close_series(symbol, curr_date)
    return float(s.iloc[-1]) if s is not None and len(s) >= 1 else None


def _ohlc_row(symbol: str, curr_date: str):
    """(open, high, low, close) for the latest session at/before curr_date, or None.

    Used to surface the overnight reference's intraday shape (the shooting-star
    / engulfing reversal that a single close-to-close % hides). Vendor path
    only — the reference is normally US-listed, which Tencent covers.
    """
    from tradingagents.dataflows.stockstats_utils import load_ohlcv
    import pandas as pd

    df = load_ohlcv(symbol, curr_date)
    if df is None or df.empty:
        return None
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date")
    df = df[df["Date"] <= pd.to_datetime(curr_date)]
    if df.empty:
        return None
    row = df.iloc[-1]
    try:
        return (float(row["Open"]), float(row["High"]),
                float(row["Low"]), float(row["Close"]))
    except (KeyError, TypeError, ValueError):
        return None


def _reversal_flag(ohlc) -> str:
    """Tag a bearish intraday reversal: opened strong, closed weak.

    Fires when the close is below the open AND the high→close drawdown exceeds
    twice the low→close range — the shooting-star / engulfing shape that says
    sellers took control after an early rally. Empty string otherwise.
    """
    if not ohlc or len(ohlc) != 4 or any(v is None for v in ohlc):
        return ""
    o, h, l, c = ohlc
    if h <= l:
        return ""
    if c < o and (h - c) > 2 * max(c - l, 1e-9):
        return " ⚠️反转"
    return ""


def _underlying_returns_1d(symbol: str, curr_date: str) -> float | None:
    """1-day return for the UNDERLYING, with an explicit yfinance fallback.

    Cross-market underlyings often trade in markets the default Tencent/mootdx
    vendors don't cover (Korea .KS, indices ^KS200, Japan .T). ``load_ohlcv``
    in those modes does NOT fall back to yfinance, so for the underlying we try
    the vendor path first, then yfinance directly. The lead reference (usually
    US-listed) does not need this fallback and uses ``_returns_1d`` directly.
    """
    # 1. vendor path — works for US/HK/CN underlyings
    r = _safe(lambda: _returns_1d(symbol, curr_date))
    if r is not None:
        return r

    # 2. explicit yfinance fallback for cross-market underlyings
    def _yf():
        from tradingagents.dataflows.stockstats_utils import yf_retry
        from tradingagents.dataflows.symbol_utils import normalize_symbol
        import yfinance as yf
        import pandas as pd

        sym = normalize_symbol(symbol)
        df = yf_retry(
            lambda: yf.download(
                sym,
                period="5mo",
                interval="1d",
                multi_level_index=False,
                progress=False,
                auto_adjust=True,
            )
        )
        if df is None or df.empty:
            return None
        df = df.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if "Close" not in df.columns:
            return None
        s = df["Close"].dropna()
        s.index = pd.to_datetime(s.index)
        s = s[s.index <= pd.to_datetime(curr_date)].sort_index()
        if len(s) < 2:
            return None
        return float((s.iloc[-1] / s.iloc[-2] - 1.0) * 100.0)

    return _safe(_yf)


def _parse_holdings_tickers(raw) -> list[str]:
    """Tickers from a holdings config (list of "TICKER" / "TICKER:w"), no weights.

    Inlined (rather than importing ``portfolio_context.parse_holdings``) to keep
    this dataflow module free of a dataflows→agents dependency. We only need the
    ticker strings here, never the weights.
    """
    out: list[str] = []
    for item in raw or []:
        if isinstance(item, dict) and item.get("ticker"):
            t = str(item["ticker"]).strip()
            if t:
                out.append(t)
            continue
        if not isinstance(item, str) or not item.strip():
            continue
        ticker, _, _ = item.partition(":")
        ticker = ticker.strip()
        if ticker:
            out.append(ticker)
    return out


def _resolve_transmission_link(ticker, structure, llm) -> dict:
    """ONE light LLM call: does THIS name have a cross-market overnight link?

    Returns ``{has_cross_market_transmission, overnight_ref_proxy, reason}``.
    No hardcoded ticker→ref map — the LLM judges from the resolved structure
    whether a lead market exists and what its overnight reference is. Falls
    back to ``{has: False, ...}`` on any failure so the builder emits nothing.
    """
    if llm is None:
        return {
            "has_cross_market_transmission": False,
            "overnight_ref_proxy": None,
            "reason": "无 LLM 可判断传导链",
        }

    listing = _listing_market(ticker)
    und_name = structure.underlying_name or "(unknown)"
    und_mkt = structure.underlying_market or "(unknown)"
    und_proxy = structure.underlying_proxy or "(none)"
    lev = structure.leverage or 1.0

    prompt = f"""You are judging whether a cross-market overnight transmission chain exists for an ETF, so a downstream builder knows whether to stitch an overnight lead into the analysis.

ETF ticker: {ticker} (listed in market: {listing})
Underlying: {und_name} (market: {und_mkt}, proxy symbol: {und_proxy})
Leverage: {lev:g}x {structure.direction}

A transmission chain exists when the underlying trades in a market that opens BEFORE the ETF's listing market and leads it overnight — e.g. a HK-listed 2x Korea-semis ETF whose underlying (SK Hynix) opens in Seoul before HK, with MU as the US overnight lead. Same-market ETFs (HK tracking HSI, US tracking SPX, CN tracking CSI) have NO cross-market chain — return false. Decide for THIS name only from the structure above; do not assume a fixed ticker map.

Return JSON only:
{{"has_cross_market_transmission": true, "overnight_ref_proxy": "MU", "reason": "one sentence why the chain exists or not"}}

overnight_ref_proxy is a yfinance-loadable symbol for the overnight LEAD reference (e.g. "MU" for a Korea-semis ETF) — the overnight lead, NOT the underlying itself. null when no single lead reference exists.
"""

    def call():
        import json
        import re

        resp = llm.invoke(prompt)
        txt = getattr(resp, "content", str(resp))
        m = re.search(r"\{.*\}", txt, re.DOTALL)
        if not m:
            raise ValueError("no JSON in transmission-link response")
        d = json.loads(m.group(0))
        ref = d.get("overnight_ref_proxy")
        ref = ref.strip() if isinstance(ref, str) and ref.strip() else None
        return {
            "has_cross_market_transmission": bool(d.get("has_cross_market_transmission")),
            "overnight_ref_proxy": ref,
            "reason": str(d.get("reason") or ""),
        }

    res = _safe(call)
    if res is None:
        return {
            "has_cross_market_transmission": False,
            "overnight_ref_proxy": None,
            "reason": "LLM 传导链判断失败",
        }
    return res


def build_overnight_transmission(
    ticker: str, curr_date, config: dict | None = None, llm=None
) -> str:
    """Render the overnight transmission block, or '' when not applicable.

    Empty (run unchanged) when: the name isn't an ETF, the LLM judges no
    cross-market link exists, the underlying proxy can't be resolved, or every
    fetch failed. Best-effort throughout; each segment degrades independently.
    """
    if config is None:
        from tradingagents.dataflows.config import get_config
        config = get_config()

    from tradingagents.dataflows.etf_data import resolve_etf_structure

    structure = _safe(lambda: resolve_etf_structure(ticker, str(curr_date), llm=llm))
    if structure is None or not structure.is_etf:
        return ""  # non-ETF — P0 scope is ETF/leveraged; plain stock → no segment

    # Manual override (config etf_underlying_map) fills gaps / overrides the
    # auto-resolved structure — the reliable path when the LLM is unsure.
    etf_map = config.get("etf_underlying_map") or {}
    override = etf_map.get(ticker) or etf_map.get(ticker.upper())
    if override:
        if override.get("underlying"):
            structure.underlying_proxy = override["underlying"]
            if not structure.underlying_name:
                structure.underlying_name = override["underlying"]
        if override.get("currency"):
            structure.underlying_currency = override["currency"]

    # One LLM judgement: does THIS name have a cross-market overnight link?
    link = _resolve_transmission_link(ticker, structure, llm)
    if not link.get("has_cross_market_transmission"):
        return ""  # same-market ETF or no lead market — honest "", don't fabricate

    und_proxy = structure.underlying_proxy
    if not und_proxy:
        return ""  # no loadable underlying symbol → can't derive open price → honest ""

    und_name = structure.underlying_name or und_proxy
    und_1d = _safe(lambda: _underlying_returns_1d(und_proxy, str(curr_date)))

    # Overnight lead reference: LLM > config overnight_refs > holdings fallback.
    ref_proxy = link.get("overnight_ref_proxy")
    if not ref_proxy:
        refs = config.get("overnight_refs") or []
        if refs:
            ref_proxy = refs[0]
    if not ref_proxy:
        listing_mkt = _listing_market(ticker)
        for t in _parse_holdings_tickers(config.get("holdings")):
            if t.upper() != ticker.upper() and _listing_market(t) != listing_mkt:
                ref_proxy = t
                break
    ref_1d = (
        _safe(lambda: _returns_1d(ref_proxy, str(curr_date))) if ref_proxy else None
    )

    lev = structure.leverage or 1.0
    dir_sign = -1.0 if (structure.direction or "long") == "inverse" else 1.0
    prev_close = _safe(lambda: _last_close(ticker, str(curr_date)))

    lines: list[str] = ["## 隔夜传导（美股隔夜 → 底层今晨 → 标的开盘）"]

    struct_bits: list[str] = []
    if lev and lev != 1.0:
        struct_bits.append(f"{lev:g}x {structure.direction}")
    struct_bits.append(f"tracking {und_name}")
    lines.append(
        f"- **结构:** {' · '.join(struct_bits)}"
        f"（underlying_proxy={und_proxy}, confidence:{structure.confidence}）"
    )
    reason = link.get("reason") or "存在跨市场隔夜领先关系"
    lines.append(f"- **传导链判断:** {reason}")

    if und_1d is not None:
        lines.append(f"- **底层今晨:** {und_name}（{und_proxy}）1日 {und_1d:+.2f}%")
    else:
        lines.append(f"- **底层今晨:** {und_name}（{und_proxy}）1日 n/a（行情不可用）")

    if ref_proxy and ref_1d is not None:
        ref_ohlc = _safe(lambda: _ohlc_row(ref_proxy, str(curr_date)))
        line = f"- **隔夜参考:** {ref_proxy} 1日 {ref_1d:+.2f}%"
        if ref_ohlc:
            o, h, l, c = ref_ohlc
            line += (
                f"（开 {o:.2f} · 高 {h:.2f} · 低 {l:.2f} · 收 {c:.2f}"
                f"{_reversal_flag(ref_ohlc)}）"
            )
        lines.append(line)
    elif ref_proxy:
        lines.append(f"- **隔夜参考:** {ref_proxy} 1日 n/a（行情不可用）")

    if und_1d is not None and prev_close is not None:
        exp_pct = und_1d * lev * dir_sign
        exp_open = prev_close * (1 + exp_pct / 100.0)
        dir_note = "" if dir_sign > 0 else " × 反向"
        lines.append(
            f"- **期望开盘:** 前收 {prev_close:.2f} × (1 + ({und_1d:+.2f}% × {lev:g}{dir_note})) "
            f"= {prev_close:.2f} × {1 + exp_pct / 100.0:.4f} ≈ **{exp_open:.2f}**"
            f"（{exp_pct:+.2f}%）"
        )

    if ref_1d is not None and und_1d is not None:
        same_dir = (ref_1d > 0) == (und_1d > 0)
        if same_dir:
            lines.append(
                f"- **传导状态:** ✅ 传导正常 —— 隔夜参考 {ref_1d:+.2f}% 与底层 {und_1d:+.2f}% 同向。"
            )
        else:
            lines.append(
                f"- **传导状态:** ⚠️ 传导断裂 —— 隔夜参考 {ref_1d:+.2f}% 与底层 {und_1d:+.2f}% 方向背离；"
                f"今日标的方向以底层本土盘为准，忽略隔夜参考收盘。"
                f"候选原因：US 假日缺口 / 外资流 / 事件悬挂（见新闻面 game_changer）"
            )

    return "\n".join(lines) + "\n"

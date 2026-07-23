"""Pre-trade portfolio context: what does adding THIS name do to the book?

`past_context` (the memory log) is hindsight — "how did similar past calls turn
out?". This is foresight: given the positions already held, how does the name
under analysis interact with them BEFORE the trade?

Two deterministic reads, no LLM:

1. **Cross-holding correlation** — daily-return correlation of the candidate vs
   each holding. A "diversifying" buy that is 0.9-correlated with three existing
   positions is really concentration in disguise (the MU + 2x-Hynix + KOSPI200
   trap: three tickers, one bet on Korean semis).
2. **Concentration** — sector and listing-currency exposure of the book with and
   without the candidate, so the PM sees "this lifts Korea-semis from 200% to
   280% — replace, don't stack".

Everything degrades: a holding whose OHLCV/identity can't be fetched is skipped,
and an empty ``holdings`` config yields '' so single-name runs are unchanged.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _safe(fn, default=None):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 — portfolio context is best-effort
        logger.debug("portfolio_context: %s", exc)
        return default


def parse_holdings(raw) -> list[dict]:
    """Parse the ``holdings`` config into ``[{ticker, weight}]``.

    Accepts a list of "TICKER" or "TICKER:weight" strings (weight in % of book),
    or a list of dicts. Bad entries are skipped. Weight is None when unspecified.
    """
    out: list[dict] = []
    for item in raw or []:
        if isinstance(item, dict) and item.get("ticker"):
            w = item.get("weight")
            out.append({"ticker": str(item["ticker"]).strip(),
                        "weight": float(w) if w is not None else None})
            continue
        if not isinstance(item, str) or not item.strip():
            continue
        ticker, _, w = item.partition(":")
        ticker = ticker.strip()
        if not ticker:
            continue
        weight = None
        if w.strip():
            try:
                weight = float(w.strip())
            except ValueError:
                weight = None
        out.append({"ticker": ticker, "weight": weight})
    return out


def _returns(symbol: str, curr_date: str, lookback: int = 60):
    """Daily returns Series for ``symbol``, or None on any failure."""
    from tradingagents.dataflows.stockstats_utils import load_ohlcv

    df = load_ohlcv(symbol, curr_date)
    if df is None or df.empty or "Close" not in df.columns:
        return None
    import pandas as pd

    s = df.copy()
    s["Date"] = pd.to_datetime(s["Date"], errors="coerce")
    s = s.dropna(subset=["Date"]).sort_values("Date").set_index("Date")["Close"]
    s = s[s.index <= pd.to_datetime(curr_date)].tail(lookback + 1)
    rets = s.pct_change().dropna()
    return rets if len(rets) >= 5 else None


def _identity(ticker: str) -> dict:
    """Identity (sector/industry/name), multi-source so it survives yfinance 403.

    Primary: resolve_instrument_identity (yfinance). Fallback: the fund/stock
    display name (Tencent → Sina, suffix-stripped) — when yfinance is throttled
    we at least recover a NAME, from which a coarse sector/region can be inferred
    downstream. Always returns a dict (possibly with just ``name``).
    """
    ident: dict = {}
    try:
        from tradingagents.agents.utils.agent_utils import resolve_instrument_identity

        ident = resolve_instrument_identity(ticker) or {}
    except Exception:  # noqa: BLE001 — identity is best-effort
        ident = {}
    if not ident.get("sector") and not ident.get("name") and not ident.get("company_name"):
        # yfinance gave nothing — recover a display name from the quote sources.
        try:
            from tradingagents.dataflows.etf_data import _fund_name

            name = _fund_name(ticker)
            if name:
                ident = {**ident, "name": name}
        except Exception:  # noqa: BLE001
            pass
    return ident


def _sector_bucket(ident: dict) -> str:
    """Coarse sector/theme for concentration, with a name-based fallback.

    Prefers yfinance sector/industry. When absent, infers a coarse theme from the
    display name keywords (semiconductor / Korea index / etc.) so a yfinance
    outage degrades to a usable bucket instead of a useless 'Unknown' wall.
    Returns 'Unknown' only when truly nothing is available.
    """
    sector = ident.get("sector") or ident.get("industry")
    if sector:
        return sector
    name = (ident.get("name") or ident.get("company_name") or "").lower()
    if not name:
        return "未知"
    # Keyword themes — generic, not per-ticker; covers the common memory/semi and
    # broad-index cases without hardcoding any specific symbol.
    themes = (
        (("半导体", "semicon", "hynix", "海力士", "memory", "chip", "micron", "tsmc", "nvidia", "英伟达"), "半导体"),
        (("kospi", "korea", "韩国", "海力士"), "韩国股票"),
        (("nasdaq", "标普", "s&p", "sp500", "道指", "dow"), "美股宽基指数"),
        (("沪深", "csi", "上证", "中证", "a50"), "A股指数"),
        (("hang seng", "恒生", "hsi"), "港股指数"),
        (("bank", "银行", "financ", "金融"), "金融"),
        (("oil", "energy", "能源", "石油"), "能源"),
    )
    for kws, label in themes:
        if any(k in name for k in kws):
            return f"{label}（按名称推断）"
    return "未知"


def _classify_sectors_llm(names: dict, llm) -> dict:
    """Classify every holding's sector in ONE LLM call, keyed by ticker.

    ``names`` maps ticker -> best-available display name. Returns ticker -> sector
    string (a GICS-style label, or for an index/ETF its theme like 'Korea equity').
    This is the cross-market, vendor-independent path the user asked for: no free
    API returns sector across US/HK/A markets, but the LLM classifies reliably
    from the company name. Returns {} on any failure so callers fall back to the
    deterministic name-keyword bucket.
    """
    if not llm or not names:
        return {}

    def call():
        import json
        import re

        listing = "\n".join(f"  {t}: {n or '(name unavailable)'}" for t, n in names.items())
        prompt = (
            "为组合集中度分析，把每个持仓归类到简洁的行业/主题。单家公司用标准"
            "行业（如『半导体』『饮料』『银行』）；指数/ETF 用其主题（如『韩国股票』"
            "『美股宽基指数』）。依据名称推断，不要臆造代码。用中文输出行业名。\n\n"
            f"持仓（代码: 名称）：\n{listing}\n\n"
            '只返回 JSON，把每个代码映射到其行业字符串，例如 '
            '{"MU": "半导体", "600519.SS": "饮料"}。'
        )
        resp = llm.invoke(prompt)
        txt = getattr(resp, "content", str(resp))
        m = re.search(r"\{.*\}", txt, re.DOTALL)
        if not m:
            raise ValueError("no JSON in sector-classifier response")
        out = json.loads(m.group(0))
        return {str(k): str(v) for k, v in out.items() if v}

    return _safe(call, default={}) or {}


def _listing_currency(ticker: str) -> str:
    """Listing currency from the ticker's market (us/hk/cn), or 'other'."""
    try:
        from tradingagents.dataflows.tencent import _classify

        market, _code = _classify(ticker)
        return {"us": "USD", "hk": "HKD", "cn": "CNY"}.get(market, "other")
    except Exception:  # noqa: BLE001
        return "other"


def _corr_label(c: float) -> str:
    if c >= 0.7:
        return "高 —— 实质是同一笔押注"
    if c >= 0.4:
        return "中等"
    if c <= -0.4:
        return "负相关 —— 真正的对冲"
    return "低 —— 有分散作用"


def build_portfolio_context(candidate: str, curr_date: str, holdings: list[dict],
                            llm=None) -> str:
    """Render the pre-trade portfolio-context block, or '' when no holdings.

    ``llm`` (when supplied) classifies each holding's sector in one call from its
    company name — the cross-market path that works when no vendor returns sector.
    Falls back to deterministic name-keyword buckets when no LLM / on failure.
    """
    held = [h for h in holdings if h["ticker"].upper() != candidate.upper()]
    if not held:
        return ""

    import pandas as pd

    cand_rets = _returns(candidate, curr_date)
    lines: list[str] = []

    # --- 1. Cross-holding correlation ---
    if cand_rets is not None:
        corr_rows = []
        skipped = []
        for h in held:
            hr = _returns(h["ticker"], curr_date)
            if hr is None:
                skipped.append(h["ticker"])
                continue
            joined = pd.concat([cand_rets.rename("c"), hr.rename("h")],
                               axis=1, join="inner").dropna()
            if len(joined) >= 5:
                c = float(joined["c"].corr(joined["h"]))
                corr_rows.append((h["ticker"], c))
            else:
                skipped.append(h["ticker"])
        if corr_rows:
            lines.append(f"**{candidate} 与当前持仓的相关性（近 60 日）：**")
            for tkr, c in sorted(corr_rows, key=lambda x: -abs(x[1])):
                lines.append(f"- {tkr}：{c:+.2f}（{_corr_label(c)}）")
            high = [t for t, c in corr_rows if c >= 0.7]
            if high:
                lines.append(
                    f"- ⚠️ {candidate} 与 {', '.join(high)} 高度相关 —— "
                    f"加入它是在加重集中度而非分散。可考虑"
                    f"替换某个现有持仓，而不是叠加。"
                )
        if skipped:
            # Be explicit rather than silently dropping — usually a too-new
            # listing (insufficient history) or an unfetchable quote.
            lines.append(
                f"- *（{', '.join(skipped)} 未计算相关性："
                f"价格历史不足或行情不可用）*"
            )
    else:
        lines.append(f"- {candidate} 收益数据不可用 —— 未计算相关性。")

    # --- 2. Sector & currency concentration ---
    sector_w: dict[str, float] = {}
    ccy_w: dict[str, float] = {}
    any_weight = any(h["weight"] is not None for h in held)
    n = len(held) + 1  # include candidate for equal-weight share
    eq = 100.0 / n
    book = held + [{"ticker": candidate, "weight": None}]

    # Resolve a display name per holding once, then classify all sectors in ONE
    # LLM call (cross-market, vendor-independent). Per-holding deterministic
    # keyword bucket is the fallback when the LLM has no label for that ticker.
    idents = {h["ticker"]: _identity(h["ticker"]) for h in book}
    names = {
        t: (d.get("name") or d.get("company_name") or "")
        for t, d in idents.items()
    }
    llm_sectors = _classify_sectors_llm(names, llm)

    for h in book:
        t = h["ticker"]
        w = h["weight"] if (any_weight and h["weight"] is not None) else eq
        sector = llm_sectors.get(t) or _sector_bucket(idents[t])
        ccy = _listing_currency(t)
        sector_w[sector] = sector_w.get(sector, 0.0) + w
        ccy_w[ccy] = ccy_w.get(ccy, 0.0) + w

    if sector_w:
        top_sector = max(sector_w, key=sector_w.get)
        lines.append("")
        lines.append("**加入 " + candidate + " 后的集中度：**")
        lines.append("- 按行业：" + "，".join(
            f"{s} {w:.0f}%" for s, w in sorted(sector_w.items(), key=lambda x: -x[1])))
        lines.append("- 按上市币种：" + "，".join(
            f"{c} {w:.0f}%" for c, w in sorted(ccy_w.items(), key=lambda x: -x[1])))
        if sector_w[top_sector] >= 50 and top_sector != "未知":
            lines.append(
                f"- ⚠️ {top_sector} 将占组合的 {sector_w[top_sector]:.0f}% —— "
                f"这是一笔集中的因子押注，而非分散的持仓。"
            )

    if not lines:
        return ""
    note = "" if any_weight else "（按等权假设 —— 未配置权重）"
    return (
        f"\n## 组合上下文（交易前 —— {candidate} 与你已持有的组合如何相互作用{note}）\n"
        + "\n".join(lines) + "\n"
    )

"""Cross-validation of a move: market vs sector vs idiosyncratic.

When a name moves hard, the analysts must not attribute it to a company-specific
story before checking the obvious: is the whole market down? is the sector down?
A −19% day on a Korean-semis ETF while KOSPI and Samsung are also red is a MARKET
move, not an ADR-dilution story. This module answers, deterministically:

  ① Did the benchmark index move the same way? (market vs idiosyncratic)
  ② Did peers / the sector move the same way? (sector vs single-name)

It computes the candidate's, the benchmark's, and each peer's 1-day and 5-day
returns from OHLCV the project already routes (``load_ohlcv``), then renders an
attribution block. Fully degrading: any leg that can't be fetched is omitted.
The "③ is there news?" leg is left to the news analyst — this gives it the
market/sector facts so it doesn't misattribute.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# A move at least this large (in %) is "notable" and triggers the cross-check
# emphasis in the rendered block.
_NOTABLE_MOVE_PCT = 5.0


def _safe(fn, default=None):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 — market context is best-effort
        logger.debug("market_context: %s", exc)
        return default


def _returns_1d_5d(symbol: str, curr_date: str) -> tuple[float | None, float | None]:
    """(1-day %, 5-day %) close-to-close for ``symbol`` on/before curr_date, or (None, None)."""
    from dromx.dataflows.stockstats_utils import load_ohlcv

    df = load_ohlcv(symbol, curr_date)
    if df is None or df.empty or "Close" not in df.columns:
        return None, None
    import pandas as pd

    s = df.copy()
    s["Date"] = pd.to_datetime(s["Date"], errors="coerce")
    s = s.dropna(subset=["Date"]).sort_values("Date")
    s = s[s["Date"] <= pd.to_datetime(curr_date)]["Close"].astype(float)
    if len(s) < 2:
        return None, None
    last = s.iloc[-1]
    d1 = (last / s.iloc[-2] - 1.0) * 100.0
    d5 = (last / s.iloc[-6] - 1.0) * 100.0 if len(s) >= 6 else None
    return d1, d5


def _resolve_benchmark(ticker: str, config: dict) -> str:
    """Benchmark index for ``ticker`` (suffix map), mirroring trading_graph._resolve_benchmark."""
    explicit = config.get("benchmark_ticker")
    if explicit:
        return explicit
    bmap = config.get("benchmark_map", {}) or {}
    up = ticker.upper()
    for suffix, bench in bmap.items():
        if suffix and up.endswith(suffix.upper()):
            return bench
    return bmap.get("", "SPY")


def _fmt(p: float | None) -> str:
    return "n/a" if p is None else f"{p:+.1f}%"


def _same_direction(a: float | None, b: float | None, thresh: float = 0.5) -> bool | None:
    """True if a,b move the same way (both beyond ±thresh%), False if opposite, None if unclear."""
    if a is None or b is None:
        return None
    if abs(a) < thresh or abs(b) < thresh:
        return None
    return (a > 0) == (b > 0)


def build_market_context(ticker: str, curr_date: str, config: dict | None = None) -> str:
    """Render the market-vs-sector cross-validation block, or '' if nothing usable.

    ``config`` supplies benchmark_map + peer_tickers (defaults to the global
    config). Peers reuse ``peer_tickers`` — the same list the analysts already use.
    """
    if config is None:
        from dromx.dataflows.config import get_config

        config = get_config()

    cand_1d, cand_5d = _safe(lambda: _returns_1d_5d(ticker, curr_date), (None, None))
    if cand_1d is None:
        return ""  # no candidate move → nothing to attribute

    benchmark = _resolve_benchmark(ticker, config)
    bench_1d, bench_5d = _safe(lambda: _returns_1d_5d(benchmark, curr_date), (None, None))

    peers = [p for p in (config.get("peer_tickers") or []) if p and p.upper() != ticker.upper()]
    peer_moves: list[tuple[str, float | None]] = []
    for p in peers:
        p1, _ = _safe(lambda pp=p: _returns_1d_5d(pp, curr_date), (None, None))
        if p1 is not None:
            peer_moves.append((p, p1))

    lines = [
        "## 异动归因（市场 vs 板块 vs 个股 —— 归因到公司故事之前必须先做的交叉验证）",
        f"- **{ticker}**：1日 {_fmt(cand_1d)}" + (f"，5日 {_fmt(cand_5d)}" if cand_5d is not None else ""),
    ]

    # ① index
    idx_same = _same_direction(cand_1d, bench_1d)
    if bench_1d is not None:
        verdict = ("同向 → 含市场驱动成分" if idx_same
                   else "反向/走平 → 无法用指数解释" if idx_same is False
                   else "不明确")
        lines.append(f"- **基准 {benchmark}**：1日 {_fmt(bench_1d)} —— {verdict}")
    else:
        lines.append(f"- 基准 {benchmark}：数据不可用")

    # ② peers / sector
    if peer_moves:
        peer_str = "，".join(f"{p} {_fmt(m)}" for p, m in peer_moves)
        same_cnt = sum(1 for _p, m in peer_moves if _same_direction(cand_1d, m))
        sector_verdict = (
            "同行同向 → 板块/主题行情" if same_cnt >= max(1, len(peer_moves) // 2 + (len(peer_moves) % 2))
            else "同行未普遍跟随 → 更偏个股"
        )
        lines.append(f"- **同业**：{peer_str} —— {sector_verdict}")
    else:
        lines.append("- 同业：未配置（设置 peer_tickers 以做板块交叉验证）")

    # attribution summary
    if abs(cand_1d) >= _NOTABLE_MOVE_PCT:
        peers_followed = sum(1 for _p, m in peer_moves if _same_direction(cand_1d, m))
        if idx_same and peers_followed >= 1:
            attribution = ("⚠️ 这主要是一次市场 / 板块行情 —— 在没有证据表明该标的涨跌幅"
                           "明显超过其指数与同业之前，不要归因于公司个体催化剂。")
        elif not idx_same and peers_followed == 0:
            # Index did not move with it (opposite OR flat) AND no peer followed.
            attribution = ("此次异动具有个体特征（指数与同业均未跟随）—— "
                           "应采用个股 / 事件驱动的解释。")
        else:
            attribution = ("混合型：部分来自市场/板块，部分来自个股。归因前请先"
                           "把指数/同业成分与个股特异残差分离开。")
        lines.append(f"- **归因：** {attribution}")

    return "\n".join(lines) + "\n"

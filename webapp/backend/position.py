"""Build the user's existing-position block for a run (position-aware analysis).

When the user declares a position in the name being analysed (shares + optional
cost basis), we render a compact markdown block that the Portfolio Manager and
Trader consume so the decision manages THAT position (add / hold / trim / exit)
instead of a generic build-from-flat call. Live P&L is computed from the latest
close via the engine data layer; everything degrades to a plain shares line if
price is unavailable. Empty / no shares → '' (flat, unchanged behaviour).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _last_close(ticker: str, curr_date: str) -> float | None:
    try:
        from datetime import date as _date

        from tradingagents.dataflows.stockstats_utils import load_ohlcv

        df = load_ohlcv(ticker, (curr_date or "").strip() or _date.today().isoformat())
        if df is None or getattr(df, "empty", True):
            return None
        cols = {c.lower(): c for c in df.columns}
        ccol = cols.get("close")
        if ccol is None:
            return None
        return float(df[ccol].iloc[-1])
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.debug("position _last_close(%s) failed: %s", ticker, exc)
        return None


def build_position_context(
    ticker: str, trade_date: str, shares: float | None, cost_basis: float | None,
) -> str:
    """Render the position block, or '' when the user holds nothing.

    ``shares`` may be negative (a short). ``cost_basis`` is per-share in the
    instrument's quote currency; when absent we still state the size but skip
    P&L. The block is intentionally terse — it is prompt context, not a report.
    """
    if not shares or shares == 0:
        return ""

    side = "多头" if shares > 0 else "空头"
    qty = abs(shares)
    lines = [f"- 方向/数量：{side} {qty:g} 股"]

    if cost_basis and cost_basis > 0:
        lines.append(f"- 成本价：{cost_basis:g}")
        px = _last_close(ticker, trade_date)
        if px is not None:
            # long P&L = (px - cost)/cost; short flips the sign.
            pnl_pct = (px - cost_basis) / cost_basis * (1 if shares > 0 else -1) * 100
            pnl_val = (px - cost_basis) * shares  # signed by shares (short → negative shares)
            lines.append(f"- 最新价：{px:g}")
            lines.append(
                f"- 浮动盈亏：{pnl_pct:+.1f}%（约 {pnl_val:+,.0f}，按最新价）"
            )
            lines.append(
                "- 该持仓已" + ("盈利" if pnl_pct >= 0 else "亏损")
                + "，请据此给出持仓管理建议（加/持/减/清），并说明原始买入逻辑是否仍成立。"
            )
        else:
            lines.append("- （最新价不可用，无法计算浮盈亏）")
    else:
        lines.append("- （未提供成本价，只按持有数量做持仓管理判断）")

    return "**用户在本标的的现有持仓：**\n" + "\n".join(lines)

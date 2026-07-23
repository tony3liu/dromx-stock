"""Pattern discovery — the deterministic forensics engine.

A prediction-type agent takes indicators and sums them into a directional call.
A forensics-type agent does the opposite: it finds the ANOMALIES first, then
asks "what was at that exact point?" — reversing the usual "I have a level, did
price touch it?" into "price stopped at a weird point, which level is there?".

This builder runs that reverse search deterministically (no LLM), producing
EVIDENCE the prediction-type analysts then reason about:

  ① Anomaly detection — z-score of amplitude / gap-open / close-position over
     the recent window; flag days that deviate >2σ from the norm.
  ② Pivot extraction — the intraday low (where price stopped and reversed).
  ③ Reverse anchor search — for each anomaly day's pivot, compete candidate
     anchors (MA20/50/100, prior low/high, round numbers) by deviation %; the
     smallest deviation wins. The anchor is DISCOVERED, not assumed.
  ④ Precision statistics — if one anchor wins across ≥2 anomaly days with
     sub-0.5% min / sub-1.5% median deviation, flag algorithmic-precision
     evidence (not market consensus).
  ⑤ Evolution — precision trend + close-vs-anchor break, the second-derivative
     read on whether control is tightening or loosening.

Pure pandas; fully degrading to '' when the tape is normal (no anomaly) or
data is thin, so a quiet market yields nothing rather than a fabricated
pattern. Mirrors the best-effort contract of overnight_transmission /
market_context. The anchor is NEVER hardcoded — it is the candidate with the
smallest deviation, so the data names the level, not a table.
"""

from __future__ import annotations

import logging
import math
from collections import Counter

logger = logging.getLogger(__name__)

_LOOKBACK = 60              # anomaly-detection window (recent days we score)
_MIN_ROWS = 20              # need this many rows to compute a usable z-score
_ANOMALY_Z = 2.0            # |z| threshold for an anomaly day
_PRECISION_MIN_DEV = 0.5    # min deviation (%) across wins for "algorithmic precision"
_PRECISION_MEDIAN_DEV = 1.5  # median deviation (%) for "algorithmic precision"
_MAIN_ANCHOR_MIN_WINS = 2   # anchor must win this many anomaly days to be "main"


def _safe(fn, default=None):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 — forensics is best-effort, never aborts
        logger.debug("pattern_discovery: %s", exc)
        return default


def _load_ohlcv_history(ticker: str, curr_date: str):
    """Full OHLCV history ≤ curr_date — full history so MA100 is computable."""
    from tradingagents.dataflows.stockstats_utils import load_ohlcv
    import pandas as pd

    df = load_ohlcv(ticker, curr_date)
    if df is None or df.empty:
        return None
    df = df.copy()
    if "Date" not in df.columns:
        # yfinance keeps dates in the index; promote to a column first.
        df = df.reset_index().rename(columns={"index": "Date", "Datetime": "Date"})
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date")
    df = df[df["Date"] <= pd.to_datetime(curr_date)]
    for col in ("Open", "High", "Low", "Close"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Close"])
    return df.set_index("Date")


def _add_anomaly_features(df):
    """Amplitude / gap-open / close-position + their rolling z-scores."""
    import pandas as pd

    d = df.copy()
    d["prev_close"] = d["Close"].shift(1)
    d["amplitude"] = (d["High"] - d["Low"]) / d["Close"]
    d["gap_open"] = (d["Open"] - d["prev_close"]) / d["prev_close"]
    rng = (d["High"] - d["Low"]).where(lambda x: x > 0)
    d["close_position"] = ((d["Close"] - d["Low"]) / rng).astype(float)

    window = min(_LOOKBACK, len(d))
    min_periods = max(5, window // 3)
    for col in ("amplitude", "gap_open", "close_position"):
        roll = d[col].rolling(window, min_periods=min_periods)
        d[col + "_z"] = (d[col] - roll.mean()) / roll.std()
    return d


def _candidate_anchors(df):
    """Per-day candidate anchor values: MA20/50/100 + prior low/high.

    MA uses the full history (so MA100 is computable). Prior low/high use a
    trailing 60-day window EXCLUDING the current day (shift(1)) so a day's own
    low never becomes its own anchor. Round numbers are added per-pivot later
    (they depend on the pivot's price scale).
    """
    close = df["Close"]
    low = df["Low"]
    high = df["High"]
    return {
        "MA20": close.rolling(20).mean(),
        "MA50": close.rolling(50).mean(),
        "MA100": close.rolling(100).mean(),
        "前低": low.shift(1).rolling(_LOOKBACK, min_periods=10).min(),
        "前高": high.shift(1).rolling(_LOOKBACK, min_periods=10).max(),
    }


def _round_number_anchors(price: float) -> dict:
    """A few round-number levels near `price` (psychological anchors).

    Step = 10**floor(log10(price)): for ₩2,045,000 the step is ₩1,000,000
    (levels ₩0/₩1M/₩2M/₩3M/₩4M); for $204.5 the step is $100 ($0/$100/$200/$300/
    $400). Coarse on purpose — round numbers are a fallback candidate, not a
    precision competitor that should shadow an MA. Returns {} when unusable.
    """
    if not price or price <= 0:
        return {}
    try:
        step = 10 ** math.floor(math.log10(price))
    except (ValueError, OverflowError):
        return {}
    if step <= 0:
        return {}
    base = round(price / step) * step
    return {f"整数{base + k * step:g}": float(base + k * step) for k in (-2, -1, 0, 1, 2)}


def _deviation(pivot: float, anchor: float) -> float | None:
    if not pivot or not anchor or anchor == 0:
        return None
    return (pivot - anchor) / anchor * 100.0


def _fmt_date(ts) -> str:
    """Cross-platform M/D (no leading zeros) — strftime %-m is GNU-only."""
    return f"{ts.month}/{ts.day}"


def build_pattern_discovery(ticker: str, curr_date, config: dict | None = None) -> str:
    """Render the forensics discovery block, or '' when nothing anomalous."""
    if config is None:
        from tradingagents.dataflows.config import get_config
        config = get_config()

    df = _safe(lambda: _load_ohlcv_history(ticker, str(curr_date)))
    if df is None or len(df) < _MIN_ROWS:
        return ""

    d = _safe(lambda: _add_anomaly_features(df))
    if d is None:
        return ""

    # ① Anomaly days: |z| >= threshold on any dimension, in the recent window.
    # No dropna — a dimension whose z is NaN (e.g. gap_open when Open==Close
    # every day, std=0) must not disqualify a day that is anomalous on another.
    z_cols = [c for c in ("amplitude_z", "gap_open_z", "close_position_z") if c in d.columns]
    d_recent = d.tail(_LOOKBACK)
    anomaly_mask = (d_recent[z_cols].abs() >= _ANOMALY_Z).any(axis=1)
    anomaly = d_recent[anomaly_mask]
    if anomaly.empty:
        return ""  # normal tape — honest "", don't fabricate a pattern

    anchors = _safe(lambda: _candidate_anchors(d)) or {}

    # ②③ For each anomaly day: compete BOTH pivots (Low AND High) against the
    # candidate anchors — direction-neutral. A short hunt on MA50 surfaces via
    # the Low touching it; a breakout test via the High touching prior high; a
    # range-bound tape via both edges touching the range. The day's discovery
    # is the pivot+anchor pair with the smallest |deviation| across both sides.
    rows = []
    for date, day in anomaly.iterrows():
        close = float(day["Close"])
        day_best = None  # (pivot_label, pivot_val, best_anchor, best_dev, devs)
        for plabel, pval in (("低", float(day["Low"])), ("高", float(day["High"]))):
            if not pval or pval <= 0:
                continue
            candidates = {}
            for name, series in anchors.items():
                if date in series.index:
                    try:
                        fval = float(series.loc[date])
                    except (TypeError, ValueError):
                        continue
                    if math.isfinite(fval) and fval > 0:
                        candidates[name] = fval
            for name, val in _round_number_anchors(pval).items():
                candidates.setdefault(name, val)
            devs = {n: _deviation(pval, v) for n, v in candidates.items()}
            devs = {n: v for n, v in devs.items() if v is not None and math.isfinite(v)}
            if not devs:
                continue
            best_anchor = min(devs, key=lambda k: abs(devs[k]))
            best_dev = devs[best_anchor]
            if day_best is None or abs(best_dev) < abs(day_best[3]):
                day_best = (plabel, pval, best_anchor, best_dev, devs)
        if day_best is None:
            continue
        rows.append({
            "date": date,
            "pivot_label": day_best[0],
            "pivot": day_best[1],
            "close": close,
            "devs": day_best[4],
            "best": day_best[2],
            "best_dev": day_best[3],
        })
    if not rows:
        return ""

    # ④ Precision statistics: which anchor wins most often, how tight, and the
    # dominant pivot direction (低=做空触锚 / 高=做多触锚 / 混合=双向博弈).
    best_counts = Counter(r["best"] for r in rows)
    main_anchor, main_wins = best_counts.most_common(1)[0]
    main_rows = [r for r in rows if r["best"] == main_anchor]
    main_devs = [abs(r["best_dev"]) for r in main_rows]
    main_devs_sorted = sorted(main_devs)
    median_dev = main_devs_sorted[len(main_devs_sorted) // 2]
    is_algorithmic = (
        main_wins >= _MAIN_ANCHOR_MIN_WINS
        and min(main_devs) < _PRECISION_MIN_DEV
        and median_dev < _PRECISION_MEDIAN_DEV
    )
    dir_counts = Counter(r["pivot_label"] for r in main_rows)
    main_dir, main_dir_count = dir_counts.most_common(1)[0]
    if main_dir_count >= max(2, len(main_rows) // 2 + 1):
        direction_label = "做空方向（低点触锚）" if main_dir == "低" else "做多方向（高点触锚）"
    else:
        direction_label = "双向（低/高均触锚）"

    # ⑤ Evolution: precision trend + close-vs-pivot break — direction-neutral.
    precision_trend = ""
    if len(main_devs) >= 2:
        if main_devs[-1] > main_devs[0] * 1.0001:
            precision_trend = "精度下降（控制力减弱）"
        elif main_devs[-1] < main_devs[0] * 0.9999:
            precision_trend = "精度上升（控制力增强）"
    break_flag = ""
    if main_rows:
        last = main_rows[-1]
        if last["pivot_label"] == "低" and last["close"] < last["pivot"] * 0.999:
            break_flag = (
                f"最后一日收盘 {last['close']:.2f} 跌破低转折 {last['pivot']:.2f} → 破位下行"
            )
        elif last["pivot_label"] == "高" and last["close"] > last["pivot"] * 1.001:
            break_flag = (
                f"最后一日收盘 {last['close']:.2f} 突破高转折 {last['pivot']:.2f} → 破位上行"
            )

    # --- render ---
    lines = ["## 取证发现（异常驱动 · 反向锚点搜索）"]

    dates_str = "，".join(_fmt_date(r["date"]) for r in rows)
    lines.append(
        f"- **异常日**（近 {_LOOKBACK} 日,振幅/低开/收盘位置 z≥{_ANOMALY_Z:g}）:{dates_str}"
    )

    # Deviation competition table — only anchors that actually competed.
    seen = []
    for r in rows:
        for n in r["devs"]:
            if n not in seen:
                seen.append(n)

    def _order(n):
        for i, p in enumerate(("MA20", "MA50", "MA100", "前低", "前高")):
            if n == p:
                return i
        return 5

    anchor_names = sorted(seen, key=_order)
    lines.append("")
    lines.append("**转折点 vs 候选锚点偏差竞争:**")
    header = "| 日期 | 转折点 |" + "".join(f" {n} |" for n in anchor_names) + " 最佳锚点 | 偏差 |"
    align = "|---|---:|" + "".join("---:|" for _ in anchor_names) + "---|---:|"
    lines.append(header)
    lines.append(align)
    for r in rows:
        cells = "".join(
            f" {r['devs'][n]:+.2f}% |" if n in r["devs"] else " n/a |"
            for n in anchor_names
        )
        lines.append(
            f"| {_fmt_date(r['date'])} | {r['pivot_label']} {r['pivot']:.2f} |{cells} {r['best']} | {r['best_dev']:+.2f}% |"
        )

    # Precision verdict.
    if is_algorithmic:
        lines.append(
            f"- **精度统计**:**{main_anchor}** 在 {main_wins}/{len(rows)} 异常日胜出,"
            f"偏差最小 {min(main_devs):.2f}%、中位 {median_dev:.2f}% "
            f"· {direction_label} "
            f"→ ⚠️ 算法精度证据（非市场合力）"
        )
    elif main_wins >= _MAIN_ANCHOR_MIN_WINS:
        lines.append(
            f"- **精度统计**:**{main_anchor}** 在 {main_wins}/{len(rows)} 异常日胜出,"
            f"但偏差偏大（最小 {min(main_devs):.2f}%）· {direction_label} → 弱信号,非精确控制"
        )
    else:
        tally = "，".join(f"{n}×{c}" for n, c in best_counts.most_common())
        lines.append(
            f"- **精度统计**:各日最佳锚点分散（{tally}）→ 无单一锚点主导"
        )

    # Evolution.
    evo = []
    if precision_trend:
        evo.append(precision_trend)
    if break_flag:
        evo.append(break_flag)
    if evo:
        lines.append(f"- **演变**:{' · '.join(evo)}")

    return "\n".join(lines) + "\n"

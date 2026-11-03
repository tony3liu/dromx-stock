"""Advanced technical indicators — 高级技术指标计算库（纯 pandas/numpy 实现）

覆盖 FinceptTerminal technicals 目录的指标类型（趋势/动量/波动/量能），
但全部按公开标准公式重新实现（AGPL 代码不复制；数学公式不受版权限制）。

设计目标：
- 输入：标准 OHLCV DataFrame（列名 Open/High/Low/Close/Volume，Date 可作列或索引）
- 输出：每个指标返回 dict {指标名: 最新值}，附简要解读文本
- 无外部指标库依赖（不依赖 TA-Lib / stockstats），仅 pandas + numpy
- 与 stockstats 命名不冲突，可独立调用

用法：:

    from dromx.dataflows.advanced_indicators import compute_advanced_indicators
    vals = compute_advanced_indicators(ohlcv_df, indicators=["ichimoku", "adx", "mfi"])
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _ensure_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce OHLCV columns to numeric; raise if the required ones are missing."""
    required = {"Open", "High", "Low", "Close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"OHLCV frame missing columns: {sorted(missing)}")
    out = df.copy()
    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def _latest(series: pd.Series, default: float | None = None) -> float | None:
    """Return the last non-NaN value, else ``default``."""
    valid = series.dropna()
    if valid.empty:
        return default
    return float(valid.iloc[-1])


def _shift_latest(series: pd.Series, n: int) -> float | None:
    """Return the latest non-NaN value from n periods back (excluding the current bar).

    ``series.iloc[-n:]`` would include the current bar, so ``prev`` computed that
    way always equals the current value and trend verdicts can never fire. This
    helper looks at the window ``[-n-1:-1]`` instead (the n values strictly
    before the latest)."""
    if len(series) < n + 1:
        return None
    return _latest(series.iloc[-(n + 1):-1])


# ---------------------------------------------------------------------------
# 趋势类指标
# ---------------------------------------------------------------------------


def ichimoku(df: pd.DataFrame, conv: int = 9, base: int = 26, span_b: int = 52, displ: int = 26) -> dict:
    """Ichimoku Cloud（一目均衡表）。

    Tenkan-sen(转换线) = (9H+9L)/2；Kijun-sen(基准线) = (26H+26L)/2；
    Senkou A(先行带A) = (Tenkan+Kijun)/2 前移26；Senkou B(先行带B) = (52H+52L)/2 前移26；
    Chikou(迟行线) = 收盘价后移26。云厚 (A-B) 判断支撑压力。
    """
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    tenkan = (high.rolling(conv).max() + low.rolling(conv).min()) / 2
    kijun = (high.rolling(base).max() + low.rolling(base).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(displ)
    senkou_b = ((high.rolling(span_b).max() + low.rolling(span_b).min()) / 2).shift(displ)
    chikou = close.shift(-displ)
    chikou_val = _latest(chikou)

    price = _latest(close)
    senkou_a_val = _latest(senkou_a)
    senkou_b_val = _latest(senkou_b)
    # 云层需至少一侧有值才能判断；否则数据不足（不能拿 0.0 兜底制造假信号）
    if price is None or senkou_a_val is None or senkou_b_val is None:
        trend = "数据不足"
    else:
        cloud_top = max(senkou_a_val, senkou_b_val)
        cloud_bot = min(senkou_a_val, senkou_b_val)
        if price > cloud_top:
            trend = "价格在云层上方（多头强势）"
        elif price < cloud_bot:
            trend = "价格在云层下方（空头强势）"
        else:
            trend = "价格在云层内部（趋势不明，等待方向选择）"

    return {
        "tenkan_sen": _latest(tenkan),
        "kijun_sen": _latest(kijun),
        "senkou_a": _latest(senkou_a),
        "senkou_b": _latest(senkou_b),
        "chikou": chikou_val,
        "ichimoku_verdict": trend,
    }


def adx(df: pd.DataFrame, period: int = 14) -> dict:
    """Average Directional Index（平均趋向指数）+ +DI/-DI。

    TR = max(H-L, |H-prevC|, |L-prevC|)；+DM = H-prevH>prevL-L ? H-prevH : 0；
    -DM = prevL-L>H-prevH ? prevL-L : 0。Wilder 平滑后：
    +DI = 100*sm(+DM)/sm(TR)；DX = 100*|+DI - -DI|/(+DI + -DI)；ADX = Wilder平滑(DX)。
    """
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    prev_close = close.shift(1)
    prev_high = high.shift(1)
    prev_low = low.shift(1)

    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    plus_dm = np.where((high - prev_high) > (prev_low - low), (high - prev_high).clip(lower=0), 0.0)
    minus_dm = np.where((prev_low - low) > (high - prev_high), (prev_low - low).clip(lower=0), 0.0)

    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / period, adjust=False).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / period, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_val = dx.ewm(alpha=1 / period, adjust=False).mean()

    pdi = _latest(plus_di)
    mdi = _latest(minus_di)
    a = _latest(adx_val)
    if a is None or pdi is None or mdi is None:
        verdict = "数据不足"
    elif a > 25 and pdi > mdi:
        verdict = f"趋势强（ADX={a:.1f}），多头主导（+DI > -DI）"
    elif a > 25 and mdi > pdi:
        verdict = f"趋势强（ADX={a:.1f}），空头主导（-DI > +DI）"
    else:
        verdict = f"趋势弱（ADX={a:.1f}），盘整概率大"

    return {"adx": a, "plus_di": pdi, "minus_di": mdi, "adx_verdict": verdict}


def vortex(df: pd.DataFrame, period: int = 14) -> dict:
    """Vortex Indicator（涡旋指标）— 判断趋势启动。

    VI+ = sm(|H - prevL|)/sm(TR)；VI- = sm(|L - prevH|)/sm(TR)。
    VI+ 上穿 VI- 且均 >1 → 多头趋势；反之空头。
    """
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)

    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    vi_plus = (high - low.shift(1)).abs().rolling(period).sum() / tr.rolling(period).sum()
    vi_minus = (low - high.shift(1)).abs().rolling(period).sum() / tr.rolling(period).sum()

    vp = _latest(vi_plus)
    vm = _latest(vi_minus)
    if vp is None or vm is None:
        verdict = "数据不足"
    elif vp > 1 and vp > vm:
        verdict = "多头涡旋主导（VI+ 领先）"
    elif vm > 1 and vm > vp:
        verdict = "空头涡旋主导（VI- 领先）"
    else:
        verdict = "涡旋强度不足 1，趋势尚未确认"

    return {"vortex_plus": vp, "vortex_minus": vm, "vortex_verdict": verdict}


def psar(df: pd.DataFrame, step: float = 0.02, max_step: float = 0.2) -> dict:
    """Parabolic SAR（抛物线转向）。

    经典递归算法：SAR 随极值点（EP）以加速度推进，翻转时重置。
    返回当前 SAR 值与方向判断。
    """
    high = df["High"].to_numpy(dtype=float)
    low = df["Low"].to_numpy(dtype=float)
    close = df["Close"].to_numpy(dtype=float)
    n = len(close)
    if n < 3:
        return {"psar": None, "psar_direction": "数据不足"}

    sar = np.full(n, np.nan)
    af = step
    uptrend = close[1] >= close[0]
    if uptrend:
        sar[0] = low[0]
        ep = high[0]
    else:
        sar[0] = high[0]
        ep = low[0]

    for i in range(1, n):
        sar[i] = sar[i - 1] + af * (ep - sar[i - 1])
        if uptrend:
            sar[i] = min(sar[i], low[i - 1], low[i - 2] if i >= 2 else low[i - 1])
            if low[i] < sar[i]:
                uptrend = False
                sar[i] = ep
                ep = low[i]
                af = step
            elif high[i] > ep:
                ep = high[i]
                af = min(af + step, max_step)
        else:
            sar[i] = max(sar[i], high[i - 1], high[i - 2] if i >= 2 else high[i - 1])
            if high[i] > sar[i]:
                uptrend = True
                sar[i] = ep
                ep = high[i]
                af = step
            elif low[i] < ep:
                ep = low[i]
                af = min(af + step, max_step)

    last_sar = float(sar[-1]) if not np.isnan(sar[-1]) else None
    direction = "多头（价格在 SAR 上方）" if (last_sar is not None and close[-1] > last_sar) else (
        "空头（价格在 SAR 下方）" if last_sar is not None else "数据不足"
    )
    return {"psar": last_sar, "psar_direction": direction}


def aroon(df: pd.DataFrame, period: int = 25) -> dict:
    """Aroon（阿隆指标）。

    AroonUp = 100 * (period - 距period内最高价天数) / period；
    AroonDown 同理取最低价。AroonOsc = Up - Down。
    """
    high = df["High"]
    low = df["Low"]

    def _aroon_dist(series: pd.Series, which: str) -> pd.Series:
        # 用 rolling apply 计算距极值最近的天数
        def _dist(window: np.ndarray) -> float:
            if which == "up":
                extreme = np.nanmax(window)
                idx = np.flatnonzero(window == extreme)[-1]
            else:
                extreme = np.nanmin(window)
                idx = np.flatnonzero(window == extreme)[-1]
            return float(period - (len(window) - 1 - idx))

        return series.rolling(period + 1).apply(_dist, raw=True)

    aroon_up = 100 * _aroon_dist(high, "up") / period
    aroon_down = 100 * _aroon_dist(low, "down") / period
    aroon_osc = aroon_up - aroon_down

    au = _latest(aroon_up)
    ad = _latest(aroon_down)
    osc = _latest(aroon_osc)
    if au is None or ad is None:
        verdict = "数据不足"
    elif au > 70 and au > ad:
        verdict = "强多头（AroonUp 高位，趋势新高高频出现）"
    elif ad > 70 and ad > au:
        verdict = "强空头（AroonDown 高位，趋势新低高频出现）"
    else:
        verdict = "区间震荡（无持续新高/新低）"

    return {"aroon_up": au, "aroon_down": ad, "aroon_osc": osc, "aroon_verdict": verdict}


def stc(df: pd.DataFrame, fast: int = 23, slow: int = 50, cycle: int = 10, smooth1: int = 3, smooth2: int = 3) -> dict:
    """Schaff Trend Cycle（STC 趋势周期）— 0~100 区间，判断趋势/震荡。

    对收盘价做 MACD（fast/slow），把 MACD 线用 RSI 式随机指标映射到 0~100，
    再双重平滑。>25 金叉 / >75 死叉参考线。
    """
    close = df["Close"]
    macd_line = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()

    def _stoch_rsi_like(series: pd.Series, period: int) -> pd.Series:
        low = series.rolling(period).min()
        high = series.rolling(period).max()
        rng = (high - low).replace(0, np.nan)
        return 100 * (series - low) / rng

    k = _stoch_rsi_like(macd_line, cycle)
    d = k.ewm(span=smooth1, adjust=False).mean()
    k2 = _stoch_rsi_like(d, cycle)
    stc_val = k2.ewm(span=smooth2, adjust=False).mean()

    v = _latest(stc_val)
    if v is None:
        verdict = "数据不足"
    elif v < 25:
        verdict = f"STC={v:.0f}，位于低位（潜在多头启动区）"
    elif v > 75:
        verdict = f"STC={v:.0f}，位于高位（潜在见顶/过热区）"
    else:
        verdict = f"STC={v:.0f}，中性区间"

    return {"stc": v, "stc_verdict": verdict}


def kst(df: pd.DataFrame, roc1: int = 10, roc2: int = 15, roc3: int = 20, roc4: int = 30,
        sma1: int = 10, sma2: int = 10, sma3: int = 10, sma4: int = 15, signal: int = 9) -> dict:
    """Know Sure Thing（KST 综合动量）。

    四条不同周期 ROC 的加权平滑和：KST = sma(roc1)+2*sma(roc2)+3*sma(roc3)+4*sma(roc4)。
    与 9 期信号线比较判断买卖。
    """
    close = df["Close"]
    rocs = [close.pct_change(p) * 100 for p in (roc1, roc2, roc3, roc4)]
    kst_val = (
        rocs[0].rolling(sma1).mean()
        + 2 * rocs[1].rolling(sma2).mean()
        + 3 * rocs[2].rolling(sma3).mean()
        + 4 * rocs[3].rolling(sma4).mean()
    )
    signal_line = kst_val.rolling(signal).mean()

    kv = _latest(kst_val)
    sv = _latest(signal_line)
    if kv is None or sv is None:
        verdict = "数据不足"
    elif kv > sv and kv > 0:
        verdict = "KST 在信号线上方且为正（多头动能）"
    elif kv < sv and kv < 0:
        verdict = "KST 在信号线下方且为负（空头动能）"
    else:
        verdict = "KST 与信号线纠缠，动能中性"

    return {"kst": kv, "kst_signal": sv, "kst_verdict": verdict}


def dpo(df: pd.DataFrame, period: int = 20) -> dict:
    """Detrended Price Oscillator（去趋势价格振荡器）。

    DPO = 收盘价 - period/2+1 天前的 period SMA。去除长趋势后观察短周期摆动。
    """
    close = df["Close"]
    shifted_sma = close.rolling(period).mean().shift(period // 2 + 1)
    dpo_val = close - shifted_sma

    v = _latest(dpo_val)
    return {"dpo": v, "dpo_verdict": f"DPO={'正' if v and v > 0 else '负'}，{'价格在中期均线上方（偏强）' if v and v > 0 else '价格在中期均线下方（偏弱）'}" if v is not None else "数据不足"}


def trix(df: pd.DataFrame, period: int = 15, signal: int = 9) -> dict:
    """TRIX（三重指数平滑平均）— 消除短期波动，抓长趋势转折。

    TRIX = EMA(EMA(EMA(close, n), n), n) 的单期百分比变化。
    """
    close = df["Close"]
    triple = close.ewm(span=period, adjust=False).mean().ewm(span=period, adjust=False).mean().ewm(span=period, adjust=False).mean()
    trix_val = triple.pct_change() * 100
    signal_line = trix_val.rolling(signal).mean()

    tv = _latest(trix_val)
    sv = _latest(signal_line)
    if tv is None or sv is None:
        verdict = "数据不足"
    elif tv > sv:
        verdict = "TRIX 在信号线上方（上升趋势延续）"
    else:
        verdict = "TRIX 在信号线下方（趋势转弱/下降）"

    return {"trix": tv, "trix_signal": sv, "trix_verdict": verdict}


def mass_index(df: pd.DataFrame, fast: int = 9, slow: int = 25, threshold: float = 27.0) -> dict:
    """Mass Index（梅斯指数）— 用 H-L 区间的 EMA 比值侦测反转。

    ratio = EMA9(H-L) / EMA25(H-L)；MI = sum(最近25期 ratio)。MI 突破 27 后回落为反转信号。
    """
    hilo = df["High"] - df["Low"]
    ema_fast = hilo.ewm(span=fast, adjust=False).mean()
    ema_slow = hilo.ewm(span=slow, adjust=False).mean()
    ratio = ema_fast / ema_slow
    mi = ratio.rolling(slow).sum()

    v = _latest(mi)
    if v is None:
        verdict = "数据不足"
    elif v > threshold:
        verdict = f"MI={v:.1f} 突破 {threshold}，关注反转（等待回落确认）"
    else:
        verdict = f"MI={v:.1f}，未到反转阈值"

    return {"mass_index": v, "mass_index_verdict": verdict}


# ---------------------------------------------------------------------------
# 动量类指标
# ---------------------------------------------------------------------------


def kama(df: pd.DataFrame, period: int = 10, fast: int = 2, slow: int = 30) -> dict:
    """Kaufman Adaptive Moving Average（考夫曼自适应均线）。

    效率系数 ER = |close - close[n]| / sum(|close - close[1:]|, n)；
    平滑常数 sc = [ER*(2/(fast+1)-2/(slow+1)) + 2/(slow+1)]^2；
    KAMA = prev + sc * (close - prev)。趋势期快、震荡期慢。
    """
    close = df["Close"]
    change = (close - close.shift(period)).abs()
    volatility = close.diff().abs().rolling(period).sum()
    er = (change / volatility.replace(0, np.nan)).fillna(0)
    fast_sc = 2 / (fast + 1)
    slow_sc = 2 / (slow + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    kama_vals = close.copy()
    prev = float(close.iloc[0]) if len(close) else np.nan
    for i in range(1, len(close)):
        c = float(close.iloc[i])
        if np.isnan(c):
            kama_vals.iloc[i] = prev
            continue
        prev = prev + float(sc.iloc[i]) * (c - prev)
        kama_vals.iloc[i] = prev

    kv = _latest(kama_vals)
    price = _latest(close)
    if kv is None or price is None:
        verdict = "数据不足"
    elif price > kv:
        verdict = "价格在 KAMA 上方（自适应趋势偏多）"
    else:
        verdict = "价格在 KAMA 下方（自适应趋势偏空）"

    return {"kama": kv, "kama_verdict": verdict}


def ppo(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """Percentage Price Oscillator（百分比价格振荡器）。

    PPO = 100 * (EMA12 - EMA26) / EMA26。消除价格量纲，便于跨标的比较。
    """
    close = df["Close"]
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    ppo_val = 100 * (ema_fast - ema_slow) / ema_slow
    signal_line = ppo_val.ewm(span=signal, adjust=False).mean()
    hist = ppo_val - signal_line

    pv = _latest(ppo_val)
    hv = _latest(hist)
    if pv is None or hv is None:
        verdict = "数据不足"
    elif hv > 0:
        verdict = f"PPO 动能转强（柱={hv:.2f}>0）"
    else:
        verdict = f"PPO 动能转弱（柱={hv:.2f}<0）"

    return {"ppo": pv, "ppo_signal": _latest(signal_line), "ppo_hist": hv, "ppo_verdict": verdict}


def pvo(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """Percentage Volume Oscillator（百分比成交量振荡器）。

    与 PPO 相同公式但用于成交量，衡量量能变化趋势。
    """
    volume = df["Volume"]
    ema_fast = volume.ewm(span=fast, adjust=False).mean()
    ema_slow = volume.ewm(span=slow, adjust=False).mean()
    pvo_val = 100 * (ema_fast - ema_slow) / ema_slow
    signal_line = pvo_val.ewm(span=signal, adjust=False).mean()
    hist = pvo_val - signal_line

    pv = _latest(pvo_val)
    hv = _latest(hist)
    if pv is None or hv is None:
        verdict = "数据不足"
    elif hv > 0:
        verdict = "量能动能转强"
    else:
        verdict = "量能动能转弱"

    return {"pvo": pv, "pvo_signal": _latest(signal_line), "pvo_hist": hv, "pvo_verdict": verdict}


def roc(df: pd.DataFrame, period: int = 12) -> dict:
    """Rate of Change（变动率）。

    ROC = 100 * (close - close[n]) / close[n]。
    """
    close = df["Close"]
    roc_val = 100 * close.pct_change(period)
    v = _latest(roc_val)
    if v is None:
        verdict = "数据不足"
    elif v > 0:
        verdict = f"ROC={v:.2f}%，{period} 日动量为正"
    else:
        verdict = f"ROC={v:.2f}%，{period} 日动量为负"
    return {"roc": v, "roc_verdict": verdict}


def tsi(df: pd.DataFrame, fast: int = 13, slow: int = 25, signal: int = 13) -> dict:
    """True Strength Index（真实强弱指数）。

    TSI = 100 * EMA13(EMA25(动量)) / EMA13(EMA25(|动量|))。
    """
    close = df["Close"]
    mom = close.diff()
    double_ema = mom.ewm(span=slow, adjust=False).mean().ewm(span=fast, adjust=False).mean()
    double_abs = mom.abs().ewm(span=slow, adjust=False).mean().ewm(span=fast, adjust=False).mean()
    tsi_val = 100 * double_ema / double_abs
    signal_line = tsi_val.ewm(span=signal, adjust=False).mean()

    tv = _latest(tsi_val)
    sv = _latest(signal_line)
    if tv is None or sv is None:
        verdict = "数据不足"
    elif tv > sv and tv > 0:
        verdict = f"TSI={tv:.1f} 在信号线上方（多头动能）"
    elif tv < sv and tv < 0:
        verdict = f"TSI={tv:.1f} 在信号线下方（空头动能）"
    else:
        verdict = "TSI 动能中性"

    return {"tsi": tv, "tsi_signal": sv, "tsi_verdict": verdict}


def awesome_oscillator(df: pd.DataFrame, fast: int = 5, slow: int = 34) -> dict:
    """Awesome Oscillator（动量振荡器）。

    AO = SMA5(中价) - SMA34(中价)，中价=(H+L)/2。看零轴穿越与柱体颜色。
    """
    median = (df["High"] + df["Low"]) / 2
    ao = median.rolling(fast).mean() - median.rolling(slow).mean()
    v = _latest(ao)
    prev = _latest(ao.iloc[:-1])
    if v is None or prev is None:
        verdict = "数据不足"
    elif v > 0 and prev <= 0:
        verdict = "AO 上穿零轴（动量转正）"
    elif v < 0 and prev >= 0:
        verdict = "AO 下穿零轴（动量转负）"
    elif v > 0:
        verdict = "AO 为正（多头动量）"
    else:
        verdict = "AO 为负（空头动量）"
    return {"awesome_oscillator": v, "ao_verdict": verdict}


def ultimate_oscillator(df: pd.DataFrame, s1: int = 7, s2: int = 14, s3: int = 28,
                        w1: float = 4.0, w2: float = 2.0, w3: float = 1.0) -> dict:
    """Ultimate Oscillator（终极振荡器）。

    BP = close - min(low, prevClose)；TR = max(high, prevClose) - min(low, prevClose)；
    三个周期的平均 BP/TR 加权：UO = 100 * (w1*avg1 + w2*avg2 + w3*avg3)/(w1+w2+w3)。
    """
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)

    bp = close - pd.concat([low, prev_close], axis=1).min(axis=1)
    tr = pd.concat([high, prev_close], axis=1).max(axis=1) - pd.concat([low, prev_close], axis=1).min(axis=1)

    def _avg(period: int) -> pd.Series:
        return bp.rolling(period).sum() / tr.rolling(period).sum()

    uo = 100 * (w1 * _avg(s1) + w2 * _avg(s2) + w3 * _avg(s3)) / (w1 + w2 + w3)
    v = _latest(uo)
    if v is None:
        verdict = "数据不足"
    elif v > 70:
        verdict = f"UO={v:.0f}，超买区"
    elif v < 30:
        verdict = f"UO={v:.0f}，超卖区"
    else:
        verdict = f"UO={v:.0f}，中性"
    return {"ultimate_oscillator": v, "uo_verdict": verdict}


def stoch_rsi(df: pd.DataFrame, period: int = 14, smooth1: int = 3, smooth2: int = 3) -> dict:
    """Stochastic RSI（随机 RSI）。

    StochRSI = (RSI - min(RSI,n)) / (max(RSI,n) - min(RSI,n))，再平滑。
    0~1 区间；>0.8 超买，<0.2 超卖。
    """
    close = df["Close"]
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))

    rsi_min = rsi.rolling(period).min()
    rsi_max = rsi.rolling(period).max()
    stoch = ((rsi - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan)).fillna(0.5)
    stoch = stoch.rolling(smooth1).mean().rolling(smooth2).mean()

    v = _latest(stoch)
    if v is None:
        verdict = "数据不足"
    elif v > 0.8:
        verdict = f"StochRSI={v:.2f}，超买"
    elif v < 0.2:
        verdict = f"StochRSI={v:.2f}，超卖"
    else:
        verdict = f"StochRSI={v:.2f}，中性"
    return {"stoch_rsi": v, "stoch_rsi_verdict": verdict}


def williams_r(df: pd.DataFrame, period: int = 14) -> dict:
    """Williams %R（威廉指标）。

    %R = -100 * (max(H,n) - close) / (max(H,n) - min(L,n))。<-80 超卖，>-20 超买。
    """
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    hh = high.rolling(period).max()
    ll = low.rolling(period).min()
    wr = -100 * (hh - close) / (hh - ll).replace(0, np.nan)

    v = _latest(wr)
    if v is None:
        verdict = "数据不足"
    elif v < -80:
        verdict = f"Williams%R={v:.0f}，超卖区"
    elif v > -20:
        verdict = f"Williams%R={v:.0f}，超买区"
    else:
        verdict = f"Williams%R={v:.0f}，中性"
    return {"williams_r": v, "williams_r_verdict": verdict}


def cci(df: pd.DataFrame, period: int = 20, constant: float = 0.015) -> dict:
    """Commodity Channel Index（商品通道指数）。

    TP = (H+L+C)/3；CCI = (TP - SMA(TP,n)) / (0.015 * mean(|TP - SMA(TP,n)|))。
    +100/-100 为超买/超卖参考。
    """
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    sma = tp.rolling(period).mean()
    mad = (tp - sma).abs().rolling(period).mean()
    cci_val = (tp - sma) / (constant * mad.replace(0, np.nan))

    v = _latest(cci_val)
    if v is None:
        verdict = "数据不足"
    elif v > 100:
        verdict = f"CCI={v:.0f}，超买（+100 上方）"
    elif v < -100:
        verdict = f"CCI={v:.0f}，超卖（-100 下方）"
    else:
        verdict = f"CCI={v:.0f}，中性"
    return {"cci": v, "cci_verdict": verdict}


# ---------------------------------------------------------------------------
# 波动类指标
# ---------------------------------------------------------------------------


def atr(df: pd.DataFrame, period: int = 14) -> dict:
    """Average True Range（平均真实波幅）。

    TR = max(H-L, |H-prevC|, |L-prevC|)；ATR = Wilder 平滑（EWM alpha=1/n）。
    """
    high = df["High"]
    low = df["Low"]
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    atr_val = tr.ewm(alpha=1 / period, adjust=False).mean()
    v = _latest(atr_val)
    price = _latest(df["Close"])
    pct = (v / price * 100) if (v is not None and price) else None
    return {
        "atr": v,
        "atr_pct_of_price": pct,
        "atr_verdict": f"ATR={v:.2f}（占价格 {pct:.1f}%）" if pct is not None else "数据不足",
    }


def keltner_channel(df: pd.DataFrame, period: int = 20, atr_period: int = 10, mult: float = 2.0) -> dict:
    """Keltner Channel（肯特纳通道）。

    中轨 = EMA20；上下轨 = 中轨 ± 2*ATR10。与布林带（标准差）相比更贴合波动。
    """
    close = df["Close"]
    ema = close.ewm(span=period, adjust=False).mean()
    high = df["High"]
    low = df["Low"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    atr_val = tr.ewm(alpha=1 / atr_period, adjust=False).mean()
    upper = ema + mult * atr_val
    lower = ema - mult * atr_val

    price = _latest(close)
    up = _latest(upper)
    lo = _latest(lower)
    if price is None or up is None or lo is None:
        verdict = "数据不足"
    elif price > up:
        verdict = "价格突破上轨（强势）"
    elif price < lo:
        verdict = "价格跌破下轨（弱势）"
    else:
        verdict = "价格在通道内（正常波动）"
    return {"keltner_upper": up, "keltner_mid": _latest(ema), "keltner_lower": lo, "keltner_verdict": verdict}


def donchian_channel(df: pd.DataFrame, period: int = 20) -> dict:
    """Donchian Channel（唐奇安通道）。

    上轨 = n 日最高，下轨 = n 日最低，中轨 = 两者均值。突破上下轨为趋势信号。
    """
    high = df["High"]
    low = df["Low"]
    upper = high.rolling(period).max()
    lower = low.rolling(period).min()
    mid = (upper + lower) / 2

    price = _latest(df["Close"])
    up = _latest(upper)
    lo = _latest(lower)
    if price is None or up is None or lo is None:
        verdict = "数据不足"
    elif price >= up:
        verdict = f"价格触及/突破 {period} 日新高（多头突破）"
    elif price <= lo:
        verdict = f"价格触及/跌破 {period} 日新低（空头突破）"
    else:
        verdict = "价格在唐奇安通道内"
    return {"donchian_upper": up, "donchian_mid": _latest(mid), "donchian_lower": lo, "donchian_verdict": verdict}


def ulcer_index(df: pd.DataFrame, period: int = 14) -> dict:
    """Ulcer Index（溃疡指数）— 衡量回撤的持续性。

    UI = sqrt(mean((close/peak - 1)*100)^2)。越大说明回撤越深越久。
    """
    close = df["Close"]
    peak = close.rolling(period, min_periods=1).max()
    drawdown_pct = (close / peak - 1) * 100
    ui = np.sqrt((drawdown_pct**2).rolling(period, min_periods=1).mean())

    v = _latest(ui)
    if v is None:
        verdict = "数据不足"
    elif v > 8:
        verdict = f"UI={v:.1f}，回撤压力大"
    elif v < 3:
        verdict = f"UI={v:.1f}，回撤温和"
    else:
        verdict = f"UI={v:.1f}，回撤中等"
    return {"ulcer_index": v, "ulcer_index_verdict": verdict}


# ---------------------------------------------------------------------------
# 量能类指标
# ---------------------------------------------------------------------------


def obv(df: pd.DataFrame) -> dict:
    """On-Balance Volume（能量潮）。

    收盘涨 → OBV 累加当日量；跌 → 累减；平 → 不变。OBV 斜率与价格背离有信号意义。
    """
    close = df["Close"]
    volume = df["Volume"]
    direction = np.sign(close.diff()).fillna(0)
    obv_val = (direction * volume).cumsum()

    v = _latest(obv_val)
    prev = _shift_latest(obv_val, 5)
    price = _latest(close)
    price_prev = _shift_latest(close, 5)
    if v is None or prev is None or price is None or price_prev is None:
        verdict = "数据不足"
    elif v > prev and price <= price_prev:
        verdict = "OBV 走高而价格走平/跌（量价背离，潜在转强）"
    elif v < prev and price >= price_prev:
        verdict = "OBV 走低而价格走平/涨（量价背离，潜在转弱）"
    elif v > prev:
        verdict = "OBV 上行（量能支持上涨）"
    else:
        verdict = "OBV 下行（量能不支持上涨）"
    return {"obv": v, "obv_verdict": verdict}


def adi(df: pd.DataFrame) -> dict:
    """Accumulation/Distribution Index（累积派发线）。

    MFM = ((C-L)-(H-C))/(H-L)；ADI = cumsum(MFM * Volume)。衡量买卖压力。
    """
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    volume = df["Volume"]
    mfm = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    adi_val = (mfm.fillna(0) * volume).cumsum()

    v = _latest(adi_val)
    prev = _shift_latest(adi_val, 5)
    if v is None or prev is None:
        verdict = "数据不足"
    elif v > prev:
        verdict = "ADI 上行（累积大于派发，买方主导）"
    else:
        verdict = "ADI 下行（派发大于累积，卖方主导）"
    return {"adi": v, "adi_verdict": verdict}


def cmf(df: pd.DataFrame, period: int = 20) -> dict:
    """Chaikin Money Flow（蔡金资金流）。

    CMF = sum(MFM*V, n) / sum(V, n)。>0 资金流入，<0 资金流出。
    """
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    volume = df["Volume"]
    mfm = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    cmf_val = (mfm.fillna(0) * volume).rolling(period).sum() / volume.rolling(period).sum()

    v = _latest(cmf_val)
    if v is None:
        verdict = "数据不足"
    elif v > 0.05:
        verdict = f"CMF={v:.3f}，资金净流入"
    elif v < -0.05:
        verdict = f"CMF={v:.3f}，资金净流出"
    else:
        verdict = f"CMF={v:.3f}，资金流中性"
    return {"cmf": v, "cmf_verdict": verdict}


def mfi(df: pd.DataFrame, period: int = 14) -> dict:
    """Money Flow Index（资金流量指数）。

    TP=(H+L+C)/3；MF = TP*V；正/负资金流比率 → RSI 式归一。>80 超买，<20 超卖。
    """
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    volume = df["Volume"]
    raw_mf = tp * volume
    pos = raw_mf.where(tp > tp.shift(1), 0.0).rolling(period).sum()
    neg = raw_mf.where(tp < tp.shift(1), 0.0).rolling(period).sum()
    ratio = pos / neg.replace(0, np.nan)
    mfi_val = 100 - 100 / (1 + ratio)

    v = _latest(mfi_val)
    if v is None:
        verdict = "数据不足"
    elif v > 80:
        verdict = f"MFI={v:.0f}，超买"
    elif v < 20:
        verdict = f"MFI={v:.0f}，超卖"
    else:
        verdict = f"MFI={v:.0f}，中性"
    return {"mfi": v, "mfi_verdict": verdict}


def force_index(df: pd.DataFrame, period: int = 13) -> dict:
    """Force Index（强力指数）。

    FI = (close - prevClose) * Volume，再 EMA 平滑。正=多方主导，负=空方主导。
    """
    close = df["Close"]
    volume = df["Volume"]
    raw = close.diff() * volume
    fi = raw.ewm(span=period, adjust=False).mean()

    v = _latest(fi)
    if v is None:
        verdict = "数据不足"
    elif v > 0:
        verdict = "强力指数为正（多方力量）"
    else:
        verdict = "强力指数为负（空方力量）"
    return {"force_index": v, "force_index_verdict": verdict}


def eom(df: pd.DataFrame, period: int = 14, div: float = 10000.0) -> dict:
    """Ease of Movement（简易波动指标）。

    DM = (H+L)/2 - (prevH+prevL)/2；BoxRatio = (V/div) / (H-L)；EOM = DM/BoxRatio。
    EOM 与价格同向放大 = 价格容易移动（趋势顺畅）。
    """
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    dm = (high + low) / 2 - (high.shift(1) + low.shift(1)) / 2
    box_ratio = (volume / div) / (high - low).replace(0, np.nan)
    eom_val = (dm / box_ratio).rolling(period).mean()

    v = _latest(eom_val)
    if v is None:
        verdict = "数据不足"
    elif v > 0:
        verdict = "EOM 为正（价格易于上行）"
    else:
        verdict = "EOM 为负（价格易于下行）"
    return {"eom": v, "eom_verdict": verdict}


def vpt(df: pd.DataFrame) -> dict:
    """Volume Price Trend（量价趋势）。

    VPT = cumsum(V * pctChange(close))。趋势向上且 VPT 新高 = 健康。
    """
    close = df["Close"]
    volume = df["Volume"]
    vpt_val = (volume * close.pct_change()).fillna(0).cumsum()

    v = _latest(vpt_val)
    prev = _shift_latest(vpt_val, 5)
    if v is None or prev is None:
        verdict = "数据不足"
    elif v > prev:
        verdict = "VPT 上行（量价配合）"
    else:
        verdict = "VPT 下行（量价背离风险）"
    return {"vpt": v, "vpt_verdict": verdict}


def nvi(df: pd.DataFrame) -> dict:
    """Negative Volume Index（负量指数）。

    量缩日：NVI += pctChange(close)；量增日：NVI 不变。反映聪明钱在缩量日的动向。
    """
    close = df["Close"]
    volume = df["Volume"]
    nvi_val = np.zeros(len(df))
    for i in range(1, len(df)):
        if volume.iloc[i] < volume.iloc[i - 1]:
            nvi_val[i] = nvi_val[i - 1] + close.pct_change().iloc[i]
        else:
            nvi_val[i] = nvi_val[i - 1]
    nvi_series = pd.Series(nvi_val, index=df.index)

    v = _latest(nvi_series)
    prev = _shift_latest(nvi_series, 10)
    if v is None or prev is None:
        verdict = "数据不足"
    elif v > prev:
        verdict = "NVI 上行（缩量日资金悄然进场）"
    else:
        verdict = "NVI 下行（缩量日资金离场）"
    return {"nvi": v, "nvi_verdict": verdict}


def vwap(df: pd.DataFrame) -> dict:
    """Volume-Weighted Average Price（成交量加权平均价，当日累计）。

    VWAP = cumsum(TP*V) / cumsum(V)。价格在 VWAP 上方 = 当日买方均价优势。
    """
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    volume = df["Volume"]
    vwap_val = (tp * volume).cumsum() / volume.cumsum().replace(0, np.nan)

    v = _latest(vwap_val)
    price = _latest(df["Close"])
    if v is None or price is None:
        verdict = "数据不足"
    elif price > v:
        verdict = "价格在 VWAP 上方（买方主导）"
    else:
        verdict = "价格在 VWAP 下方（卖方主导）"
    return {"vwap": v, "vwap_verdict": verdict}


# ---------------------------------------------------------------------------
# 指标注册表 & 统一入口
# ---------------------------------------------------------------------------

# 指标名 → (计算函数, 中文名, 分类)
_INDICATOR_REGISTRY: dict[str, dict] = {
    # 趋势
    "ichimoku": {"fn": ichimoku, "name": "一目均衡表", "category": "trend"},
    "adx": {"fn": adx, "name": "平均趋向指数", "category": "trend"},
    "vortex": {"fn": vortex, "name": "涡旋指标", "category": "trend"},
    "psar": {"fn": psar, "name": "抛物线转向", "category": "trend"},
    "aroon": {"fn": aroon, "name": "阿隆指标", "category": "trend"},
    "stc": {"fn": stc, "name": "STC 趋势周期", "category": "trend"},
    "kst": {"fn": kst, "name": "KST 综合动量", "category": "trend"},
    "dpo": {"fn": dpo, "name": "去趋势价格振荡器", "category": "trend"},
    "trix": {"fn": trix, "name": "三重指数平滑平均", "category": "trend"},
    "mass_index": {"fn": mass_index, "name": "梅斯指数", "category": "trend"},
    # 动量
    "kama": {"fn": kama, "name": "考夫曼自适应均线", "category": "momentum"},
    "ppo": {"fn": ppo, "name": "百分比价格振荡器", "category": "momentum"},
    "pvo": {"fn": pvo, "name": "百分比成交量振荡器", "category": "momentum"},
    "roc": {"fn": roc, "name": "变动率", "category": "momentum"},
    "tsi": {"fn": tsi, "name": "真实强弱指数", "category": "momentum"},
    "awesome_oscillator": {"fn": awesome_oscillator, "name": "动量振荡器", "category": "momentum"},
    "ultimate_oscillator": {"fn": ultimate_oscillator, "name": "终极振荡器", "category": "momentum"},
    "stoch_rsi": {"fn": stoch_rsi, "name": "随机 RSI", "category": "momentum"},
    "williams_r": {"fn": williams_r, "name": "威廉指标", "category": "momentum"},
    "cci": {"fn": cci, "name": "商品通道指数", "category": "momentum"},
    # 波动
    "atr": {"fn": atr, "name": "平均真实波幅", "category": "volatility"},
    "keltner_channel": {"fn": keltner_channel, "name": "肯特纳通道", "category": "volatility"},
    "donchian_channel": {"fn": donchian_channel, "name": "唐奇安通道", "category": "volatility"},
    "ulcer_index": {"fn": ulcer_index, "name": "溃疡指数", "category": "volatility"},
    # 量能
    "obv": {"fn": obv, "name": "能量潮", "category": "volume"},
    "adi": {"fn": adi, "name": "累积派发线", "category": "volume"},
    "cmf": {"fn": cmf, "name": "蔡金资金流", "category": "volume"},
    "mfi": {"fn": mfi, "name": "资金流量指数", "category": "volume"},
    "force_index": {"fn": force_index, "name": "强力指数", "category": "volume"},
    "eom": {"fn": eom, "name": "简易波动指标", "category": "volume"},
    "vpt": {"fn": vpt, "name": "量价趋势", "category": "volume"},
    "nvi": {"fn": nvi, "name": "负量指数", "category": "volume"},
    "vwap": {"fn": vwap, "name": "成交量加权均价", "category": "volume"},
}


def list_advanced_indicators() -> list[str]:
    """返回所有支持的高级指标名。"""
    return sorted(_INDICATOR_REGISTRY.keys())


def compute_advanced_indicators(
    ohlcv: pd.DataFrame,
    indicators: Sequence[str] | None = None,
) -> dict[str, float | str]:
    """计算高级技术指标。

    Args:
        ohlcv: 标准 OHLCV DataFrame（Open/High/Low/Close/Volume 列）。
        indicators: 要计算的指标名列表；None = 计算全部（较慢）。未知名称被忽略并告警。

    Returns:
        {指标字段名: 最新值或解读文本}。数值缺失时值为 None。
    """
    if ohlcv is None or ohlcv.empty:
        return {"error": "No usable OHLCV rows"}
    df = _ensure_numeric(ohlcv)
    if df.empty or df["Close"].dropna().empty:
        return {"error": "No usable OHLCV rows"}

    if indicators is None:
        names = list(_INDICATOR_REGISTRY.keys())
    else:
        names = []
        for ind in indicators:
            key = str(ind).strip().lower()
            if key in _INDICATOR_REGISTRY:
                names.append(key)
            else:
                logger.warning("advanced_indicators: unknown indicator %r; available: %s",
                               ind, ", ".join(list_advanced_indicators()))

    result: dict[str, float | str] = {}
    for name in names:
        try:
            entry = _INDICATOR_REGISTRY[name]
            values = entry["fn"](df)
            for k, v in values.items():
                if isinstance(v, (int, float, np.floating, np.integer)) and not isinstance(v, bool):
                    result[k] = round(float(v), 4) if not np.isnan(float(v)) else None
                elif isinstance(v, str):
                    result[k] = v
                else:
                    result[k] = v
        except Exception as exc:  # noqa: BLE001 — 单指标失败不影响其他指标
            logger.warning("advanced_indicators: %s failed: %s", name, exc)
            result[f"{name}_error"] = f"计算失败: {exc}"

    return result

---
name: volatility-regime
description: High-volatility framework — ATR-based stops, wider bands, mean-reversion discount. The counter to forcing tight levels in a choppy tape.
version: 1.0.0
analyst: market
tags: [technical, volatility, atr, risk, stops]
regimes: [volatile, bearish]
instruments: [equity, etf]
markets: [US, HK, KR, CN]
---

# Volatility-Regime Framework

## When to Apply
The regime is high-volatility (ATR >> norm, Bollinger wide, recent amplitude extreme). Forcing tight MA levels / precise targets here whipsaws. This skill sets ATR-based stops, wider bands, and discounts the mean-reversion signals that work in calm tapes.

## Procedure
1. **Volatility level.** `get_verified_market_snapshot` gives ATR + Bollinger width. ATR/price > 5% = high-vol; > 10% = extreme. Compare Bollinger width to its own norm (`get_stock_data` ~60 days). State the level plainly.
2. **ATR-based stops.** Stops/levels scale with ATR, not round numbers. Reasonable stop = 1.5–2× ATR from entry; a "support" is only credible if within ~1 ATR of a real prior pivot. Round-number levels in high-vol are noise.
3. **Mean-reversion discount.** RSI extremes / Bollinger-tag reversals that work in calm tapes fail in high-vol (price can ride the band). Don't size on mean-reversion in high-vol; if taken, size small + tight invalidation. Use the oversold-bounce skill's base rate, but discount the conviction.
4. **Risk-first sizing.** In high-vol, position shrinks (same $ risk = fewer shares at wider stop). The PM/Trader layers Kelly on top; your job is the ATR-derived stop + volatility level so sizing scales correctly.
5. **Regime-transition watch.** High-vol mean-reverts to calm (volatility is mean-reverting). Watch ATR compressing + Bollinger narrowing = regime transitioning to a tradable trend; until then, stay risk-first.

## Pitfalls
- ATR-based stops are wider → position smaller for same risk; don't quote a big size without scaling for the wider stop.
- A "support" that's just a round number or a thin prior pivot gets sliced through in high-vol — require a real pivot (pattern_discovery / prior lows from `get_stock_data`).
- High-vol ≠ "no trend" — a high-vol downtrend is still a downtrend; risk-first means smaller size + wider stops in the trend direction, not no-view.

## Output
State: (1) volatility level (ATR% + Bollinger width vs norm), (2) ATR-based stop distance + credible support levels (real pivots only), (3) mean-reversion discount (base rate if available, discounted), (4) risk-first sizing hint (wider stop → smaller size), (5) regime-transition watch (ATR compressing?).

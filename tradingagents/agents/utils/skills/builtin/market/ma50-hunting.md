---
name: ma50-hunting
description: Detect institutional MA50 hunting (stop-runs) vs genuine breakdown in high-institutional-ownership names.
version: 1.0.0
analyst: market
tags: [technical, institutional, ma50, stop-hunting]
regimes: [volatile, bearish, downtrend]
instruments: [equity, etf]
markets: [US, HK, KR]
---

# MA50 Hunting Detection

## When to Apply
Price is approaching or testing the 50-day moving average from above, especially in names with high institutional/foreign ownership (semiconductors, large-cap tech). The question: is the MA50 touch a real breakdown or an institutional stop-hunt (a liquidity grab below a key level)?

## Procedure
1. **Locate MA50 + distance.** Call `get_verified_market_snapshot(ticker, date, 30)` — the snapshot includes the 50 SMA. Note the price-vs-MA50 distance. Call `get_stock_data(ticker, start, end)` for ~180 days to see prior MA50 touches.
2. **Volume at the touch.** From `get_stock_data`, compare volume on MA50-touch days vs the 20-day average. Volume >1.5x average at the touch = potential institutional activity (not retail drift).
3. **Foreign / institutional flow (if a foreign-flow block is in your context).** The chip-face block gives foreign-ownership % + consecutive net-sell/buy days. Stable foreign ownership % + a sharp down-touch = domestic/retail panic, NOT institutional exit → hunting pattern more likely. Falling foreign ownership % = real exit, not hunting.
4. **Pattern-discovery block (if present).** The forensics block's anomaly-day + anchor-deviation verdict tells you whether MA50 is the algorithmic anchor (precision evidence). A Low-pivot win at MA50 = a short-hunt read; combine with the volume/flow read above.
5. **Options confirmation — SKIP if no options tool.** There is no `get_options_flow` tool in this build. Skip put/call confirmation; rely on the volume + foreign-flow + pattern-discovery triad. Do not fabricate put/call numbers.
6. **Historical bounce rate.** From the 180-day `get_stock_data`, count prior MA50 touches and how many bounced within 5 days. 3+ prior bounces = strong support; a break below with 2+ daily closes = genuine breakdown, not hunting.

## Pitfalls
- High volume + falling foreign-ownership % = real exit, not hunting — do not call it a stop-run.
- A single daily close below MA50 is inconclusive; need 2+ closes or a clean reclaim.
- MA50 hunting is indistinguishable from a trend breakdown in thin, low-ownership names — this skill assumes institutional ownership.

## Output
State plainly: (1) hunting vs real breakdown, (2) confidence, (3) key evidence (volume multiple, foreign-flow sign, prior bounce rate, pattern-discovery verdict if present).

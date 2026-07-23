---
name: leveraged-etf-decay
description: Frame a leveraged/inverse ETF via underlying path + volatility decay, not company DCF.
version: 1.0.0
analyst: market
tags: [leveraged-etf, decay, path-dependence, volatility]
regimes: [volatile, uptrend, downtrend, sideways]
instruments: [leveraged_etf, inverse_etf]
markets: [US, HK, KR]
---

# Leveraged / Inverse ETF Decay Analysis

## When to Apply
The instrument is a leveraged (2x/3x) or inverse (-1x/-2x/-3x) ETF. These are path-dependent: in a sideways/volatile tape they bleed via daily reset (volatility decay), and the headline index call is NOT the holder's actual exposure.

## Procedure
1. **Underlying path, not point move.** Call `get_stock_data(underlying, start, end)` and `get_stock_data(ticker, start, end)` for ≥60 days. Compare the cumulative underlying return vs the ETF's return over the same window — the gap is the decay/tracking error. A 2x ETF up less than 2× the index over a choppy window = decay in action.
2. **Overnight transmission (if a cross-market block is present).** For a HK-listed leveraged ETF on a US/KR underlying, the overnight block gives the leverage-derived expected open + transmission state. Anchor the next-session view to it, not to the ETF's own close.
3. **Volatility regime.** From the regime context: high-volatility regimes amplify decay (daily reset punishes both-direction chopping). In a clean one-direction trend, decay is small and the ETF behaves close to N× the index.
4. **No fundamentals.** Do NOT analyse a leveraged ETF like a company (no PE / DCF / moat). The `framework_note` in your context already redirects you — honour it. The "fundamentals" are the underlying index's path + the reset math.

## Pitfalls
- Quoting "the index will rise X%, so the ETF rises 2X%" without adjusting for path — wrong over any multi-day horizon in a choppy tape.
- Ignoring FX: an unhedged cross-market leveraged ETF has a hidden currency leg that can dominate.
- Treating a single-day 2× move as representative — decay only shows over multi-day windows.

## Output
State: (1) expected decay magnitude this regime, (2) the underlying path required for the ETF to outperform cash, (3) the next-session open anchor (if overnight block present), (4) confidence.

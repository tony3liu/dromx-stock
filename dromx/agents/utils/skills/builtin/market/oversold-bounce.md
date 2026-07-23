---
name: oversold-bounce
description: Quantify oversold-bounce probability — N-day drawdown vs history + prior-bounce rate. Counters the Regime's blanket "defensive" lean in high-vol downtrends.
version: 1.0.0
analyst: market
tags: [technical, oversold, bounce, mean-reversion]
regimes: [volatile, bearish, downtrend]
instruments: [equity, etf]
markets: [US, HK, KR, CN]
---

# Oversold-Bounce Quantification

## When to Apply
The tape is a high-vol downtrend AND the name has sold off hard over the last few sessions (N-day drawdown well beyond the norm). The Regime node will lean defensive here, but an extreme oversold print has a high mechanical bounce probability — blindly shorting/underweighting at the lows is a common trap. This skill quantifies how oversold, and what happened last time.

## Procedure
1. **N-day drawdown.** Call `get_stock_data(ticker, start, end)` for ~60 trading days. Compute the cumulative return over the last 3 / 5 / 7 / 10 sessions. A 7-day −39% (e.g. GLW 6/29→7/8) is extreme; a 7-day −8% in a high-vol name is routine.
2. **Oversold magnitude vs history.** Over the 60-day window, how does this N-day drawdown compare to the typical N-day drawdown? You don't need a precise z-score — estimate: is this drawdown in the bottom 2–3 of the 60-day window or not? "Bottom 2–3" = extreme oversold (≈ z ≤ −2). State the rank plainly ("worst 7-day drop in the window").
3. **Prior-bounce rate.** Find the prior 2–3 instances of similar-magnitude N-day drawdowns in the 60-day window. For each, check whether the next 5 sessions were positive (a bounce). Report the rate (e.g. "2 of 3 prior extreme-oversold prints bounced within 5 days"). This is the base rate for a mechanical bounce.
4. **Oversold-bounce vs trend-down.** Distinguish:
   - **Oversold-bounce** — sharp drop + prior bounces usually held + price still above long-term support (e.g. 200-SMA) + no fundamental break (earnings/guidance not cut) → short-term bounce probable, frame as a tactical long / flat-not-short.
   - **Trend-down** — grinding decline + fundamental deterioration (earnings cut, guidance reset) + broken long-term support → continue to avoid/short, the drop is not "oversold" it's "right".
   Use `get_verified_market_snapshot` to check the 200-SMA / 50-SMA levels and `get_fundamentals`/the news block to check for a fundamental break.
5. **Reconcile with the Regime.** Even when the Regime says "risk-first, mean-reversion is not a core hold", an extreme-oversold + positive-bounce-base-rate setup shifts the SHORT-term read toward bounce/flat (not short/add-risk). Keep the horizons separate: bounce is a 1–5 day tactical view; the medium-term trend can still be down.

## Pitfalls
- Oversold ≠ must-bounce. A fundamental break (earnings cut, capital raise, delisting risk) overshadows the mechanical bounce — always check the news/fundamentals for a reason.
- A bounce is a SHORT-term mechanical view; do not extend it into a medium-term hold. Say the horizon explicitly.
- With <60 days of history or no prior oversold samples, downgrade to a qualitative call and say so — don't fabricate a base rate.

## Output
State: (1) N-day drawdown + its rank vs 60-day history (or "extreme oversold"), (2) prior-bounce rate (N/M prior extreme-oversolds bounced within 5d), (3) oversold-bounce vs trend-down call, (4) the SHORT-term direction (bounce probability) kept distinct from the medium-term trend.

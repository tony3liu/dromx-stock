---
name: sentiment-contagion
description: Spot cross-asset / cross-market sentiment spillover and distinguish it from idiosyncratic flow.
version: 1.0.0
analyst: sentiment
tags: [sentiment, contagion, cross-asset, risk-appetite]
regimes: [volatile, bearish, uptrend, downtrend]
instruments: [equity, etf]
markets: [US, HK, KR, CN]
---

# Sentiment Contagion Analysis

## When to Apply
A move in one market/asset spills into others — risk-on / risk-off across regions, a US sell-off dragging HK/KR/A-share opens, a crypto-volatility spike hitting risk assets. The question: is your ticker's sentiment move idiosyncratic or contagion, and is the contagion risk-on or risk-off?

## Procedure
1. **Sense the source.** `get_global_news(date, 7, 10)` for the macro sentiment driver (Fed, geopolitical, crypto, oil). `get_news(ticker, start, end)` for the name's own stories. If the global driver dominates and the ticker has no name-specific story, the move is contagion.
2. **Cross-asset read.** The prediction-market block (if present) gives risk-implied probabilities (recession / rate-cut). A recession-probability spike = risk-off contagion; your ticker's sentiment should be read as risk-off driven, not company-driven.
3. **Social channels.** `fetch_stocktwits_messages` / `fetch_reddit_posts` / `fetch_x_posts` (when wired as tools) — if the chatter is about the macro driver, not the company, that confirms contagion. If chatter is name-specific (product, management), it's idiosyncratic.
4. **Direction of contagion.** Risk-on contagion (liquidity-driven) lifts beta names more; risk-off contagion hits high-beta + high-short-interest names harder. Place your ticker's beta vs the market to gauge the expected sentiment over/undershoot.
5. **Decay.** Contagion moves decay as the source stabilises — a sentiment call based purely on contagion should be short-horizon; a name-specific sentiment call can be longer.

## Pitfalls
- Mislabelling contagion as idiosyncratic (or vice versa) — the trade is very different. Always check the global driver first.
- Extending a contagion-driven sentiment call to a multi-month horizon — contagion decays; don't over-horizon it.
- Fabricating social-sentiment numbers — if the social tools are unavailable, say so and rely on news + prediction markets.

## Output
State: (1) contagion vs idiosyncratic, (2) the source driver, (3) risk-on or risk-off, (4) your ticker's expected over/undershoot given beta, (5) horizon (short for contagion), (6) confidence.

---
name: earnings-deviation
description: Frame fundamentals as an expectation gap — market-implied vs your estimate, not absolute quality.
version: 1.0.0
analyst: fundamentals
tags: [earnings, expectation-gap, valuation]
regimes: [volatile, uptrend, downtrend, sideways]
instruments: [equity]
markets: [US, HK, KR]
---

# Earnings / Expectation-Deviation Analysis

## When to Apply
Always, for any name with financial statements — but the edge is the expectation gap, not the absolute quality. A great company at expectations already above yours is a sell; a mediocre one below your estimate is a buy.

## Procedure
1. **Pull the statements.** `get_fundamentals(ticker, date)` for overview (PE/ROE/margins), `get_income_statement(ticker, "quarterly", date)`, `get_balance_sheet(...)`, `get_cashflow(...)` for the trajectory.
2. **Market-implied growth.** From the PE (overview) + the risk-free rate (macro context), infer the growth rate the market is pricing in. A 40x PE with a 4% risk-free implies ~7-8% real perpetual growth (back-of-envelope). State it.
3. **Your estimate.** From the income-statement trajectory (revenue/margin acceleration or deceleration), state your own growth/margin estimate for the next 4-8 quarters.
4. **The gap.** Expected deviation = your estimate − market-implied. Positive gap (you're above) = bullish edge. Negative gap = bearish edge. The magnitude of the gap is the size of the edge.
5. **Earnings-quality check.** From `get_cashflow`: operating cash flow vs net income (OCF/NI < 0.8 = low quality, accruals inflating). A low-quality beat is worth less than a high-quality one.
6. **Peer-relative.** If `peer_tickers` are configured, compare your growth/margin/valuation to peers — a name 30% cheaper than peers on the same growth is a different call than 30% expensive.

## Pitfalls
- Stopping at "good company / bad company" — the edge is the gap, not the level.
- Using a single quarter's beat as the trajectory — look across ≥4 quarters for the trend.
- Fabricating a whisper number — if you don't have consensus, say so and use the PE-implied growth as the benchmark.

## Output
State: (1) market-implied growth/margin, (2) your estimate, (3) the gap (signed), (4) earnings quality (OCF/NI), (5) peer-relative, (6) direction + confidence.

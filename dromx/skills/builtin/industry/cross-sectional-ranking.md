---
name: cross-sectional-ranking
description: Rank this name vs configured peers on relative momentum/earnings/valuation/flow/event-risk. Single-name bullish ≠ worth holding.
version: 1.0.0
analyst: industry
tags: [cross-sectional, relative, ranking, peers]
regimes: [volatile, bearish, uptrend, downtrend]
instruments: [equity, etf]
markets: [US, HK, KR, CN]
---

# Cross-Sectional Relative Ranking

## When to Apply
Configured peers exist (`peer_tickers`) OR you can name 2-3 same-sector/same-risk names. Single-name "bullish" doesn't mean "hold this one" — the portfolio question is whether it beats its peers on a relative basis. This skill ranks the name vs peers on 5 axes and gives a composite.

## Procedure
1. **Name the peer set.** From `peer_tickers` (configured) + your knowledge, 2-3 same-sector/same-risk names. Tag `[data]` (configured) / `[knowledge]`.
2. **Relative momentum (30%).** `get_stock_data(peer, start, end)` for each peer + the name. Compare recent returns (1M/3M). Is the name leading or lagging the cohort?
3. **Relative earnings revision (25%).** `get_fundamentals(peer, date)` for each. Compare revenue/EPS trajectory + any recent revision. Is the name's earnings being upgraded more or less than peers?
4. **Relative valuation (20%).** Compare PE / EV-EBITDA (from fundamentals) across the set. Is the name cheap or expensive vs peers (not vs its own history)?
5. **Relative flow/activity (15%).** Volume + (if available) institutional/foreign flow. Is the name seeing more or less flow than peers?
6. **Event-risk adjustment (10%).** Any name-specific event risk (litigation, capital raise, regulatory) that peers don't have? Adjust the score down for idiosyncratic risk.
7. **Composite.** Weighted score (30/25/20/15/10). Rank the name in the set: "Name ranks 2/4 on momentum, 1/4 on earnings revision …" → composite rank.

## Pitfalls
- No configured peers + can't name a credible set → say "no peer set, single-name analysis only", don't fabricate peers.
- Relative scores are `[knowledge]`-heavy when data is thin — tag, and downgrade confidence.
- A name can be #1 on momentum but #4 on valuation — the composite, not any single axis, decides.

## Output
State: (1) the peer set (tagged), (2) per-axis relative ranks (momentum / earnings / valuation / flow / event-risk), (3) composite weighted rank, (4) "is this name the best in the set?" yes/no + why.

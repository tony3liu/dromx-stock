---
name: sector-overnight-flow
description: Sector overnight / recent co-moves — pull peer & supply-chain returns to read sector momentum, the lead signal for "next session up/down".
version: 1.0.0
analyst: [market, industry]
tags: [sector, flow, overnight, correlation, lead-signal]
regimes: [volatile, bearish, uptrend, downtrend]
instruments: [equity, etf]
markets: [US, HK, KR, CN]
---

# Sector Overnight / Recent Co-Move

## When to Apply
The name has a strong sector / supply-chain linkage (upstream/downstream/peer cohort) and you need the NEXT-session direction, not just where it has been. Overnight and same-sector recent moves are a lead signal: overnight Asia semis up → US AI-hardware up → the name (a fibre/upstream play) likely up. Single-name analysis misses this transmission. This skill uses the existing `get_stock_data` tool to pull peer/linked returns and read sector momentum — no special pre-market data feed required.

## Procedure
1. **Name the linked cohort.** From the configured `peer_tickers` (if any) plus your knowledge, list 2–3 (NOT more — each is a tool call) names that move with this one: same sector, upstream/downstream, or the overnight lead market. For a US fibre/AI-hardware upstream name (e.g. GLW), the cohort is MU/NVDA/AMD (US AI-hardware) and 000660.KS / the Korea semis (overnight Asia lead). Tag each `[data]` (from peer_tickers) or `[knowledge]`.
2. **Pull recent returns.** Call `get_stock_data(linked, start, end)` for each of the 2–3 cohort names, ~1–5 sessions. The most-recent session's close-vs-prior-close is the overnight / latest-direction proxy (precise pre-market futures aren't in this build — say so and use the daily proxy).
3. **Sector momentum.** Average the cohort's recent returns. Positive + broad (most of the cohort up) = sector momentum up; negative + broad = down. One name moving alone is idiosyncratic, not sector.
4. **Linkage strength.** Roughly: does this name usually move with the cohort (same-direction frequency)? Strong linkage + sector up → the next-session signal is credible; weak linkage → downgrade.
5. **Transmission path.** State the chain explicitly: "overnight Asia semis (000660.KS) +X% → US AI-hardware open bid → this name (upstream fibre) likely follows". A clear path makes the signal credible; a vague "sector is up" is weak.

## Pitfalls
- Sector up does NOT force this name up — idiosyncratic risk (earnings, litigation, a company-specific news item) can decouple it. Check the news block for a name-specific overhang before leaning on the sector signal.
- The cohort is partly `[knowledge]`-tagged and may be wrong; prefer configured `peer_tickers` where they exist.
- "Overnight" here is a daily-close proxy, not precise pre-market/after-hours/futures. State the limitation; don't claim a pre-market print you don't have.

## Output
State: (1) the cohort (each tagged [data]/[knowledge]) + their recent returns, (2) sector momentum (sign + breadth + strength), (3) the transmission path, (4) the next-session read for THIS name given its linkage (likely-follows / decoupled / unclear).

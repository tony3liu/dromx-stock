---
name: korea-cross-market
description: Trace US-overnight -> underlying -> Korea/HK listing-open transmission for cross-market names.
version: 1.0.0
analyst: [news, market]
tags: [cross-market, korea, overnight, transmission]
regimes: [volatile, uptrend, downtrend]
instruments: [equity, leveraged_etf, etf]
markets: [HK, KR, US]
---

# Korea / Cross-Market Transmission

## When to Apply
The listing market differs from the underlying's primary market — e.g. a HK-listed Korea-semis ETF, a US ADR of a Korea/HK name, or a KR listing reacting to US-overnight futures. The overnight-transmission block in your context already computed the chain; this skill interprets it.

## Procedure
1. **Read the overnight-transmission block.** It gives: the underlying overnight return, the leverage-derived expected open, and the transmission state (intact / broken). Anchor the next-session view to the expected open, not to the listing's own close.
2. **Confirm with news.** `get_global_news(date, 7, 10)` for the overnight macro that drove the underlying. `get_news(ticker, start, end)` for name-specific overnight stories. If the underlying moved on a sector/macro story (not name-specific), the listing's open should follow the index, not a name catalyst.
3. **Transmission-break detection.** If the listing opens materially off the expected-open (the block flags "broken"), that is itself a signal: local forces (local flow, local news, local regulation) are overriding the cross-market lead. Investigate local `get_news` for the divergence cause.
4. **Foreign-flow block (Korea listings).** If the listing is .KS, the foreign-flow block gives foreign-ownership % + net trading — foreign behaviour is the transmission channel in Korea. Foreign net-sell into a US-overnight up tape = local distribution overriding the lead.

## Pitfalls
- Not every cross-market listing has a transmission chain — if the block is empty (same-market ETF, or the LLM judged "no link"), do not fabricate one. State "no cross-market transmission detected".
- The expected-open is a leverage-derived anchor, not a prediction — the actual open can deviate on local order flow.
- US futures ≠ US cash market — the overnight block uses the underlying's actual session, not futures.

## Output
State: (1) overnight lead + expected open, (2) transmission intact/broken, (3) if broken, the local cause, (4) foreign-flow alignment (if .KS), (5) next-session read anchored to the expected open.

---
name: event-chain-tracing
description: Trace a single news event through its chain of downstream effects across companies/sectors.
version: 1.0.0
analyst: news
tags: [event-chain, causality, downstream]
regimes: [volatile, bearish, uptrend, downtrend, sideways]
instruments: [equity, etf]
markets: [US, HK, KR]
---

# Event-Chain Tracing

## When to Apply
A single headline carries implications beyond the named company — e.g. "Company X wins big AI chip order" → affects X's supplier chain, X's competitors, the customer, the substrate/material suppliers. The task: trace the chain so the thesis reflects second-order effects, not just the headline.

## Procedure
1. **Name the catalyst + date.** From `get_news(ticker, start, end)`, identify the triggering event and its date. State it as "Event X on date Y".
2. **Upstream / downstream map.** From `get_news` + your knowledge: who supplies the named company? who competes? who is the customer? List each as a node. Use `[knowledge]` tags for relationships not grounded in the fetched news.
3. **Confirm each node with news.** For each downstream name you claim is affected, check `get_news(that_name, start, end)` for corroboration. If no corroborating story, downgrade that node to "speculative" — do not present it as confirmed.
4. **Time-order the chain.** Effects ripple: first-order (direct counterparties) → second-order (their suppliers) → third-order (substitution). State which order your ticker sits at.
5. **Quantify exposure.** Use `get_fundamentals(ticker, date)` for segment revenue — what % of the ticker's revenue touches the event? A 5% segment exposure is a different call from 60%.

## Pitfalls
- Presenting a speculative downstream node as confirmed — every node needs a news citation or a `[knowledge]` tag.
- Over-tracing: beyond 3rd order the signal is noise; stop.
- Ignoring lags: supply-chain effects land quarters later; do not price them in immediately.

## Output
State: (1) the catalyst + date, (2) the chain (ordered, each node cited or tagged speculative), (3) your ticker's position in the chain, (4) revenue exposure %, (5) net read for your ticker.

---
name: expectation-gap
description: Frame news as expectation gap — known fact vs market expectation vs surprise (up/inline/down). Not "good news = bullish".
version: 1.0.0
analyst: news
tags: [expectation-gap, surprise, consensus]
regimes: [volatile, bearish, uptrend, downtrend, sideways]
instruments: [equity, etf]
markets: [US, HK, KR, CN]
---

# Expectation-Gap Analysis

## When to Apply
Always — this is the core news-analysis frame. Stocks move on surprise vs expectation, not on the headline direction. "Good news" that's already priced in is neutral; "bad news" that's worse than feared can be bullish (relief). Force the expectation-gap frame on every material item.

## Procedure
1. **Known fact.** From `get_news(ticker, start, end)` + `get_global_news`, state the concrete fact/event + date. What actually happened?
2. **Market expectation.** What was the market/consensus expecting before this? (whisper number, consensus revenue/EPS, prior guidance, the priced-in scenario). If you have consensus data, state it. If not — say "no reliable consensus data available" and tag the gap judgment as directional-only.
3. **Surprise direction.** Is the new information above (upward revision), in-line, or below (downward revision) the expectation? The surprise, not the headline, is what moves price.
4. **Priced-in vs fresh.** Even a positive surprise may be priced in if the market front-ran it (price ran ahead of the news). Judge whether the surprise is already discounted or fresh.
5. **Honest gap.** If no consensus: "No reliable consensus data — judging event direction only, cannot determine if it's an expectation gap." Don't fabricate a whisper number.

## Pitfalls
- "Good news = bullish" is the trap. Price-up on good news that was already expected is NOT bullish (priced in, maybe sell-the-news).
- Fabricating a consensus/whisper when you don't have one — say "no consensus data" instead.
- A surprise fades if the market front-ran it — check the price action before the news.

## Output
State: (1) the known fact + date, (2) market expectation (or "no consensus data"), (3) surprise direction (up/inline/down), (4) priced-in vs fresh, (5) the expectation-gap read (bullish/bearish/neutral ON THE GAP, not the headline).

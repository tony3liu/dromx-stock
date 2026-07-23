---
name: event-update-check
description: When the report cites a pending event (IPO pricing / filing / decision) as the pivot, actively search whether it has ALREADY landed before concluding "wait for X". Don't rely on stale "pending".
version: 1.0.0
analyst: [news, industry]
tags: [event, update, search, pending, ipo, stale]
regimes: [volatile, bearish, uptrend, downtrend, sideways]
instruments: [equity, etf]
markets: [US, HK, KR, CN]
---

# Event-Update Check (don't conclude "wait for X" without searching)

## When to Apply
The analysis surfaces a PENDING event as the pivot — "wait for CXMT IPO pricing", "wait for the Fed decision", "wait for Q2 earnings". Before making "wait" the conclusion, ACTIVELY search whether the event has ALREADY happened (pricing landed, decision released, earnings printed). A stale "pending" when the event resolved yesterday is a worse call than an honest "I don't know" — it tells the desk to wait for something that's already here. This is the single most common reason an analysis feels "behind".

## Procedure
1. **Identify the pending event.** Name it + its expected date (from the news block / your knowledge). E.g. "CXMT IPO pricing — expected mid-July".
2. **Search the news for the update.** Call `get_news(ticker, start, end)` with a window covering the expected date through today. Call `get_global_news(date, 7, 10)` with the same window — an IPO pricing / macro decision often lands as a GLOBAL headline, not a ticker one. Search both.
3. **If the news block is silent, SEARCH.** Call `web_search(query)` (serper.dev — real Google results, no CAPTCHA) with a query like "<event name> <date> 定价 / 落地 / 公布" to find whether it landed. Pick the best result URL from the titles+snippets, then `web_read(url)` for the full text. `web_search` searches the web (unlike `web_read` which only reads a URL you already have) — use it when get_news/get_global_news don't carry the event.
4. **Update the conclusion.** If the event HAS landed: fold the actual outcome (pricing level, decision, beat/miss) into the read — "wait for X" becomes "X landed at $Y, [above/below] expectation → [bullish/bearish]". If it genuinely hasn't: "still pending as of [today], no update found after searching" — don't fabricate a landing.
5. **Honest miss.** If you searched (get_news + get_global_news + web_read) and found nothing, say "event still pending / no update found as of the search" — and THEN "wait" is honest. Do NOT conclude "wait" as if you never looked.

## Pitfalls
- Concluding "wait for X" WITHOUT searching whether X already happened — the error this skill exists to fix. If a run looks "behind", it's usually this.
- web_read needs a URL; if you have none, say so and rely on get_news/get_global_news — don't fabricate.
- The event may be in GLOBAL news, not ticker news (an IPO pricing / rate decision is a macro headline) — search both, not just the ticker.
- The pending event is the PIVOT of the call — if you don't check it, the whole rating rests on stale info.

## Output
State: (1) the pending event + expected date, (2) what get_news / get_global_news / web_read returned about it, (3) LANDED or STILL-PENDING, (4) if landed: the actual outcome + how it changes the read, (5) "no update found after searching" if you looked and found nothing (THEN "wait" is honest).

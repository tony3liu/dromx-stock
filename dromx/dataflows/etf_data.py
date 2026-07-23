"""ETF passthrough: see through an ETF wrapper to what actually drives it.

Given ANY ticker, the system auto-detects whether it is an ETF and, if so, what
it really exposes the holder to — with ZERO hardcoded per-ticker mappings:

1. **Structure** — ``resolve_etf_structure`` reads the fund's name (Tencent quote,
   whose names carry strong clues, e.g. "XL二南方海力士" = 2x SK Hynix,
   "半导体ETF三倍做多" = 3x semis long) plus yfinance fund fields, and an LLM
   parses them into {is_etf, leverage, direction, underlying, currencies}. No
   per-ticker table — it generalises to any market / language.
2. **Leverage decay** — a 2x/3x daily-reset product compounds negatively in chop;
   flagged automatically once leverage > 1.
3. **FX impact** — a fund listed in one currency tracking a market in another
   (e.g. an HK-listed Korea fund) carries the underlying currency's move on top.
4. **Tracking** — ETF vs underlying-proxy returns when a proxy can be located.

Fully degrading: anything that can't be fetched/parsed is omitted, and a non-ETF
yields an empty block so the analyst prompt is unchanged.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _safe(fn, default=None):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 — ETF context is best-effort, never abort
        logger.debug("ETF passthrough: %s", exc)
        return default


def _returns(symbol: str, curr_date: str, lookback: int = 60):
    """Daily close-to-close returns for ``symbol`` over the last ``lookback`` rows.

    Returns a pandas Series indexed by date, or None on any failure.
    """
    from tradingagents.dataflows.stockstats_utils import load_ohlcv

    df = load_ohlcv(symbol, curr_date)
    if df is None or df.empty or "Close" not in df.columns:
        return None
    import pandas as pd

    s = df.copy()
    s["Date"] = pd.to_datetime(s["Date"], errors="coerce")
    s = s.dropna(subset=["Date"]).sort_values("Date").set_index("Date")["Close"]
    s = s[s.index <= pd.to_datetime(curr_date)].tail(lookback + 1)
    rets = s.pct_change().dropna()
    return rets if len(rets) >= 5 else None


def _quote_currency(ticker: str) -> str | None:
    """ETF listing currency, derived deterministically from its market.

    Uses Tencent's market classifier (cn/hk/us) — far more reliable than scraping
    a currency token out of a live quote — and maps to the listing currency.
    Returns None for markets we don't map.
    """
    def fetch():
        from tradingagents.dataflows.tencent import _classify

        market, _code = _classify(ticker)
        return {"us": "USD", "hk": "HKD", "cn": "CNY"}.get(market)

    return _safe(fetch)


def _tencent_name(ticker: str) -> str | None:
    """Fund/stock display name from a Tencent quote."""
    def fetch():
        import requests

        from tradingagents.dataflows.tencent import _tencent_code

        code, _market = _tencent_code(ticker)
        r = requests.get(
            f"https://qt.gtimg.cn/q={code}", timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        r.encoding = "gbk"
        body = r.text.split('"', 2)[1] if '"' in r.text else ""
        fields = body.split("~")
        return fields[1] if len(fields) > 1 and fields[1] else None

    return _safe(fetch)


def _sina_name(ticker: str) -> str | None:
    """Fund/stock display name from Sina — a second source for resilience.

    Uses the SUFFIX-STRIPPED bare code (07709.HK -> rt_hk07709, NVDA -> gb_nvda,
    510300.SS -> sh510300), which is what reaches the name even when the Tencent
    endpoint is throttled. Names carry the key clues (e.g. 'ＸＬ二南方海力士' = 2x
    SK Hynix, '半导体ETF...三倍做多' = 3x semis long)."""
    def fetch():
        import re

        import requests

        from tradingagents.dataflows.tencent import _classify

        market, _code = _classify(ticker)
        base = ticker.strip().upper().split(".")[0]
        if market == "hk":
            key = "rt_hk" + base.zfill(5)
        elif market == "us":
            key = "gb_" + base.lower()
        elif market == "cn":
            key = ("sh" if base.startswith(("6", "5", "9")) else "sz") + base
        else:
            return None
        r = requests.get(
            f"https://hq.sinajs.cn/list={key}", timeout=8,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"},
        )
        r.encoding = "gbk"
        if '"' not in r.text:
            return None
        parts = r.text.split('"')[1].split(",")
        # HK rt_ feed: parts[0] is the english code, parts[1] the chinese name.
        # US gb_ / CN sh|sz feeds: parts[0] is the name.
        name = parts[1] if (market == "hk" and len(parts) > 1) else (parts[0] if parts else None)
        return name or None

    return _safe(fetch)


def _fund_name(ticker: str) -> str | None:
    """Best-available display name across sources (Tencent → Sina fallback)."""
    return _tencent_name(ticker) or _sina_name(ticker)


def _yf_fund_fields(ticker: str) -> dict:
    """yfinance identity fields useful for ETF structure (best-effort, may be {})."""
    def fetch():
        import yfinance as yf

        from tradingagents.dataflows.symbol_utils import normalize_symbol

        info = yf.Ticker(normalize_symbol(ticker)).info or {}
        return {
            k: info.get(k) for k in (
                "quoteType", "longName", "shortName", "fundFamily", "category",
            ) if info.get(k)
        }

    return _safe(fetch, default={}) or {}


# Inline structured schema for the LLM parser — kept here (not schemas.py) so the
# dataflow stays self-contained.
class ETFStructure:
    """Plain container for the resolved ETF passthrough structure."""

    def __init__(self, *, is_etf=False, leverage=1.0, direction="long",
                 underlying_name=None, underlying_proxy=None, underlying_market=None,
                 listing_currency=None, underlying_currency=None, confidence="low",
                 notes=""):
        self.is_etf = is_etf
        self.leverage = leverage
        self.direction = direction            # "long" | "inverse"
        self.underlying_name = underlying_name
        self.underlying_proxy = underlying_proxy  # a ticker/index symbol if known
        self.underlying_market = underlying_market
        self.listing_currency = listing_currency
        self.underlying_currency = underlying_currency
        self.confidence = confidence
        self.notes = notes

    def instrument_type(self) -> str:
        """Coarse instrument-type label that selects the analysis FRAMEWORK.

        'leveraged_etf' / 'inverse_etf' / 'etf' / 'equity'. (ADR detection would
        slot in here too once a reliable signal exists; for now ADRs are treated
        as equity unless flagged as a fund.)
        """
        if not self.is_etf:
            return "equity"
        if self.direction == "inverse":
            return "inverse_etf"
        if self.leverage and self.leverage > 1.0:
            return "leveraged_etf"
        return "etf"

    def framework_note(self) -> str:
        """A one-block instruction telling downstream agents how to FRAME this
        instrument — so a fund wrapper is never analysed as if it were a company.
        Empty for a plain equity (default framework applies)."""
        t = self.instrument_type()
        if t == "equity":
            return ""
        lev = self.leverage or 1.0
        und = self.underlying_name or "its underlying"
        lines = [
            f"## Instrument type: {t.replace('_', ' ').upper()} — analyse it as a "
            f"FUND WRAPPER, not a company.",
            f"- It tracks **{und}**" + (f" at **{lev:g}x** ({self.direction})." if lev != 1.0 else "."),
            "- Do NOT run company DCF / PE / three-statement valuation on the wrapper "
            "itself — it has no independent fundamentals. Analyse the UNDERLYING's "
            "direction and drivers instead.",
            f"- Any price target must be derived as: underlying move × {lev:g} × "
            "tracking-efficiency haircut — NOT a company valuation.",
        ]
        if lev and lev > 1.0:
            lines.append(
                "- Flag leverage decay: a daily-reset leveraged product compounds "
                "negatively in choppy tapes; multi-week holds can lag the leverage "
                "multiple badly even if the underlying ends flat."
            )
        if (self.listing_currency and self.underlying_currency
                and self.listing_currency.upper() != self.underlying_currency.upper()):
            lines.append(
                f"- FX exposure: listed in {self.listing_currency} but underlying "
                f"trades in {self.underlying_currency} — an unhedged currency leg "
                "rides on top of the underlying move."
            )
        return "\n".join(lines)


def resolve_etf_structure(ticker: str, curr_date: str, llm=None) -> ETFStructure:
    """Auto-detect whether ``ticker`` is an ETF and parse its passthrough structure.

    Zero hardcoded per-ticker mappings: feeds the fund name (Tencent) + yfinance
    fund fields to an LLM, which returns the structure generically. Falls back to
    a deterministic best-effort (yfinance quoteType + listing currency) when no
    LLM is supplied or the LLM call fails. Always returns an ETFStructure; for a
    plain stock it has ``is_etf=False`` and the caller emits nothing.
    """
    name = _fund_name(ticker)
    yf_fields = _yf_fund_fields(ticker)
    listing_ccy = _quote_currency(ticker)

    # Deterministic prior: yfinance quoteType is the most reliable is-ETF signal.
    quote_type = str(yf_fields.get("quoteType", "")).upper()
    det_is_etf = quote_type in ("ETF", "MUTUALFUND")

    if llm is None:
        return ETFStructure(
            is_etf=det_is_etf, leverage=1.0, direction="long",
            underlying_name=yf_fields.get("longName") or name,
            listing_currency=listing_ccy, confidence="low",
            notes="deterministic fallback (no LLM)",
        )

    name_block = name or "(unavailable)"
    yf_block = "\n".join(f"  {k}: {v}" for k, v in yf_fields.items()) or "  (unavailable)"
    prompt = f"""You are an ETF/fund structure classifier. Given a ticker and the metadata fetched for it, decide whether it is a fund/ETF wrapper and, if so, what it really exposes the holder to. Use the fund NAME's clues (e.g. "三倍/3x/daily" = leverage, "二/2x", "做空/inverse", a company or index name = the underlying). Do NOT rely on any memorized per-ticker table; reason from the metadata.

Ticker: {ticker}
Tencent display name: {name_block}
yfinance fields:
{yf_block}

Return JSON only:
{{
  "is_etf": true/false,
  "leverage": 1.0,            // 1.0 normal, 2.0 = 2x, 3.0 = 3x, etc.
  "direction": "long"|"inverse",
  "underlying_name": "what it tracks, e.g. 'SK Hynix', 'KOSPI 200' or null",
  "underlying_proxy": "a ticker/index symbol for the underlying if obvious, else null",
  "underlying_market": "the market the underlying trades in, e.g. 'Korea', 'US' or null",
  "listing_currency": "{listing_ccy or 'null'}",
  "underlying_currency": "ISO currency of the underlying market, e.g. 'KRW', or null",
  "confidence": "low"|"medium"|"high"
}}
If it is plainly an ordinary single stock, set is_etf=false and leave the rest null/defaults."""

    def call():
        import json
        import re

        resp = llm.invoke(prompt)
        txt = getattr(resp, "content", str(resp))
        m = re.search(r"\{.*\}", txt, re.DOTALL)
        if not m:
            raise ValueError("no JSON in LLM response")
        d = json.loads(m.group(0))
        return ETFStructure(
            is_etf=bool(d.get("is_etf")),
            leverage=float(d.get("leverage") or 1.0),
            direction=str(d.get("direction") or "long"),
            underlying_name=d.get("underlying_name"),
            underlying_proxy=d.get("underlying_proxy"),
            underlying_market=d.get("underlying_market"),
            listing_currency=d.get("listing_currency") or listing_ccy,
            underlying_currency=d.get("underlying_currency"),
            confidence=str(d.get("confidence") or "low"),
            notes=f"name={name_block}",
        )

    result = _safe(call)
    if result is None:
        # LLM failed — deterministic fallback so we never abort.
        return ETFStructure(
            is_etf=det_is_etf, leverage=1.0, direction="long",
            underlying_name=yf_fields.get("longName") or name,
            listing_currency=listing_ccy, confidence="low",
            notes="deterministic fallback (LLM error)",
        )
    return result


def build_etf_passthrough(ticker: str, curr_date: str, *, structure: ETFStructure | None = None,
                          underlying: str | None = None,
                          underlying_currency: str | None = None) -> str:
    """Render an ETF passthrough block, or '' when this isn't an ETF / nothing useful.

    Preferred path: pass a resolved ``structure`` (from ``resolve_etf_structure``)
    — leverage decay, FX exposure, and tracking are all driven from it, with no
    per-ticker config. The legacy ``underlying`` / ``underlying_currency`` args
    are an optional manual override (config ``etf_underlying_map``) and are folded
    into the structure when given.
    """
    structure = structure or ETFStructure(is_etf=bool(underlying), confidence="low")
    # Manual override (config map) fills gaps in / overrides the auto structure.
    if underlying:
        structure.underlying_proxy = underlying
        structure.is_etf = True
    if underlying_currency:
        structure.underlying_currency = underlying_currency

    if not structure.is_etf:
        return ""

    lines: list[str] = []

    # Identity line: leverage + direction + underlying.
    lev = structure.leverage or 1.0
    desc_bits = []
    if lev and lev != 1.0:
        desc_bits.append(f"{lev:g}x {structure.direction}")
    if structure.underlying_name:
        desc_bits.append(f"tracking {structure.underlying_name}")
    if desc_bits:
        suffix = f" (confidence: {structure.confidence})" if structure.confidence else ""
        lines.append(f"- **Structure:** {' · '.join(desc_bits)}{suffix}.")

    # Leverage decay — the single most important warning for a daily-reset product.
    if lev and lev > 1.0:
        lines.append(
            f"- ⚠️ **Leverage decay:** a {lev:g}x DAILY-reset product compounds "
            f"negatively in choppy/volatile tapes — over weeks it can lag {lev:g}× "
            f"the underlying badly even if the underlying ends flat. Built for "
            f"short holds, not buy-and-hold; size and time accordingly."
        )

    # Tracking vs an underlying proxy, when we have a fetchable symbol.
    proxy = structure.underlying_proxy
    if proxy:
        etf_rets = _safe(lambda: _returns(ticker, curr_date))
        und_rets = _safe(lambda: _returns(proxy, curr_date))
        if etf_rets is not None and und_rets is not None:
            import pandas as pd

            joined = pd.concat(
                [etf_rets.rename("etf"), und_rets.rename("und")],
                axis=1, join="inner",
            ).dropna()
            if len(joined) >= 5:
                diff = joined["etf"] - joined["und"]
                te = float(diff.std() * (252 ** 0.5)) * 100
                cum_etf = float((1 + joined["etf"]).prod() - 1) * 100
                cum_und = float((1 + joined["und"]).prod() - 1) * 100
                corr = float(joined["etf"].corr(joined["und"]))
                lines.append(
                    f"- **Tracking vs {proxy}** (last {len(joined)}d): tracking "
                    f"error ≈ {te:.1f}% annualised, correlation {corr:.2f}. "
                    f"Cumulative: ETF {cum_etf:+.1f}% vs underlying {cum_und:+.1f}% "
                    f"(drift {cum_etf - cum_und:+.1f} pts)."
                )

    # FX exposure: listed in one currency, underlying trades in another.
    lc, uc = structure.listing_currency, structure.underlying_currency
    if lc and uc and lc.upper() != uc.upper():
        lines.append(
            f"- **FX exposure:** listed in {lc} but the underlying trades in {uc}. "
            f"Your real return = underlying move + {uc}/{lc} move — an unhedged "
            f"currency bet rides on top of the index/stock call."
        )
    elif lc:
        lines.append(f"- Listing currency: {lc}.")

    if not lines:
        return ""
    return (
        "\n## ETF passthrough (you are analysing a fund wrapper — see through it "
        "to the real exposure)\n" + "\n".join(lines) + "\n"
    )

import functools
import logging
from collections.abc import Mapping
from typing import Any

import yfinance as yf
from langchain_core.messages import HumanMessage, RemoveMessage

# Import tools from separate utility files
from dromx.agents.utils.core_stock_tools import get_stock_data
from dromx.agents.utils.fundamental_data_tools import (
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
)
from dromx.agents.utils.macro_data_tools import get_macro_indicators
from dromx.agents.utils.market_data_validation_tools import get_verified_market_snapshot
from dromx.agents.utils.news_data_tools import (
    get_global_news,
    get_insider_transactions,
    get_news,
)
from dromx.agents.utils.prediction_markets_tools import get_prediction_markets
from dromx.agents.utils.technical_indicators_tools import get_indicators

# Public surface: the data tools are imported here so agents and the graph
# import them from one place, plus the instrument/language helpers defined below.
__all__ = [
    "get_stock_data",
    "get_indicators",
    "get_fundamentals",
    "get_balance_sheet",
    "get_cashflow",
    "get_income_statement",
    "get_news",
    "get_global_news",
    "get_insider_transactions",
    "get_macro_indicators",
    "get_prediction_markets",
    "get_verified_market_snapshot",
    "build_instrument_context",
    "resolve_instrument_identity",
    "get_instrument_context_from_state",
    "get_language_instruction",
    "create_msg_delete",
]

logger = logging.getLogger(__name__)


def get_language_instruction() -> str:
    """Return a prompt instruction for the configured output language.

    Returns empty string when English (default), so no extra tokens are used.
    Applied to every agent whose output reaches the saved report —
    analysts, researchers, debaters, research manager, trader, and
    portfolio manager — so a non-English run produces a fully localized
    report rather than a mix of languages.
    """
    from dromx.dataflows.config import get_config
    lang = get_config().get("output_language", "English")
    if lang.strip().lower() == "english":
        return ""
    return f" Write your entire response in {lang}."


def _clean_identity_value(value: Any) -> str | None:
    """Return a trimmed string, or None for empty / placeholder-ish values."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned or cleaned.lower() in {"none", "n/a", "nan", "null"}:
        return None
    return cleaned


def _resolve_cn_identity(ticker: str) -> dict:
    """A-share identity via eastmoney push2 (yfinance often rate-limits A-shares).

    Returns {company_name, sector, industry} for a 6-digit A-share code
    (603986 -> 兆易创新, 半导体). Empty {} for non-A-share / failure. This
    fixes the 603986=北京君正 hallucination: yfinance returned {} (rate-limited),
    the LLM guessed the wrong company.
    """
    import re

    s = ticker.strip().upper()
    m = re.match(r"^(\d{6})(?:\.(SS|SZ))?$", s)
    if not m:
        return {}
    code, suf = m.group(1), m.group(2)
    # market: sh=沪市(60/68/90), sz=深市(00/30/20)
    market = "sh" if (suf == "SS" or code.startswith(("60", "68", "90"))) else "sz"
    # eastmoney push2 rejects python-requests TLS (RemoteDisconnected); tencent
    # qt.gtimg.cn accepts requests and returns the name (GBK). Format:
    # v_sh603986="1~兆易创新~603986~514.61~..."  (parts[1] = company name).
    try:
        import requests

        resp = requests.get(
            f"https://qt.gtimg.cn/q={market}{code}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        text = resp.content.decode("gbk", errors="ignore")
        parts = text.split("~")
        if len(parts) <= 1 or not parts[1]:
            return {}
        return {"company_name": parts[1]}
    except Exception as exc:  # noqa: BLE001 — fail open
        logger.debug("A-share gtimg identity failed for %s: %s", ticker, exc)
        return {}


@functools.lru_cache(maxsize=256)
def resolve_instrument_identity(ticker: str) -> dict:
    """Resolve deterministic identity metadata (company name, sector, …) for a ticker.

    This exists to stop the pipeline from hallucinating a *different* company
    when a chart pattern suggests a different industry than the real one
    (#814): without a ground-truth name, the market analyst would pattern-match
    the price action to a narrative and invent an identity that then cascaded
    through every downstream agent.

    Best-effort by design: if yfinance is unavailable, rate-limited, or doesn't
    recognise the ticker, we return ``{}`` and the caller falls back to
    ticker-only context rather than failing before analysis starts. Cached so
    the lookup happens at most once per ticker per process.

    The symbol is normalized first (e.g. ``XAUUSD`` -> ``GC=F``) so identity
    resolves for the same instrument the price path actually fetches (#983).
    """
    # A-share 6-digit codes: yfinance often rate-limits / returns empty info,
    # which left identity {} and the LLM hallucinated a wrong company (603986
    # was called "北京君正" instead of 兆易创新). Use eastmoney push2 first.
    cn_identity = _resolve_cn_identity(ticker)
    if cn_identity:
        return cn_identity

    from dromx.dataflows.symbol_utils import normalize_symbol

    try:
        info = yf.Ticker(normalize_symbol(ticker)).info or {}
    except Exception as exc:  # noqa: BLE001 — fail open, never block the run
        logger.debug("Could not resolve instrument identity for %s: %s", ticker, exc)
        return {}

    identity: dict[str, str] = {}
    company_name = _clean_identity_value(info.get("longName")) or _clean_identity_value(
        info.get("shortName")
    )
    if company_name:
        identity["company_name"] = company_name
    for source_key, target_key in (
        ("sector", "sector"),
        ("industry", "industry"),
        ("exchange", "exchange"),
        ("quoteType", "quote_type"),
    ):
        value = _clean_identity_value(info.get(source_key))
        if value:
            identity[target_key] = value
    return identity


def build_instrument_context(
    ticker: str,
    asset_type: str = "stock",
    identity: Mapping[str, str] | None = None,
) -> str:
    """Describe the exact instrument so agents preserve identity and ticker.

    When ``identity`` is provided (resolved deterministically via
    :func:`resolve_instrument_identity`), the company name and business
    classification are injected so agents anchor to the real company rather
    than pattern-matching the price chart to a wrong one (#814).
    """
    is_crypto = asset_type == "crypto"
    instrument_label = "asset" if is_crypto else "instrument"
    context = (
        f"The {instrument_label} to analyze is `{ticker}`. "
        "Use this exact ticker in every tool call, report, and recommendation, "
        "preserving any exchange suffix (e.g. `.TO`, `.L`, `.HK`, `.T`, `-USD`)."
    )

    details = []
    if identity:
        name = identity.get("company_name") or identity.get("name")
        if name:
            details.append(f"{'Name' if is_crypto else 'Company'}: {name}")
        sector, industry = identity.get("sector"), identity.get("industry")
        if sector and industry:
            details.append(f"Business classification: {sector} / {industry}")
        elif sector:
            details.append(f"Sector: {sector}")
        elif industry:
            details.append(f"Industry: {industry}")
        if identity.get("exchange"):
            details.append(f"Exchange: {identity['exchange']}")

    if details:
        context += (
            f" Resolved identity: {'; '.join(details)}. "
            "Do not substitute a different company or ticker unless a tool "
            "result explicitly disproves this resolved identity."
        )

    if is_crypto:
        context += (
            " Treat it as a crypto asset rather than a company, and do not "
            "assume company fundamentals are available."
        )
    return context


def get_instrument_context_from_state(state: Mapping[str, Any]) -> str:
    """Return the instrument context for the current run.

    Prefers the identity-resolved context computed once at run start and
    stored on the state (see ``DromXGraph.resolve_instrument_context``).
    Falls back to a ticker-only context — with no network lookup — when the
    state was constructed without it (bare programmatic states, tests), so a
    consumer is never forced to make a yfinance call mid-graph.
    """
    context = state.get("instrument_context")
    if isinstance(context, str) and context.strip():
        return context
    return build_instrument_context(
        str(state["company_of_interest"]),
        state.get("asset_type", "stock"),
    )


def get_regime_context_from_state(state: Mapping[str, Any]) -> str:
    """Return a short regime-context block to inject into analyst prompts.

    The Regime Analyst runs before the analyst team and writes
    ``regime_report`` to the state. We surface it to each downstream analyst so
    they can weight their lens per the prevailing market state. Returns an empty
    string when no regime report is present (e.g. regime node disabled, or a
    bare programmatic state), so callers can splice it in unconditionally.
    """
    report = state.get("regime_report")
    if isinstance(report, str) and report.strip():
        return (
            "\n## Market regime (classified before this analysis — weight your "
            "lens accordingly)\n"
            f"{report}\n"
        )
    return ""


def get_framework_note_from_state(state: Mapping[str, Any]) -> str:
    """Return the instrument-type framework instruction to inject, or ''.

    Resolved once at run start (see ``DromXGraph._resolve_instrument_type``):
    for a fund wrapper (e.g. a 2x ETF) it tells downstream agents to analyse the
    underlying + leverage/FX rather than run company valuation on the wrapper.
    Empty for a plain equity, so callers splice it unconditionally.
    """
    note = state.get("framework_note")
    if isinstance(note, str) and note.strip():
        return f"\n{note}\n"
    return ""


def get_market_context_from_state(state: Mapping[str, Any]) -> str:
    """Return the move cross-validation block to inject, or ''.

    Computed at run start (see ``DromXGraph._build_market_context``): the
    candidate's move vs its benchmark index and peers, so a node attributes a big
    move to market/sector vs single-name BEFORE inventing a company story. Empty
    when no move/benchmark available, so callers splice it unconditionally.
    """
    ctx = state.get("market_context")
    if isinstance(ctx, str) and ctx.strip():
        return f"\n{ctx}\n"
    return ""


def get_overnight_transmission_from_state(state: Mapping[str, Any]) -> str:
    """Return the overnight transmission block to inject, or ''.

    Computed at run start (see ``DromXGraph._build_overnight_transmission``):
    the cross-market lead chain (US overnight → underlying morning → listing
    open) for an ETF, with the leverage-derived expected open and a transmission
    intact/broken flag. Empty for a non-ETF, a same-market fund, an LLM "no
    link" verdict, or any fetch failure, so callers splice it unconditionally.
    """
    ctx = state.get("overnight_transmission")
    if isinstance(ctx, str) and ctx.strip():
        return f"\n{ctx}\n"
    return ""


def get_pattern_discovery_from_state(state: Mapping[str, Any]) -> str:
    """Return the forensics discovery block to inject, or ''.

    Computed at run start (see ``DromXGraph._build_pattern_discovery``):
    the anomaly-driven reverse anchor search — anomaly days, the pivot-vs-anchor
    deviation competition, algorithmic-precision verdict, and evolution. Pure
    deterministic EVIDENCE (no LLM) so the Market Analyst reasons from computed
    facts, not its own narrative. Empty for a normal tape (no anomaly) or thin
    data, so callers splice it unconditionally.
    """
    ctx = state.get("pattern_discovery")
    if isinstance(ctx, str) and ctx.strip():
        return f"\n{ctx}\n"
    return ""


def get_foreign_flow_from_state(state: Mapping[str, Any]) -> str:
    """Return the foreign-flow (chip) block to inject, or ''.

    Computed at run start (see ``DromXGraph._build_foreign_flow``):
    Korea-only (Naver) foreign-ownership% snapshot + daily net-trading series +
    a consecutive net-sell/buy-days flag. Empty for non-Korea tickers or on
    fetch failure, so callers splice it unconditionally.
    """
    ctx = state.get("foreign_flow")
    if isinstance(ctx, str) and ctx.strip():
        return f"\n{ctx}\n"
    return ""


def get_position_context_from_state(state: Mapping[str, Any]) -> str:
    """Return the user's existing-position block to inject, or ''.

    Set at run start from the user's declared position IN this name (shares +
    cost basis → unrealized P&L). Present → the decision is framed as managing an
    OPEN position (add / trim / hold / exit); empty → a build-from-flat decision.
    """
    ctx = state.get("position_context")
    if isinstance(ctx, str) and ctx.strip():
        return f"\n{ctx}\n"
    return ""


# Shared numeric-discipline rule injected into every agent that emits a price,
# stop, or target. The point is to kill confident-but-unsourced numbers (the
# "115.86 with no derivation" failure): a number is only allowed if it traces to
# data already in context, with the derivation shown.
NUMERIC_DISCIPLINE = (
    "\n**Numeric discipline (no unsourced precision):**\n"
    "- Every price, stop-loss, or target you state MUST show its derivation from "
    "data already in context — an ATR multiple (e.g. close − 2×ATR), a prior "
    "low/high, a moving-average level, or for a leveraged ETF: underlying move × "
    "leverage × tracking haircut. State the inputs and the arithmetic.\n"
    "- If you cannot ground a number in provided data, do NOT emit a two-decimal "
    "figure — give a clearly-labelled 'reference range' or say it is unavailable. "
    "A precise number with no source is a hallucination, not a forecast.\n"
    "- Use ONE current price (the verified latest close) consistently; never quote "
    "two different 'current' prices.\n"
)


def get_numeric_discipline() -> str:
    """Return the shared numeric-discipline rule block (see ``NUMERIC_DISCIPLINE``)."""
    return NUMERIC_DISCIPLINE


# Shared source-attribution + freshness rule. Two real failures motivate it:
# (1) stale data treated as current — citing a pre-earnings guidance preview
#     after the print already landed; (2) un-sourced claims a reader can't check
#     — attributing "7/10" to the wrong event. It is GENERIC across factors: every
#     analyst cites something (a price snapshot, an indicator reading, a financial
#     line item, a sentiment score, a peer figure, a news item) and must tag where
#     it came from. The frontend lifts 【来源：…】 tags into clickable citations.
SOURCE_FRESHNESS_DISCIPLINE = (
    "\n**Source & freshness discipline (every data-backed claim is traceable and current):**\n"
    "- Tag EVERY figure, fact, or event you cite inline with the data block it came "
    "from and its date — e.g. 【来源：技术快照 · 2026-06-24】, 【来源：财报 FY24Q1】, "
    "【来源：StockTwits 情绪】, 【来源：新闻标题 · 2026-06-24】. Use the [YYYY-MM-DD] "
    "stamp when the source carries one. This applies to ALL of your numbers (prices, "
    "indicators, ratios, sentiment scores, peer comparisons), not just news — a reader "
    "must be able to trace any claim back to a block provided to you.\n"
    "- Check recency against TODAY's analysis date before relying on a dated item. An "
    "event dated BEFORE today has already happened: use its actual outcome, never the "
    "prior pre-event prediction (e.g. if an earnings date has passed, reason from the "
    "result, not the preview). An item marked '[date unknown]' is unverified — flag it "
    "as such and do NOT treat it as a current catalyst.\n"
    "- Never attach a specific date to an event unless that date is in the provided data. "
    "If you are unsure which event a date refers to, say '待核实/date to verify' rather "
    "than guessing — a confident wrong date is worse than an acknowledged gap.\n"
)


def get_source_freshness_discipline() -> str:
    """Return the shared source-attribution + freshness rule (see ``SOURCE_FRESHNESS_DISCIPLINE``)."""
    return SOURCE_FRESHNESS_DISCIPLINE


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add a context-anchored placeholder.

        The placeholder must not be a bare ``"Continue"``: some
        OpenAI-compatible providers interpret that literally as the user task
        and produce output about the word "continue" instead of analysing the
        instrument (#888). Anchoring it to the resolved instrument context and
        date keeps the next analyst on-task even if the provider treats the
        placeholder as a standalone request.
        """
        messages = state["messages"]
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        instrument_context = get_instrument_context_from_state(state)
        trade_date = state.get("trade_date", "the requested date")
        placeholder = HumanMessage(
            content=(
                f"Proceed with your assigned analysis for this workflow. "
                f"{instrument_context} The analysis date is {trade_date}."
            )
        )
        return {"messages": removal_operations + [placeholder]}

    return delete_messages




"""Naver Finance — Korea-only foreign-flow (chip) data.

The SK Hynix case study's lead indicator was the foreign-ownership% trend
(51.29% → 50.06%, 23 days of only-selling) — chip-face evidence that the
forensics engine can't get from OHLCV alone. Naver's item page exposes both:
  - a foreign-ownership% snapshot (외국인비율)
  - a daily foreign net-trading table (날짜/종가/전일비/외국인/기관, ~30 days)

This builder fetches both and computes the "consecutive net sell/buy days"
signal — the case study's "23 days only-selling" — deterministically, with no
LLM. Korea-only (.KS/.KQ); non-Korea tickers return '' so other markets are
unchanged. Mirrors the best-effort contract of overnight_transmission /
pattern_discovery.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_BASE = "https://finance.naver.com/item/main.naver?code={code}"
_UA = {"User-Agent": "Mozilla/5.0"}
_MIN_CONSEC_FOR_FLAG = 5  # consecutive same-sign days before the ⚠️ flag


def _safe(fn, default=None):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 — foreign-flow is best-effort, never aborts
        logger.debug("naver: %s", exc)
        return default


def _kr_code(ticker: str) -> str | None:
    """000660.KS / 000660.KQ / bare 000660 → '000660'; non-Korea → None."""
    s = ticker.strip().upper()
    if "." in s:
        base, _, suf = s.rpartition(".")
        if suf in ("KS", "KQ") and base.isdigit():
            return base
    if s.isdigit() and len(s) == 6:
        return s
    return None


def _fetch_page(code: str) -> str | None:
    def go():
        import requests

        r = requests.get(_BASE.format(code=code), headers=_UA, timeout=12)
        r.raise_for_status()
        # Naver serves UTF-8 (confirmed); ignore any stray bytes.
        return r.content.decode("utf-8", errors="ignore")

    return _safe(go)


def _parse_ownership_pct(html: str) -> float | None:
    """외국인비율(%) snapshot — first number in the row/cell containing that label.

    Walks up a few levels from the label text so it survives Naver wrapping the
    label in spans/strongs; the snapshot row reads "외국인비율(%) 50.05 ...".
    """
    def go():
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for el in soup.find_all(string=re.compile(r"외국인비율")):
            ctx = el.parent
            for _ in range(4):  # search up a few levels
                if ctx is None:
                    break
                row = ctx.get_text(" ", strip=True)
                if "외국인비율" in row:
                    after = row.split("외국인비율", 1)[1]
                    m = re.search(r"[\d.]+", after)
                    if m:
                        return float(m.group())
                ctx = ctx.parent
        return None

    return _safe(go)


def _parse_daily_net(html: str) -> list[tuple[str, int]]:
    """[(date_str, net_shares), ...] from the 날짜/외국인/기관 table, newest first."""
    def go():
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for table in soup.find_all("table"):
            if "외국인" not in table.get_text():
                continue
            out: list[tuple[str, int]] = []
            for tr in table.find_all("tr"):
                cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
                if len(cells) < 5 or cells[0] in ("날짜", ""):
                    continue
                date = cells[0]
                m = re.search(r"([+-]?[\d,]+)", cells[3])  # 외국인 column
                if not m:
                    continue
                try:
                    net = int(m.group(1).replace(",", ""))
                except ValueError:
                    continue
                out.append((date, net))
            if out:
                return out
        return []

    return _safe(go, default=[]) or []


def fetch_foreign_trading(ticker: str, curr_date: str) -> dict | None:
    """Fetch foreign-ownership% snapshot + daily net-trading series, or None."""
    code = _kr_code(ticker)
    if not code:
        return None
    html = _fetch_page(code)
    if not html:
        return None
    pct = _parse_ownership_pct(html)
    daily = _parse_daily_net(html)
    if pct is None and not daily:
        return None
    return {"foreign_ownership_pct": pct, "daily_net": daily}


def _consecutive_run(daily: list[tuple[str, int]]) -> tuple[str, int]:
    """(direction, days) of the trailing same-sign run.

    ``daily`` is newest-first (Naver table order), so the run is counted from
    ``daily[0]`` forward (newest → oldest). direction is 'sell' if the latest
    day is net negative, 'buy' if positive, 'flat' if zero.
    """
    if not daily:
        return ("flat", 0)
    last = daily[0][1]
    if last == 0:
        return ("flat", 0)
    sign = 1 if last > 0 else -1
    days = 0
    for _, net in daily:  # newest → oldest
        if (net > 0 and sign > 0) or (net < 0 and sign < 0):
            days += 1
        else:
            break
    return ("buy" if sign > 0 else "sell", days)


def _fmt_net(n: int) -> str:
    return f"{n:+,}"


def build_foreign_flow(ticker: str, curr_date, config: dict | None = None) -> str:
    """Render the foreign-flow (chip) block, or '' for non-Korea / failure."""
    data = _safe(lambda: fetch_foreign_trading(ticker, str(curr_date)))
    if not data:
        return ""

    pct = data.get("foreign_ownership_pct")
    daily = data.get("daily_net") or []

    lines: list[str] = ["## 外资筹码（Naver）"]
    if pct is not None:
        lines.append(f"- **当前外资持股:** {pct:.2f}%（截至最新）")

    if daily:
        window = min(20, len(daily))
        cum = sum(n for _, n in daily[:window])
        cum_label = "净流出" if cum < 0 else "净流入" if cum > 0 else "持平"
        lines.append(f"- **近 {window} 日外资净买卖:** {_fmt_net(cum)} 股（{cum_label}）")

        direction, days = _consecutive_run(daily)
        if days >= _MIN_CONSEC_FOR_FLAG:
            is_sell = direction == "sell"
            tag = "⚠️ 外资持续流出" if is_sell else "⚠️ 外资持续流入"
            verb = "卖" if is_sell else "买"
            mono = "减" if is_sell else "增"
            lines.append(
                f"- **连续净{verb}天数:** {days} 日（只{mono}不{'增' if is_sell else '减'}）{tag}"
            )
        elif days >= 2:
            verb = "卖" if direction == "sell" else "买"
            lines.append(f"- **连续净{verb}天数:** {days} 日")

        recent = daily[:5]
        detail = " · ".join(f"{d} {_fmt_net(n)}" for d, n in recent)
        lines.append(f"- **近 5 日明细:** {detail}")

    if len(lines) <= 1:
        return ""
    return "\n".join(lines) + "\n"

"""Comprehensive analysis report → PDF (v0.4.0 PZ).

Turns a finished analysis run into a polished, sell-side-style research report
that downloads as a single PDF:

  1. The Portfolio-Manager agent writes a cohesive report (one deep-LLM call)
     from the already-produced analysis — executive summary, thesis, key
     drivers, risks/falsification, time-horizon outlook, conclusion. Input is
     the compact ``report_summarizer`` summary (bounded tokens), not the raw
     10K-token state. Falls back to assembling the existing PM decision +
     section reports if the LLM is unavailable.
  2. The markdown is rendered into a branded HTML template (Fraunces display +
     Geist body, cover page, sectioned body) and printed to PDF by a headless
     Chromium via playwright — reusing the already-cached ms-playwright browser
     (no extra download, no pango/cairo). Result: a real .pdf download, no
     print dialog.

The generated markdown is cached back into the run record (``report_md``) so a
second export is instant and doesn't re-hit the LLM.
"""
from __future__ import annotations

import glob
import logging
import os
from datetime import datetime, timezone

import markdown as md_lib

from dromx.core.agent_utils import get_language_instruction
from webapp.backend import store

logger = logging.getLogger("dromx.web.report")

# Bump when the synthesis prompt / pipeline changes so previously-cached
# (and shallower) reports are regenerated on the next export instead of
# being served stale.
_REPORT_VERSION = 2


# ---------------------------------------------------------------------------
# 1. PM synthesis
# ---------------------------------------------------------------------------

_REPORT_PROMPT = """你是一位管理数十亿资金的资深卖方首席分析师，要基于下方**完整的多智能体分析底稿**，撰写一份**机构级深度投研报告**（markdown）。底稿包含：市场状态、异动交叉验证、组合上下文、技术面、情绪面、新闻宏观、基本面、行业与供应链、信号融合、事件冲击、关键问题、研究经理综合、交易员方案、风险共识、时间轴预测、组合经理决策——全部列在文末「完整分析底稿」。

这不是把底稿摘要或复述——底稿是你的**原始素材**，你要像资深分析师读完所有一手材料后，**重新组织、提炼、深挖、给出有洞察力的观点**，写出一篇连贯、有论证深度的研报。

## 报告结构（严格遵循，每节都要写透）

### 一、执行摘要
开门见山给出：评级、目标价/预期区间、时间框架、核心投资论点（一段），以及**最该盯的那一个变量**。让机构客户 30 秒读懂结论与理由。

### 二、投资论点与预期差
不是罗列指标，而是讲清楚**市场当前的预期是什么、价格 price-in 了多少、我们的判断与之的差（预期差 = alpha 来源）**。综合看多与看空两方最强的论据，明确我们为什么给这个评级、安全边际在哪、赔率是否对称。

### 三、分维度深度论证
逐一综合各分析师的一手发现（技术面、基本面、行业链、情绪、新闻、事件冲击），但**必须提炼成观点而非复制**——每个维度回答"它对论点是加分还是减分、权重多大、证据强度如何"。相互印证或矛盾的地方要点破。工具类型特殊的标的（如杠杆 ETF）要用对框架（底层穿透+杠杆衰减，而非公司 DCF）。**若底稿含「取证发现」块**（异常日+锚点偏差竞争+算法精度证据），这是改变前提级别的博弈取证，不是普通技术信号——必须在分维度或关键驱动里点明主锚点、方向、精度证据，并据此调整论点权重；**若含「隔夜传导」块**，在执行摘要或时间轴里引用期望开盘价与传导状态（正常/断裂）；**若含「外资筹码」块**，外资连续净卖/买是筹码面领先信号，结合取证发现的异常日判断是否机构行为。

### 四、关键驱动（加权分解）
列出决定该标的走向的 ≥3 个加权变量（各占大致权重与方向），点明最该盯的那一个，明确反对"只有单一变量"的简化。

### 五、风险与证伪
主要风险（含尾部风险）+ **明确的证伪条件**：什么具体、可观测的事件会证明论点错了，届时如何调整评级。证伪条件的时间窗口要与投资时间框架对齐。

### 六、时间轴展望
按 T+1 / T+5 / T+20 / T+60 分层给出区间、情景与置信度——短期基于技术位/ATR/事件日历，长期基于行业周期/竞争格局。给出一句话的"融合预期路径"。

### 七、结论与操作建议
明确操作（建仓/持有/减仓/规避）、仓位区间、分批与止损位——每个价格都附推导来源（ATR×N、前低、正股涨幅×杠杆×跟踪折减、Kelly 仓位锚等）。

## 硬性要求
- **深度优先**：这是深度研报不是摘要。充分展开论证、量化推导、点破因子间的相互作用。宁可长而扎实，不要短而空泛。
- **只用底稿数据**，不编造数字；任何价格/目标价/止损必须附推导来源，无来源的数字标"参考区间"不给两位小数精确值。
- 语气专业克制，像给机构客户的研报——不用感叹号、不用营销词、不用"综上所述"的空话。
- 直接输出 markdown 正文，从"### 一、执行摘要"开始，不要额外前言、不要代码块围栏、不要复述本提示词。

## 完整分析底稿
{context}
"""


# Section label map (English key → Chinese heading) for building the full
# analysis context fed to the synthesis LLM.
_CONTEXT_SECTIONS: list[tuple[str, str]] = [
    ("instrument_context", "标的属性"),
    ("regime_report", "市场状态"),
    ("market_context", "异动交叉验证"),
    ("portfolio_context", "组合上下文"),
    ("overnight_transmission", "隔夜传导"),
    ("pattern_discovery", "取证发现"),
    ("foreign_flow", "外资筹码"),
    ("market_report", "技术面分析"),
    ("sentiment_report", "情绪面分析"),
    ("news_report", "新闻与宏观"),
    ("fundamentals_report", "基本面分析"),
    ("industry_report", "行业与供应链"),
    ("signal_aggregation", "信号融合"),
    ("event_impact", "事件冲击评估"),
    ("key_question", "关键问题"),
    ("investment_plan", "研究经理综合"),
    ("trader_investment_plan", "交易员方案"),
    ("risk_consensus", "风险共识"),
    ("forecast_report", "时间轴预测"),
    ("final_trade_decision", "组合经理决策"),
]


def _build_full_context(final_state: dict) -> str:
    """Assemble the FULL analysis (not a compressed summary) as report input.

    The complete finished state is only ~12k tokens — small enough to feed a
    single deep-LLM call whole. Feeding the full one-hand material (rather than
    a truncated ~900-char-per-analyst summary) is what lets the PM write a deep
    report instead of a shallow paraphrase.
    """
    parts: list[str] = []
    for key, label in _CONTEXT_SECTIONS:
        val = (final_state.get(key) or "").strip()
        if val:
            parts.append(f"## {label}\n\n{val}")
    return "\n\n".join(parts)


def _synthesize_markdown(final_state: dict, llm) -> str:
    """One deep-LLM call → deep report markdown. Falls back to assembly on failure.

    Feeds the FULL analysis state and uses the deep-thinking LLM so the report
    has real analytical depth, not a summary of a summary.
    """
    ctx = _build_full_context(final_state)
    prompt = _REPORT_PROMPT.format(context=ctx) + get_language_instruction()
    try:
        resp = llm.invoke(prompt)
        text = getattr(resp, "content", str(resp)).strip()
        # strip an accidental ```markdown fence
        if text.startswith("```"):
            text = text.split("```", 2)[1] if text.count("```") >= 2 else text.strip("`")
            text = text.split("\n", 1)[-1] if text.lower().startswith("markdown") else text
        if len(text) > 400:
            return text
        logger.warning("report synthesis returned too little; using assembly fallback")
    except Exception as e:  # noqa: BLE001 — never fail the export over the LLM
        logger.warning("report synthesis failed (%s); using assembly fallback", e)
    return _assemble_fallback(final_state)


def _assemble_fallback(final_state: dict) -> str:
    """No-LLM fallback: assemble the PM decision + section reports into markdown."""
    parts: list[str] = []
    pm = (final_state.get("final_trade_decision") or "").strip()
    if pm:
        parts.append("## 组合经理决策\n\n" + pm)
    for key, label in store.REPORT_SECTIONS:
        if key == "final_trade_decision":
            continue
        v = (final_state.get(key) or "").strip()
        if v:
            parts.append(f"## {label}\n\n{v}")
    return "\n\n".join(parts) or "_本次分析暂无可用内容。_"


# ---------------------------------------------------------------------------
# 2. Caching (report markdown lives in the run record)
# ---------------------------------------------------------------------------


def get_cached(run_id: str) -> str | None:
    rec = store.load_run(run_id)
    if rec is None:
        return None
    md = rec.get("report_md")
    return md if isinstance(md, str) and md.strip() else None


def build_report_markdown(run_id: str, llm, *, force: bool = False) -> tuple[str, dict] | None:
    """Return (markdown, run_record) for ``run_id``; None if the run is absent.

    Uses the cached markdown only when it was produced by the current
    ``_REPORT_VERSION`` (so older, shallower reports regenerate). Persists a
    freshly generated one together with its version stamp.
    """
    rec = store.load_run(run_id)
    if rec is None:
        return None
    if not force:
        cached = rec.get("report_md")
        if (isinstance(cached, str) and cached.strip()
                and rec.get("report_version") == _REPORT_VERSION):
            return cached, rec
    final_state = rec.get("final_state") or {}
    md = _synthesize_markdown(final_state, llm)
    try:
        rec["report_md"] = md
        rec["report_version"] = _REPORT_VERSION
        store.save_run(rec)
    except Exception as e:  # noqa: BLE001 — caching is best-effort
        logger.warning("failed to cache report_md for %s: %s", run_id, e)
    return md, rec


# ---------------------------------------------------------------------------
# 3. HTML template + PDF rendering
# ---------------------------------------------------------------------------

_CSS = """
@page { size: A4; margin: 22mm 18mm 20mm; }
* { box-sizing: border-box; }
body {
  font-family: "Geist", -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
  color: #0e1a14; line-height: 1.7; font-size: 10.5pt; margin: 0;
  -webkit-font-smoothing: antialiased;
}
.cover { page-break-after: always; padding-top: 26vh; }
.cover .eyebrow { font-size: 10pt; letter-spacing: 0.22em; text-transform: uppercase; color: #03894a; font-weight: 600; }
.cover h1 { font-family: "Fraunces", Georgia, serif; font-size: 40pt; line-height: 1.08; letter-spacing: -0.02em; margin: 14px 0 6px; }
.cover .sub { color: #54635b; font-size: 12pt; margin-top: 8px; }
.cover .meta { margin-top: 40px; display: flex; gap: 28px; color: #54635b; font-size: 10pt; }
.cover .meta b { color: #0e1a14; font-weight: 600; }
.badge { display: inline-block; border-radius: 999px; padding: 4px 14px; font-weight: 600; font-size: 11pt;
  background: #e6f9f0; color: #03894a; }
.badge.bear { background: #ffecec; color: #ff5a5f; }
.badge.neutral { background: #fff4de; color: #b8780a; }
h2 { font-family: "Fraunces", Georgia, serif; font-size: 17pt; letter-spacing: -0.01em; margin: 1.6em 0 0.5em;
  padding-bottom: 6px; border-bottom: 1px solid #e6ebe7; color: #0e1a14; page-break-after: avoid; }
h3 { font-size: 12pt; font-weight: 600; margin: 1.1em 0 0.3em; }
p { margin: 0.5em 0; color: #24312b; }
strong { color: #0e1a14; }
ul, ol { padding-left: 1.3em; margin: 0.4em 0; }
li { margin: 0.25em 0; }
table { width: 100%; border-collapse: collapse; margin: 0.8em 0; font-size: 9.5pt; }
th, td { border: 1px solid #e6ebe7; padding: 6px 9px; text-align: left; }
th { background: #f0f4f1; font-weight: 600; }
td { font-variant-numeric: tabular-nums; }
code { font-family: "Geist Mono", monospace; background: #f0f4f1; padding: 1px 5px; border-radius: 4px; font-size: 9pt; }
blockquote { border-left: 3px solid #06c167; margin: 0.6em 0; padding: 2px 0 2px 14px; color: #54635b; }
.footer { margin-top: 28px; padding-top: 10px; border-top: 1px solid #e6ebe7; color: #8a978f; font-size: 8.5pt; }
"""

_FONTS = ("https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700"
          "&family=Geist+Mono:wght@400;500&family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&display=swap")


def _rating_class(rating: str | None) -> str:
    r = (rating or "").lower()
    if any(w in r for w in ("sell", "underweight", "减", "卖")):
        return "bear"
    if any(w in r for w in ("hold", "neutral", "持有", "中")):
        return "neutral"
    return ""  # bull/overweight/buy → default green


def render_html(markdown_text: str, *, ticker: str, trade_date: str, rating: str | None) -> str:
    body = md_lib.markdown(markdown_text, extensions=["tables", "fenced_code", "sane_lists"])
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    badge = f'<span class="badge {_rating_class(rating)}">{rating or "—"}</span>'
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{_FONTS}" rel="stylesheet">
<style>{_CSS}</style></head><body>
<section class="cover">
  <div class="eyebrow">DromX · 综合投研报告</div>
  <h1>{ticker}</h1>
  <div class="sub">多智能体 AI 深度分析 · 综合研报</div>
  <div class="meta">
    <div>评级<br><b>{badge}</b></div>
    <div>分析日期<br><b>{trade_date or "—"}</b></div>
    <div>生成时间<br><b>{stamp}</b></div>
  </div>
</section>
<main>{body}
  <div class="footer">本报告由 DromX 多智能体系统基于公开免费数据自动生成，仅供研究参考，不构成投资建议。生成于 {stamp}。</div>
</main>
</body></html>"""


def _find_chromium() -> str | None:
    """Locate an already-cached ms-playwright Chromium (avoid a fresh download)."""
    pats = [
        os.path.expanduser("~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium"),
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
    ]
    for pat in pats:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def html_to_pdf(html: str) -> bytes:
    """Render HTML → PDF bytes via a headless Chromium (playwright)."""
    from playwright.sync_api import sync_playwright

    exe = _find_chromium()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            page.emulate_media(media="screen")
            pdf = page.pdf(format="A4", print_background=True,
                           margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        finally:
            browser.close()
    return pdf


def build_report_pdf(run_id: str, llm) -> tuple[bytes, dict] | None:
    """Full path: markdown (cached/generated) → HTML → PDF bytes. None if no run."""
    res = build_report_markdown(run_id, llm)
    if res is None:
        return None
    md, rec = res
    html = render_html(
        md,
        ticker=(rec.get("ticker") or "").strip() or run_id,
        trade_date=(rec.get("trade_date") or "").strip(),
        rating=rec.get("rating"),
    )
    return html_to_pdf(html), rec

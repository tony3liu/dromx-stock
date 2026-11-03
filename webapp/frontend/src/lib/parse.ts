// Light client-side parsers over the engine's markdown report sections.
// The engine emits deterministic bold headers (**Field**: value), so we can lift
// the decision card's key numbers without changing the engine.

export interface DecisionFields {
  rating: string | null;
  executiveSummary: string | null;
  priceTarget: string | null;
  stop: string | null;
  sizing: string | null;
  horizon: string | null;
}

function boldField(md: string, label: string): string | null {
  // Two engine formats:
  //   **Label**: value        (label and value separate — e.g. RAM)
  //   **Label：value**        (label + colon + value all inside one bold — e.g. MU)
  // Match either, capturing only up to the end of line or the closing ** — never
  // spilling across into the NEXT bold block (which produced the doubled-text bug).
  const inside = md.match(new RegExp(`\\*\\*\\s*${label}\\s*[:：]\\s*([^*\\n]+?)\\s*\\*\\*`, "i"));
  if (inside) return inside[1].trim();
  const outside = md.match(new RegExp(`\\*\\*\\s*${label}\\s*\\*\\*\\s*[:：]?\\s*([^\\n*]+)`, "i"));
  return outside ? outside[1].trim() : null;
}

// A rating value is a single band word; strip any trailing prose the field may
// carry (e.g. "Underweight（减持…）" → "Underweight").
const _RATING_WORDS = /(Buy|Overweight|Hold|Neutral|Underweight|Sell|买入|增持|持有|中性|减持|卖出)/i;
function cleanRating(v: string | null): string | null {
  if (!v) return null;
  const m = v.match(_RATING_WORDS);
  return m ? m[1] : v.split(/[\s（(：:，,]/)[0] || v;
}

// Grab the first non-empty paragraph under a markdown heading like `## 执行摘要`
// or `### Executive Summary`. Engine reports often use headings, not bold fields.
function sectionUnderHeading(md: string, names: string[]): string | null {
  for (const name of names) {
    const re = new RegExp(`#{2,4}\\s*${name}[^\\n]*\\n+([\\s\\S]*?)(?:\\n#{2,4}\\s|\\n-{3,}|$)`, "i");
    const m = md.match(re);
    if (m) {
      // first paragraph, strip bold markers and surrounding whitespace
      const para = m[1].trim().split(/\n\s*\n/)[0]?.replace(/\*\*/g, "").trim();
      if (para) return para;
    }
  }
  return null;
}

// Pull the first "$123" / "123.45" / "95-100" style figure near a keyword in text.
function nearNumber(text: string, keywords: string[]): string | null {
  for (const kw of keywords) {
    const re = new RegExp(
      `${kw}[^0-9]{0,12}((?:US?\\$|HK\\$|￥)?\\d[\\d,\\.]*(?:\\s*[-–~]\\s*\\d[\\d,\\.]*)?%?)`,
      "i",
    );
    const m = text.match(re);
    if (m) return m[1].trim();
  }
  return null;
}

export function parseDecision(md: string): DecisionFields {
  const rating = cleanRating(boldField(md, "评级") ?? boldField(md, "Rating"));
  const exec =
    boldField(md, "执行摘要") ??
    boldField(md, "Executive Summary") ??
    sectionUnderHeading(md, ["执行摘要", "Executive Summary", "核心行动", "核心决策"]);
  const summaryBlock = exec ?? md;
  return {
    rating,
    executiveSummary: exec,
    priceTarget:
      boldField(md, "目标价") ??
      boldField(md, "Price Target") ??
      nearNumber(summaryBlock, ["看至", "首目标", "目标价", "目标看", "target"]),
    stop: nearNumber(summaryBlock, ["止损", "stop"]),
    sizing: nearNumber(summaryBlock, ["仓位", "敞口", "规模", "position", "size", "%"]),
    horizon:
      boldField(md, "时间框架") ??
      boldField(md, "Time Horizon") ??
      (summaryBlock.match(/时间框架[：:]*\s*([0-9]+\s*[-–~]?\s*[0-9]*\s*(?:个月|周|天|months?|weeks?))/i)?.[1] ??
        summaryBlock.match(/([0-9]+\s*[-–~]\s*[0-9]+\s*(?:个月|months?))/i)?.[1] ??
        null),
  };
}

export interface SignalRow {
  analyst: string;
  direction: string;
  confidence: string;
  score: string;
}
export interface SignalSummary {
  consensus: string | null;
  weightedScore: string | null;
  agreement: string | null;
  ev: string | null;
  skew: string | null;
  rows: SignalRow[];
}

export function parseSignal(md: string): SignalSummary {
  const head = md.match(/\*\*融合信号：\*\*\s*\*\*([^*]+)\*\*\s*（加权分\s*([+\-]?[\d.]+)，一致性：\s*([^）]+)）/);
  const ev = md.match(/融合期望值\s*≈?\s*([+\-]?[\d.]+%)/)?.[1] ?? null;
  const skew = md.match(/收益偏度\s+([^\s（(·]+)/)?.[1]?.trim() ?? null;

  const rows: SignalRow[] = [];
  // Table rows: | 分析师 | 方向 | 置信度 | 评分 |
  const lines = md.split("\n").filter((l) => l.trim().startsWith("|"));
  for (const l of lines) {
    const cells = l.split("|").map((c) => c.trim()).filter(Boolean);
    if (cells.length !== 4) continue;
    if (/^分析师$/.test(cells[0]) || /^[-:]+$/.test(cells[1])) continue;
    rows.push({ analyst: cells[0], direction: cells[1], confidence: cells[2], score: cells[3] });
  }

  return {
    consensus: head?.[1]?.trim() ?? null,
    weightedScore: head?.[2]?.trim() ?? null,
    agreement: head?.[3]?.trim() ?? null,
    ev,
    skew,
    rows,
  };
}

export interface ForecastLeg {
  horizon: string; // T+1 ...
  direction: string | null;
  confidence: string | null;
  range: string | null;
  body: string;
}

export function parseForecast(md: string): { legs: ForecastLeg[]; path: string | null } {
  const path =
    md.match(/\*\*Expected path:\*\*\s*([^\n]+)/i)?.[1]?.trim() ??
    md.match(/(?:预期路径|路径)[：:]\s*\**\s*([^\n*]+)/i)?.[1]?.trim() ??
    null;

  const legs: ForecastLeg[] = [];
  // Find every horizon heading and slice the body between consecutive headings.
  // Handles all observed shapes: "### T+1 — …", "#### T+1: 下一交易日 (…)",
  // bare "T+1（…）". `T+N` may sit behind any number of `#` and whitespace.
  const headRe = /(?:^|\n)\s*#{0,6}\s*(T\+\d+)\b/g;
  const heads: { horizon: string; start: number }[] = [];
  for (let m = headRe.exec(md); m; m = headRe.exec(md)) {
    heads.push({ horizon: m[1], start: m.index });
  }
  for (let i = 0; i < heads.length; i++) {
    const p = md.slice(heads[i].start, i + 1 < heads.length ? heads[i + 1].start : undefined);
    const horizon = heads[i].horizon;
    const dir =
      p.match(/(Mildly Bullish|Mildly Bearish|Bullish|Neutral|Bearish|温和看涨|温和看跌|看涨|看跌|中性|偏多|偏空|震荡偏[下弱强上多空]|震荡)/i)?.[1] ??
      null;
    const conf = p.match(/confidence[：:\s]*([a-z高中低]+)/i)?.[1] ?? p.match(/置信度?[：:\s（(]*\**\s*([高中低]|low|medium|high)/i)?.[1] ?? null;
    legs.push({ horizon, direction: dir, confidence: conf, range: extractRange(p), body: p.trim() });
  }
  return { legs, path };
}

// Pull the predicted price range out of one horizon's body. Prefers the value
// next to a 价格区间/价格范围/range label (the table row), and rejects anything
// that looks like a date (e.g. "2026-06-30") so a heading date isn't mistaken
// for a price band.
function extractRange(p: string): string | null {
  const isDate = (s: string) => /\b20\d{2}\s*[-–]\s*\d{1,2}\b/.test(s);
  const labelled = p.match(
    /(?:price[_ ]?range|range|价格区间|价格范围|区间)\s*[*：:|\s]*([\[\(]?\s*\$?\d[\d.,]*\s*[-–~]\s*\$?\d[\d.,]*\s*[\]\)]?)/i,
  );
  if (labelled && !isDate(labelled[1])) return labelled[1];
  // last resort: first numeric "lo – hi" pair that isn't a date. \$? allows the
  // "$170 – $202" shape the LLM emits (the labelled regex handles it too, but
  // the fallback must so a body without a 价格区间 label still parses right).
  const re = /(\$?\d[\d.,]*\s*[-–~]\s*\$?\d[\d.,]*)/g;
  for (let m = re.exec(p); m; m = re.exec(p)) {
    if (!isDate(m[1])) return m[1];
  }
  return null;
}

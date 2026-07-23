// Map an internal ticker to a Google Finance symbol (TICKER:EXCHANGE) and build
// the deep links the Research Panel offers. Zero-cost, no scraping, no API — per
// PRD §4.3 (P0): just hand the user the right Google Finance URLs for the name.
//
// Internal tickers come in a few shapes:
//   NVDA            US (exchange unknown → Google resolves NASDAQ/NYSE itself)
//   600519.SS       Shanghai      → 600519:SHA
//   000001.SZ       Shenzhen      → 000001:SHE
//   07709.HK        Hong Kong     → 07709:HKG
//   7203.T          Tokyo         → 7203:TYO
//   005930.KS       Korea (KOSPI) → 005930:KRX

const SUFFIX_TO_EXCHANGE: Record<string, string> = {
  SS: "SHA",
  SH: "SHA",
  SZ: "SHE",
  HK: "HKG",
  T: "TYO",
  KS: "KRX",
  KQ: "KOSDAQ",
  L: "LON",
  TO: "TSE",
  AX: "ASX",
};

export interface GoogleFinanceLinks {
  symbol: string; // e.g. "NVDA" or "07709:HKG"
  quote: string;
  earnings: string;
  comparison: (peers?: string[]) => string;
  aiPrompt: string; // ready-to-paste prompt for Google Finance's AI panel
}

/** Resolve a ticker to its Google Finance symbol form. US names have no suffix,
 *  so we return the bare symbol and let Google resolve the listing exchange. */
export function toGoogleFinanceSymbol(ticker: string): string {
  const t = ticker.trim().toUpperCase();
  const dot = t.lastIndexOf(".");
  if (dot === -1) return t; // US / already bare
  const base = t.slice(0, dot);
  const suffix = t.slice(dot + 1);
  const ex = SUFFIX_TO_EXCHANGE[suffix];
  return ex ? `${base}:${ex}` : base;
}

export function googleFinanceLinks(ticker: string, date?: string): GoogleFinanceLinks {
  const symbol = toGoogleFinanceSymbol(ticker);
  const enc = encodeURIComponent(symbol);
  const base = `https://www.google.com/finance/quote/${enc}`;
  return {
    symbol,
    quote: base,
    earnings: `${base}?window=6M`,
    comparison: (peers?: string[]) =>
      peers && peers.length
        ? `${base}?comparison=${encodeURIComponent(peers.map(toGoogleFinanceSymbol).join(","))}`
        : base,
    aiPrompt:
      `请基于 Google Finance 的实时数据，分析 ${ticker}${date ? `（截至 ${date}）` : ""}：` +
      `1) 最新价格、估值与近期走势；2) 即将到来的财报日期与市场预期；` +
      `3) 华尔街分析师评级分布与目标价中位数；4) 同业对比中的相对位置。` +
      `用要点形式回答，标注每个数字的来源与日期。`,
  };
}

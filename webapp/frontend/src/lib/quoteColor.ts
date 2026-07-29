// 涨跌配色模式（全球用户习惯不同）：
//   intl — 绿涨红跌（美股/海外习惯，默认）
//   cn   — 红涨绿跌（A股/国内习惯）
//
// 模式持久化在 localStorage，通过 <html data-quote-color="..."> 切换
// CSS 变量（--color-bull/--color-bear，见 index.css），canvas 类图表
// （KlineChart 等不带 CSS 变量的硬编码颜色）监听 CHANGE_EVENT 重取色。

export type QuoteColorMode = "intl" | "cn";

const STORAGE_KEY = "dromx-quote-color";
export const QUOTE_COLOR_CHANGE_EVENT = "dromx:quote-color-change";

const COLORS: Record<QuoteColorMode, { up: string; down: string }> = {
  intl: { up: "#10b981", down: "#f85149" },
  cn: { up: "#f85149", down: "#10b981" },
};

export function getQuoteColorMode(): QuoteColorMode {
  try {
    return localStorage.getItem(STORAGE_KEY) === "cn" ? "cn" : "intl";
  } catch {
    return "intl";
  }
}

export function applyQuoteColorMode(mode: QuoteColorMode = getQuoteColorMode()): void {
  document.documentElement.dataset.quoteColor = mode;
}

export function setQuoteColorMode(mode: QuoteColorMode): void {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    /* private mode 等场景忽略 */
  }
  applyQuoteColorMode(mode);
  window.dispatchEvent(new CustomEvent(QUOTE_COLOR_CHANGE_EVENT, { detail: mode }));
}

/** canvas/SVG 图表用的涨跌色（跟随当前模式） */
export function quoteColors(mode: QuoteColorMode = getQuoteColorMode()): { up: string; down: string } {
  return COLORS[mode];
}

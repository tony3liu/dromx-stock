import { REPORT_SECTIONS, SECTION_CN } from "../api/types";

/** Assemble a consolidated markdown report from the streamed/stored sections. */
export function buildReportMarkdown(
  ticker: string,
  date: string,
  rating: string | null,
  sections: Record<string, string>,
): string {
  const lines: string[] = [
    `# TradingAgents 分析报告 — ${ticker}`,
    "",
    `- 分析日期: ${date}`,
    `- 评级: ${rating ?? "—"}`,
    "",
  ];
  for (const { key, label } of REPORT_SECTIONS) {
    const md = sections[key];
    if (md && md.trim()) {
      lines.push(`## ${SECTION_CN[key] ?? label}`, "", md.trim(), "");
    }
  }
  return lines.join("\n");
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

export function downloadText(filename: string, text: string): void {
  const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

import { useEffect, useState } from "react";
import { Loader2, Shield, AlertTriangle, Link2 } from "lucide-react";
import { api } from "../api/client";
import type { HedgeReport } from "../api/types";
import { cn } from "../lib/format";
import { PageHeader } from "./PageHeader";
import { Card } from "./ui/Card";

// Colour a correlation cell: red = concentrated (high +), green = hedge (neg), grey = ~0.
function corrStyle(c: number | null): { bg: string; text: string } {
  if (c == null) return { bg: "transparent", text: "var(--color-ink-faint)" };
  if (c >= 0.7) return { bg: "color-mix(in srgb, var(--color-danger) 22%, transparent)", text: "var(--color-danger)" };
  if (c >= 0.4) return { bg: "color-mix(in srgb, var(--color-danger) 10%, transparent)", text: "var(--color-ink)" };
  if (c <= -0.4) return { bg: "rgba(6,193,103,0.18)", text: "var(--color-brand-dark)" };
  return { bg: "var(--color-surface-2)", text: "var(--color-ink-soft)" };
}

export function HedgeView() {
  const [report, setReport] = useState<HedgeReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api.hedge().then((r) => alive && setReport(r))
      .catch((e) => alive && setErr(e instanceof Error ? e.message : "加载失败"))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, []);

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader
        icon={<Shield size={18} />}
        title="跨品种对冲"
        subtitle="跨品种相关性复盘，识别「三个代码、一笔押注」的集中风险与天然对冲腿"
        maxWidth="1180px"
      />
      <div className="mx-auto max-w-[1180px] px-8 py-6">

      {loading && (
        <div className="flex items-center gap-2 py-16 text-[var(--color-ink-faint)]">
          <Loader2 size={18} className="animate-spin" /> 计算相关性矩阵…
        </div>
      )}
      {err && !loading && (
        <div className="rounded-[var(--radius-card)] bg-[var(--color-danger-tint)] p-4 text-sm text-[var(--color-danger)]">{err}</div>
      )}

      {report && !loading && report.names.length < 2 && (
        <Card className="p-8 text-center text-[var(--color-ink-faint)]">
          至少需要 2 个可取价的已分析标的才能做跨品种对冲分析。
          {report.skipped.length > 0 && <div className="mt-1 text-xs">（{report.skipped.join(", ")} 价格数据不足，已跳过）</div>}
        </Card>
      )}

      {report && !loading && report.names.length >= 2 && (
        <>
          {/* suggestions */}
          {report.suggestions.length > 0 && (
            <div className="mb-5 space-y-2">
              {report.suggestions.map((s, i) => (
                <div key={i} className={cn(
                  "flex items-start gap-2.5 rounded-[var(--radius-card)] p-3.5 text-sm",
                  s.kind === "concentration" ? "bg-[var(--color-warn-tint)]" : "bg-[var(--color-brand-tint)]")}
                  style={{ boxShadow: "var(--shadow-card)" }}>
                  {s.kind === "concentration"
                    ? <AlertTriangle size={16} className="mt-0.5 shrink-0 text-[var(--color-warn)]" />
                    : <Link2 size={16} className="mt-0.5 shrink-0 text-[var(--color-brand-dark)]" />}
                  <span className="text-[var(--color-ink)]">{s.text}</span>
                </div>
              ))}
            </div>
          )}

          {/* correlation matrix */}
          <Card className="overflow-x-auto p-4">
            <div className="mb-2 text-sm font-semibold text-[var(--color-ink)]">
              相关性矩阵 <span className="font-normal text-[var(--color-ink-faint)]">· 近 {report.lookback_days} 日日收益</span>
            </div>
            <table className="border-collapse text-sm">
              <thead>
                <tr>
                  <th className="p-2"></th>
                  {report.names.map((n) => (
                    <th key={n} className="p-2 text-xs font-medium text-[var(--color-ink-soft)]">{n}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {report.matrix.map((row) => (
                  <tr key={row.ticker}>
                    <td className="p-2 text-xs font-medium text-[var(--color-ink-soft)] whitespace-nowrap">{row.ticker}</td>
                    {report.names.map((n) => {
                      const c = row.corr[n];
                      const st = corrStyle(c);
                      return (
                        <td key={n} className="p-1">
                          <div className="grid h-11 w-16 place-items-center rounded-lg tnum text-xs font-semibold"
                            style={{ background: st.bg, color: st.text }}>
                            {c == null ? "—" : c.toFixed(2)}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-[var(--color-ink-faint)]">
              <span className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded" style={{ background: "color-mix(in srgb, var(--color-danger) 22%, transparent)" }} /> ≥0.7 同一押注</span>
              <span className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded" style={{ background: "rgba(6,193,103,0.18)" }} /> ≤-0.4 对冲</span>
              {report.skipped.length > 0 && <span>· 跳过（数据不足）：{report.skipped.join(", ")}</span>}
            </div>
          </Card>
        </>
      )}
      </div>
    </div>
  );
}

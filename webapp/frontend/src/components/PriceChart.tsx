import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TrendingUp, TrendingDown } from "lucide-react";
import { api } from "../api/client";
import type { PricePoint } from "../api/types";
import { cn } from "../lib/format";

// Trailing simple moving averages over the close series, for each window.
type Row = PricePoint & { ma5?: number; ma10?: number; ma20?: number };
function withMAs(points: PricePoint[]): Row[] {
  const ma = (i: number, w: number): number | undefined => {
    if (i + 1 < w) return undefined;
    let sum = 0;
    for (let j = i - w + 1; j <= i; j++) sum += points[j].close;
    return +(sum / w).toFixed(4);
  };
  return points.map((p, i) => ({ ...p, ma5: ma(i, 5), ma10: ma(i, 10), ma20: ma(i, 20) }));
}

const MA_LINES = [
  { key: "ma5", label: "MA5", color: "var(--color-neutral)" },
  { key: "ma10", label: "MA10", color: "var(--color-violet)" },
  { key: "ma20", label: "MA20", color: "var(--color-mint)" },
] as const;
const MA_NAME: Record<string, string> = { ma5: "MA5", ma10: "MA10", ma20: "MA20", close: "收盘" };
// Fixed tooltip row order: 收盘 → MA5 → MA10 → MA20 (recharts sorts by value otherwise).
const TOOLTIP_ORDER: Record<string, number> = { close: 0, ma5: 1, ma10: 2, ma20: 3 };

export function PriceChart({ ticker, date }: { ticker: string; date?: string }) {
  const [points, setPoints] = useState<PricePoint[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    setPoints(null);
    setFailed(false);
    api
      .price(ticker, date, 120)
      .then((r) => {
        if (!alive) return;
        if (!r.points?.length) setFailed(true);
        else setPoints(r.points);
      })
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [ticker, date]);

  if (failed) return null; // best-effort: hide the chart, never break the report
  if (!points)
    return (
      <div className="skeleton h-56 w-full rounded-[var(--radius-card)]" />
    );

  const data = withMAs(points);
  const first = points[0].close;
  const last = points[points.length - 1].close;
  const chg = first ? ((last - first) / first) * 100 : 0;
  const up = chg >= 0;
  const stroke = up ? "var(--color-bull)" : "var(--color-bear)";
  const lo = Math.min(...points.map((p) => p.low ?? p.close));
  const hi = Math.max(...points.map((p) => p.high ?? p.close));
  const pad = (hi - lo) * 0.08 || 1;

  return (
    <section
      className="animate-pop rounded-[var(--radius-card)] bg-[var(--color-surface)] p-6"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-bold text-[var(--color-ink)]">
          价格走势 <span className="text-sm font-normal text-[var(--color-ink-faint)]">· 近 {points.length} 个交易日</span>
        </h2>
        <div
          className={cn(
            "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-sm font-semibold tnum",
            up ? "bg-[var(--color-bull-tint)] text-[var(--color-bull)]" : "bg-[var(--color-bear-tint)] text-[var(--color-bear)]",
          )}
        >
          {up ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
          {up ? "+" : ""}
          {chg.toFixed(2)}%
        </div>
      </div>
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: -8 }}>
            <defs>
              <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={stroke} stopOpacity={0.22} />
                <stop offset="100%" stopColor={stroke} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--color-border)" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: "var(--color-ink-faint)" }}
              tickFormatter={(d: string) => d.slice(5)}
              minTickGap={40}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              domain={[+(lo - pad).toFixed(2), +(hi + pad).toFixed(2)]}
              tick={{ fontSize: 11, fill: "var(--color-ink-faint)" }}
              width={48}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                borderRadius: 12,
                border: "1px solid var(--color-border)",
                fontSize: 12,
              }}
              labelStyle={{ color: "var(--color-ink-soft)" }}
              itemSorter={(item) => TOOLTIP_ORDER[String(item.dataKey)] ?? 99}
              formatter={(v, name) => [
                typeof v === "number" ? v.toFixed(2) : String(v ?? ""),
                MA_NAME[String(name)] ?? String(name),
              ]}
            />
            <Area
              type="monotone"
              dataKey="close"
              name="close"
              stroke={stroke}
              strokeWidth={2}
              fill="url(#priceFill)"
              dot={false}
              isAnimationActive={false}
            />
            {MA_LINES.map((m) => (
              <Area
                key={m.key}
                type="monotone"
                dataKey={m.key}
                name={m.key}
                stroke={m.color}
                strokeWidth={1.5}
                fill="none"
                dot={false}
                isAnimationActive={false}
                connectNulls
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* legend */}
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-[var(--color-ink-soft)]">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-3 rounded-full" style={{ background: stroke }} /> 收盘
        </span>
        {MA_LINES.map((m) => (
          <span key={m.key} className="flex items-center gap-1.5">
            <span className="inline-block h-0.5 w-3.5 rounded-full" style={{ background: m.color }} />
            {m.label}
          </span>
        ))}
      </div>
    </section>
  );
}

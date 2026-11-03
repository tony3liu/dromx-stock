import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";

// A distinct, ZA-friendly palette for overlaid tickers.
const SERIES_COLORS = [
  "var(--color-brand)",
  "var(--color-violet)",
  "var(--color-neutral)",
  "var(--color-mint)",
];

interface Props {
  tickers: string[];
  date?: string;
}

/**
 * Overlays each ticker's close price REBASED to 100 at its first point, so
 * tickers from different markets / price levels compare on % terms. Aligns by
 * trading-day index (not calendar date) so cross-market series line up.
 */
export function ComparePriceChart({ tickers, date }: Props) {
  const [series, setSeries] = useState<Record<string, number[]> | null>(null);

  useEffect(() => {
    let alive = true;
    setSeries(null);
    Promise.all(
      tickers.map((t) =>
        api
          .price(t, date, 120)
          .then((r) => [t, r.points.map((p) => p.close)] as const)
          .catch(() => [t, [] as number[]] as const),
      ),
    ).then((pairs) => {
      if (!alive) return;
      const out: Record<string, number[]> = {};
      for (const [t, closes] of pairs) {
        const base = closes[0];
        out[t] = base ? closes.map((c) => +((c / base) * 100).toFixed(2)) : [];
      }
      setSeries(out);
    });
    return () => {
      alive = false;
    };
  }, [tickers.join(","), date]);

  if (!series) return <div className="skeleton h-64 w-full rounded-[var(--radius-card)]" />;

  const maxLen = Math.max(0, ...tickers.map((t) => series[t]?.length ?? 0));
  if (maxLen === 0) return null;

  // Build row-per-day data: { i, <ticker>: rebasedValue, ... }
  const data = Array.from({ length: maxLen }, (_, i) => {
    const row: Record<string, number | string> = { i: i - maxLen + 1 }; // 0 = latest
    for (const t of tickers) {
      const arr = series[t] ?? [];
      // right-align series so the latest points coincide at i = 0
      const off = maxLen - arr.length;
      if (i >= off) row[t] = arr[i - off];
    }
    return row;
  });

  return (
    <section
      className="animate-pop rounded-[var(--radius-card)] bg-[var(--color-surface)] p-6"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <h2 className="mb-1 text-base font-bold text-[var(--color-ink)]">
        相对走势 <span className="text-sm font-normal text-[var(--color-ink-faint)]">· 归一到 100</span>
      </h2>
      <p className="mb-3 text-xs text-[var(--color-ink-faint)]">
        各标的收盘价按起点归一为 100，横轴为相对交易日（0 = 最新），便于跨市场比较涨跌幅。
      </p>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 6, right: 12, bottom: 0, left: -8 }}>
            <CartesianGrid stroke="var(--color-border)" vertical={false} />
            <XAxis
              dataKey="i"
              tick={{ fontSize: 11, fill: "var(--color-ink-faint)" }}
              axisLine={false}
              tickLine={false}
              minTickGap={36}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "var(--color-ink-faint)" }}
              width={42}
              axisLine={false}
              tickLine={false}
              domain={["auto", "auto"]}
            />
            <Tooltip
              contentStyle={{ borderRadius: 12, border: "1px solid var(--color-border)", fontSize: 12 }}
              labelFormatter={(i) => `相对日 ${i}`}
            />
            {tickers.map((t, idx) => (
              <Line
                key={t}
                type="monotone"
                dataKey={t}
                name={t}
                stroke={SERIES_COLORS[idx % SERIES_COLORS.length]}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-3 flex flex-wrap gap-3">
        {tickers.map((t, idx) => (
          <span key={t} className="flex items-center gap-1.5 text-sm text-[var(--color-ink-soft)]">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ background: SERIES_COLORS[idx % SERIES_COLORS.length] }}
            />
            {t}
          </span>
        ))}
      </div>
    </section>
  );
}

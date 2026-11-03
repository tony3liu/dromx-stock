import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { parseForecast } from "../lib/parse";

// Parse "180-200" / "[180.5 ~ 201]" / "180–200" into [lo, hi].
function parseRange(range: string | null): [number, number] | null {
  if (!range) return null;
  const nums = range.replace(/[^\d.\-–~,\s]/g, " ").match(/\d[\d.]*/g);
  if (!nums || nums.length < 2) return null;
  const lo = parseFloat(nums[0]);
  const hi = parseFloat(nums[1]);
  if (!isFinite(lo) || !isFinite(hi)) return null;
  return lo <= hi ? [lo, hi] : [hi, lo];
}

function dirColor(dir: string | null): string {
  const d = (dir || "").toLowerCase();
  if (/bull|看涨|偏多/.test(d)) return "var(--color-bull)";
  if (/bear|看跌|偏空/.test(d)) return "var(--color-bear)";
  return "var(--color-neutral)";
}

/**
 * Floating range bars for the forecast horizons (T+1/T+5/T+20/T+60), each
 * spanning its predicted price range and colored by direction. Renders nothing
 * if the forecast markdown has no parseable ranges (best-effort).
 */
export function ScenarioChart({ forecastMd }: { forecastMd: string }) {
  const data = useMemo(() => {
    const { legs } = parseForecast(forecastMd);
    return legs
      .map((l) => {
        const r = parseRange(l.range);
        if (!r) return null;
        return {
          horizon: l.horizon,
          base: r[0],
          span: r[1] - r[0],
          lo: r[0],
          hi: r[1],
          color: dirColor(l.direction),
          direction: l.direction ?? "",
        };
      })
      .filter(Boolean) as {
      horizon: string;
      base: number;
      span: number;
      lo: number;
      hi: number;
      color: string;
      direction: string;
    }[];
  }, [forecastMd]);

  if (data.length < 2) return null;

  const lo = Math.min(...data.map((d) => d.lo));
  const hi = Math.max(...data.map((d) => d.hi));
  const pad = (hi - lo) * 0.12 || 1;

  return (
    <section
      className="animate-pop rounded-[var(--radius-card)] bg-[var(--color-surface)] p-6"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <h2 className="mb-1 text-base font-bold text-[var(--color-ink)]">
        情景区间 <span className="text-sm font-normal text-[var(--color-ink-faint)]">· 时间轴预测</span>
      </h2>
      <p className="mb-3 text-xs text-[var(--color-ink-faint)]">
        每段为该时间窗的预测价格区间，颜色表示方向（绿涨／红跌／黄中性）。
      </p>
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 14, right: 12, bottom: 0, left: -8 }}>
            <CartesianGrid stroke="var(--color-border)" vertical={false} />
            <XAxis
              dataKey="horizon"
              tick={{ fontSize: 12, fill: "var(--color-ink-soft)" }}
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
              cursor={{ fill: "var(--color-surface-2)" }}
              contentStyle={{ borderRadius: 12, border: "1px solid var(--color-border)", fontSize: 12 }}
              formatter={(_v, _n, p) => {
                const d = p?.payload as { lo: number; hi: number; direction: string };
                return [`${d.lo} – ${d.hi}`, d.direction || "区间"];
              }}
            />
            {/* transparent spacer to the range floor, then the visible range bar */}
            <Bar dataKey="base" stackId="r" fill="transparent" isAnimationActive={false} />
            <Bar dataKey="span" stackId="r" radius={[6, 6, 6, 6]} isAnimationActive={false}>
              {data.map((d, i) => (
                <Cell key={i} fill={d.color} fillOpacity={0.85} />
              ))}
              <LabelList
                dataKey="hi"
                position="top"
                style={{ fontSize: 11, fill: "var(--color-ink-soft)" }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

import { useCallback, useEffect, useRef, useState } from "react";
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
} from "lightweight-charts";
import { TrendingUp, TrendingDown } from "lucide-react";
import { api } from "../api/client";
import type { PricePoint, IntradayPoint } from "../api/types";
import { cn } from "../lib/format";
import { quoteColors, QUOTE_COLOR_CHANGE_EVENT, type QuoteColorMode } from "../lib/quoteColor";

const MA_COLORS = ["#e3b341", "#7c6bf5", "#3dd9c5"];
const MA_LABELS = ["MA5", "MA10", "MA20"];
// Beijing time offset (UTC+8) in seconds — convert UTC timestamps to local time for display.
const BEIJING_OFFSET = 8 * 3600;

export type KlineMode = "daily" | "intraday";

function withMAs<T extends { close: number }>(points: T[]): (T & { ma5?: number; ma10?: number; ma20?: number })[] {
  const ma = (i: number, w: number): number | undefined => {
    if (i + 1 < w) return undefined;
    let sum = 0;
    for (let j = i - w + 1; j <= i; j++) sum += points[j].close;
    return sum / w;
  };
  return points.map((p, i) => ({ ...p, ma5: ma(i, 5), ma10: ma(i, 10), ma20: ma(i, 20) }));
}

export function KlineChart({
  ticker,
  date,
  mode = "daily",
  refreshInterval = 0,
  onDataLoaded,
  className = "",
  chartClassName = "h-64",
}: {
  ticker: string;
  date?: string;
  mode?: KlineMode;
  refreshInterval?: number;
  onDataLoaded?: () => void;
  className?: string;
  chartClassName?: string;
}) {
  const [dailyPoints, setDailyPoints] = useState<PricePoint[] | null>(null);
  const [intradayPoints, setIntradayPoints] = useState<IntradayPoint[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [colors, setColors] = useState(quoteColors);
  const containerRef = useRef<HTMLDivElement>(null);

  // 涨跌配色切换（绿涨红跌 / 红涨绿跌）：重取色并即时应用到 K 线系列
  useEffect(() => {
    const onChange = (e: Event) => {
      setColors(quoteColors((e as CustomEvent<QuoteColorMode>).detail));
    };
    window.addEventListener(QUOTE_COLOR_CHANGE_EVENT, onChange);
    return () => window.removeEventListener(QUOTE_COLOR_CHANGE_EVENT, onChange);
  }, []);

  useEffect(() => {
    candleRef.current?.applyOptions({
      upColor: colors.up,
      downColor: colors.down,
      wickUpColor: colors.up,
      wickDownColor: colors.down,
    });
  }, [colors]);
  const chartRef = useRef<IChartApi | null>(null);
  const chartContainerRef = useRef<HTMLDivElement | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const maRefs = useRef<ISeriesApi<"Line">[]>([]);
  const onDataLoadedRef = useRef(onDataLoaded);

  useEffect(() => {
    onDataLoadedRef.current = onDataLoaded;
  }, [onDataLoaded]);

  const fetchData = useCallback(async () => {
    try {
      if (mode === "daily") {
        const r = await api.price(ticker, date, 120);
        if (r.points?.length) {
          setDailyPoints(r.points);
          onDataLoadedRef.current?.();
        } else {
          setFailed(true);
        }
      } else {
        const r = await api.intradayPrice(ticker, "5m");
        if (r.points?.length) {
          setIntradayPoints(r.points);
          onDataLoadedRef.current?.();
        } else {
          setFailed(true);
        }
      }
    } catch {
      setFailed(true);
    }
  }, [ticker, date, mode]);

  // Initial fetch
  useEffect(() => {
    setDailyPoints(null);
    setIntradayPoints(null);
    setFailed(false);
    fetchData();
  }, [fetchData]);

  // Auto-refresh polling
  useEffect(() => {
    if (!refreshInterval) return;
    const t = setInterval(fetchData, refreshInterval * 1000);
    return () => clearInterval(t);
  }, [fetchData, refreshInterval]);

  // Create chart when container is ready, update data when points change
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const raf = requestAnimationFrame(() => {
      // Container changed (e.g. ticker switch) → destroy old chart and rebuild
      if (chartContainerRef.current !== container && chartRef.current) {
        (chartRef.current as unknown as { _ro?: ResizeObserver })._ro?.disconnect();
        chartRef.current.remove();
        chartRef.current = null;
        candleRef.current = null;
        maRefs.current = [];
      }
      chartContainerRef.current = container;

      // Create chart once
      if (!chartRef.current) {
        const chart = createChart(container, {
          layout: {
            background: { color: "transparent" },
            textColor: "rgba(240,246,252,0.8)",
          },
          grid: {
            vertLines: { color: "rgba(48,54,61,0.4)" },
            horzLines: { color: "rgba(48,54,61,0.4)" },
          },
          rightPriceScale: { borderVisible: false },
          timeScale: { borderVisible: false, timeVisible: true },
          width: container.clientWidth,
          height: container.clientHeight,
        });
        chartRef.current = chart;

        candleRef.current = chart.addSeries(CandlestickSeries, {
          upColor: quoteColors().up,
          downColor: quoteColors().down,
          borderVisible: false,
          wickUpColor: quoteColors().up,
          wickDownColor: quoteColors().down,
        });

        maRefs.current = [5, 10, 20].map((_period, i) =>
          chart.addSeries(LineSeries, {
            color: MA_COLORS[i],
            lineWidth: 1,
            priceLineVisible: false,
          }),
        );

        const ro = new ResizeObserver(() => {
          chart.applyOptions({ width: container.clientWidth, height: container.clientHeight });
        });
        ro.observe(container);
        (chart as unknown as { _ro: ResizeObserver })._ro = ro;
      }

      // Update data
      if (candleRef.current) {
        if (mode === "daily" && dailyPoints?.length) {
          const data = withMAs(dailyPoints).sort((a, b) => a.date.localeCompare(b.date));
          candleRef.current.setData(
            data.map((d) => ({
              time: d.date,
              open: d.open ?? d.close,
              high: d.high ?? d.close,
              low: d.low ?? d.close,
              close: d.close,
            })),
          );
          [5, 10, 20].forEach((period, i) => {
            maRefs.current[i]?.setData(
              data
                .map((d) => ({
                  time: d.date,
                  value: period === 5 ? d.ma5 : period === 10 ? d.ma10 : d.ma20,
                }))
                .filter((d) => d.value != null),
            );
          });
          chartRef.current?.timeScale().fitContent();
        } else if (mode === "intraday" && intradayPoints?.length) {
          const data = withMAs(intradayPoints).sort((a, b) => a.time - b.time);
          // Convert UTC timestamps to Beijing time (UTC+8) for display
          const localTime = (t: number) => (t + BEIJING_OFFSET) as unknown as Parameters<ISeriesApi<"Candlestick">["setData"]>[0][number]["time"];
          candleRef.current.setData(
            data.map((d) => ({
              time: localTime(d.time),
              open: d.open ?? d.close,
              high: d.high ?? d.close,
              low: d.low ?? d.close,
              close: d.close,
            })),
          );
          [5, 10, 20].forEach((period, i) => {
            maRefs.current[i]?.setData(
              data
                .map((d) => ({
                  time: localTime(d.time),
                  value: period === 5 ? d.ma5 : period === 10 ? d.ma10 : d.ma20,
                }))
                .filter((d) => d.value != null),
            );
          });
          chartRef.current?.timeScale().fitContent();
        }
      }
    });

    return () => cancelAnimationFrame(raf);
  }, [dailyPoints, intradayPoints, mode]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (chartRef.current) {
        (chartRef.current as unknown as { _ro?: ResizeObserver })._ro?.disconnect();
        chartRef.current.remove();
        chartRef.current = null;
        chartContainerRef.current = null;
        candleRef.current = null;
        maRefs.current = [];
      }
    };
  }, []);

  const points = mode === "daily" ? dailyPoints : intradayPoints;
  if (failed) return null;
  if (!points) return <div className="skeleton h-64 w-full rounded-[var(--radius-card)]" />;

  const first = points[0].close;
  const last = points[points.length - 1].close;
  const chg = first ? ((last - first) / first) * 100 : 0;
  const up = chg >= 0;

  return (
    <section
      className={cn(
        "animate-pop rounded-[var(--radius-card)] bg-[var(--color-surface)] p-6",
        className,
      )}
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-bold text-[var(--color-ink)]">
          K 线走势 <span className="text-sm font-normal text-[var(--color-ink-faint)]">· {mode === "daily" ? `近 ${points.length} 个交易日` : "当日分时"}</span>
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
      <div ref={containerRef} className={cn("w-full", chartClassName)} />
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-[var(--color-ink-soft)]">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-3 rounded-full" style={{ background: colors.up }} /> 上涨
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-3 rounded-full" style={{ background: colors.down }} /> 下跌
        </span>
        {MA_LABELS.map((m, i) => (
          <span key={m} className="flex items-center gap-1.5">
            <span className="inline-block h-0.5 w-3.5 rounded-full" style={{ background: MA_COLORS[i] }} />
            {m}
          </span>
        ))}
      </div>
    </section>
  );
}

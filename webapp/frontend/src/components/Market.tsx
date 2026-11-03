import { useCallback, useEffect, useState } from "react";
import { Plus, X, Search, RefreshCw } from "lucide-react";
import { api } from "../api/client";
import { KlineChart, type KlineMode } from "./KlineChart";
import { cn } from "../lib/format";

const STORAGE_KEY = "dromx:watchlist";

const INDICES = [
  { ticker: "000001.SS", name: "上证指数", market: "cn" },
  { ticker: "399001.SZ", name: "深证成指", market: "cn" },
  { ticker: "399006.SZ", name: "创业板指", market: "cn" },
  { ticker: "^HSI", name: "恒生指数", market: "hk" },
  { ticker: "^HSTECH", name: "恒生科技", market: "hk" },
  { ticker: "^GSPC", name: "标普500", market: "us" },
  { ticker: "^IXIC", name: "纳斯达克", market: "us" },
  { ticker: "^DJI", name: "道琼斯", market: "us" },
] as const;

type WatchItem = { ticker: string; name?: string };

function loadWatchlist(): WatchItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveWatchlist(items: WatchItem[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    // ignore quota errors
  }
}

const REFRESH_OPTIONS = [
  { label: "10秒", value: 10 },
  { label: "30秒", value: 30 },
  { label: "1分钟", value: 60 },
] as const;

/** 大盘 / 个股 K 线页：顶部搜索 + 横排 pill，下方全宽大 K 线图。 */
export function Market() {
  const [selected, setSelected] = useState<string>(INDICES[0].ticker);
  const [query, setQuery] = useState("");
  const [watchlist, setWatchlist] = useState<WatchItem[]>(loadWatchlist);
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [summaries, setSummaries] = useState<Record<string, { close: number; change: number } | null>>({});
  const [mode, setMode] = useState<KlineMode>("daily");
  const [refreshInterval, setRefreshInterval] = useState(0);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const handleDataLoaded = useCallback(() => {
    setLastUpdated(new Date());
  }, []);

  // 拉取指数涨跌幅
  useEffect(() => {
    let alive = true;
    Promise.all(
      INDICES.map(async (idx) => {
        try {
          const r = await api.price(idx.ticker, undefined, 5);
          if (!alive) return;
          const p = r.points;
          if (p?.length >= 2) {
            const change = ((p[p.length - 1].close - p[0].close) / p[0].close) * 100;
            setSummaries((s) => ({ ...s, [idx.ticker]: { close: p[p.length - 1].close, change } }));
          }
        } catch {
          // ignore
        }
      }),
    );
    return () => {
      alive = false;
    };
  }, []);

  // 拉取自选股涨跌幅
  useEffect(() => {
    let alive = true;
    Promise.all(
      watchlist.map(async (item) => {
        try {
          const r = await api.price(item.ticker, undefined, 5);
          if (!alive) return;
          const p = r.points;
          if (p?.length >= 2) {
            const change = ((p[p.length - 1].close - p[0].close) / p[0].close) * 100;
            setSummaries((s) => ({ ...s, [item.ticker]: { close: p[p.length - 1].close, change } }));
          }
        } catch {
          // ignore
        }
      }),
    );
    return () => {
      alive = false;
    };
  }, [watchlist]);

  const addToWatchlist = async () => {
    const ticker = query.trim().toUpperCase();
    if (!ticker) return;
    if (watchlist.some((w) => w.ticker === ticker)) {
      setAddError("已在自选中");
      return;
    }
    setAddError(null);
    setAdding(true);
    try {
      const r = await api.price(ticker, undefined, 5);
      if (!r.points?.length) throw new Error("无数据");
      const items = [...watchlist, { ticker }];
      setWatchlist(items);
      saveWatchlist(items);
      setQuery("");
      setSelected(ticker);
    } catch {
      setAddError("找不到该标的，请检查代码格式（如 600519.SS / 0700.HK / NVDA）");
    } finally {
      setAdding(false);
    }
  };

  const removeFromWatchlist = (ticker: string) => {
    const items = watchlist.filter((w) => w.ticker !== ticker);
    setWatchlist(items);
    saveWatchlist(items);
    if (selected === ticker) setSelected(INDICES[0].ticker);
  };

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Top bar: search + horizontal pills */}
      <div className="shrink-0 border-b border-[var(--color-border)] bg-[var(--color-canvas)]">
        {/* Search row */}
        <div className="flex items-center gap-3 px-4 py-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              addToWatchlist();
            }}
            className="flex flex-1 items-center gap-2"
          >
            <div className="relative flex-1 max-w-md">
              <Search size={15} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-ink-faint)]" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="搜股票代码，如 600519.SS / 0700.HK / NVDA"
                aria-label="搜索股票"
                className="tnum w-full rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface)] py-2 pl-8 pr-2 text-sm text-[var(--color-ink)] outline-none transition placeholder:font-sans placeholder:text-[var(--color-ink-faint)] focus:border-[var(--color-brand)]"
              />
            </div>
            <button
              type="submit"
              disabled={adding || !query.trim()}
              className="btn-brand flex h-9 w-9 items-center justify-center rounded-[var(--radius-control)] disabled:opacity-50"
              aria-label="加入自选"
            >
              {adding ? <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" /> : <Plus size={16} />}
            </button>
          </form>
          {addError && <p className="text-xs text-[var(--color-danger)]">{addError}</p>}

          {/* mode toggle + refresh controls */}
          <div className="ml-auto flex items-center gap-2">
            {lastUpdated && (
              <span className="tnum hidden text-[11px] text-[var(--color-ink-faint)] sm:block">
                更新 {lastUpdated.toLocaleTimeString()}
              </span>
            )}

            {/* 日线 / 分时 toggle */}
            <div className="flex items-center gap-1 rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface)] p-1">
              {(["daily", "intraday"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={cn(
                    "rounded px-2.5 py-1 text-xs transition",
                    mode === m
                      ? "bg-[var(--color-brand)] text-white"
                      : "text-[var(--color-ink-soft)] hover:text-[var(--color-ink)]",
                  )}
                >
                  {m === "daily" ? "日线" : "分时"}
                </button>
              ))}
            </div>

            {/* refresh interval selector (intraday only) */}
            {mode === "intraday" && (
              <>
                <div className="flex items-center gap-1 rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface)] p-1">
                  {REFRESH_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setRefreshInterval(refreshInterval === opt.value ? 0 : opt.value)}
                      className={cn(
                        "rounded px-2.5 py-1 text-xs transition",
                        refreshInterval === opt.value
                          ? "bg-[var(--color-brand)] text-white"
                          : "text-[var(--color-ink-soft)] hover:text-[var(--color-ink)]",
                      )}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
                <button
                  onClick={() => setRefreshInterval(0)}
                  title="手动刷新"
                  className="grid h-8 w-8 place-items-center rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-ink-soft)] transition hover:text-[var(--color-ink)]"
                  aria-label="手动刷新"
                >
                  <RefreshCw size={14} />
                </button>
              </>
            )}
          </div>
        </div>

        {/* Pills row */}
        <div className="flex gap-1.5 overflow-x-auto px-4 pb-3 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {/* Watchlist pills */}
          {watchlist.map((item) => {
            const s = summaries[item.ticker];
            return (
              <div
                key={item.ticker}
                className={cn(
                  "group flex shrink-0 items-center gap-1 rounded-full border transition",
                  selected === item.ticker
                    ? "border-[var(--color-brand)]/40 bg-[var(--color-brand-tint)]"
                    : "border-[var(--color-border)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-2)]",
                )}
              >
                <button
                  onClick={() => setSelected(item.ticker)}
                  className="flex items-center gap-1.5 py-1.5 pl-3 pr-1"
                >
                  <span className="tnum text-sm font-medium text-[var(--color-ink)]">{item.ticker}</span>
                  {s ? (
                    <span
                      className={cn(
                        "text-xs tnum",
                        s.change >= 0 ? "text-[var(--color-bull)]" : "text-[var(--color-bear)]",
                      )}
                    >
                      {s.change >= 0 ? "+" : ""}
                      {s.change.toFixed(2)}%
                    </span>
                  ) : (
                    <span className="text-xs text-[var(--color-ink-faint)]">—</span>
                  )}
                </button>
                <button
                  onClick={() => removeFromWatchlist(item.ticker)}
                  className="grid h-6 w-6 place-items-center rounded-full text-[var(--color-ink-faint)] opacity-0 transition hover:bg-[var(--color-surface-2)] hover:text-[var(--color-danger)] group-hover:opacity-100"
                  aria-label={`移除 ${item.ticker}`}
                >
                  <X size={12} />
                </button>
              </div>
            );
          })}

          {/* Divider */}
          {watchlist.length > 0 && (
            <div className="mx-1 w-px shrink-0 self-stretch bg-[var(--color-border)]" />
          )}

          {/* Index pills */}
          {INDICES.map((idx) => {
            const s = summaries[idx.ticker];
            return (
              <button
                key={idx.ticker}
                onClick={() => setSelected(idx.ticker)}
                className={cn(
                  "shrink-0 rounded-full px-3 py-1.5 text-sm transition",
                  selected === idx.ticker
                    ? "bg-[var(--color-brand-tint)] text-[var(--color-brand-dark)]"
                    : "text-[var(--color-ink-soft)] hover:bg-[var(--color-surface-2)]",
                )}
              >
                {idx.name}
                {s && (
                  <span
                    className={cn(
                      "ml-1.5 text-xs tnum",
                      s.change >= 0 ? "text-[var(--color-bull)]" : "text-[var(--color-bear)]",
                    )}
                  >
                    {s.change >= 0 ? "+" : ""}
                    {s.change.toFixed(2)}%
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Chart area — full width & height */}
      <div className="flex-1 overflow-hidden px-4 py-4">
        <div className="mx-auto h-full max-w-[1400px]">
          <KlineChart
            ticker={selected}
            mode={mode}
            refreshInterval={mode === "intraday" ? refreshInterval : 0}
            onDataLoaded={handleDataLoaded}
            className="flex h-full flex-col"
            chartClassName="flex-1 min-h-[420px]"
          />
        </div>
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import {
  Search, Bell, TrendingUp, Sparkles, ArrowRight, ArrowUpRight,
  ShieldCheck, GitCompareArrows, FlaskConical, Bot, Brain,
} from "lucide-react";
import { Logo, LogoLockup } from "./Logo";
import { KlineBackground } from "./KlineBackground";
import { spotlightProps } from "../lib/useSpotlight";
import mascot from "../assets/brand/mascot.png";
import iconCandle from "../assets/brand/icon-candle.png";
import iconAiBrain from "../assets/brand/icon-ai-brain.png";
import iconGauge from "../assets/brand/icon-gauge.png";
import iconBolt from "../assets/brand/icon-bolt.png";
import iconSearch from "../assets/brand/icon-search.png";
import iconGrowth from "../assets/brand/icon-growth.png";
import shotScreener from "../assets/landing/shot-screener.png";
import shotReport from "../assets/landing/shot-report.png";
import shotMonitor from "../assets/landing/shot-monitor.png";

/**
 * Marketing landing page (route: /landing) — DromX brand identity v1.0.
 * Full dark tech theme (#0D1117 + brand emerald #10B981): grid-pattern hero
 * with the Dromy mascot, spec gradient-text slogan 让 AI 读懂每一支股票,
 * scroll-reveal motion, ticker marquee, and a tech-gradient final CTA.
 */
export function Landing({ onEnter }: { onEnter: () => void }) {
  useRevealOnScroll();

  return (
    <div className="min-h-[100dvh] overflow-x-hidden bg-[var(--color-canvas)] text-[var(--color-ink)]">
      <Nav onEnter={onEnter} />
      <Hero onEnter={onEnter} />
      <TickerMarquee />
      <Lifecycle />
      <FeatureSplit
        id="screener"
        eyebrow="选股 · Screener"
        title="声明式策略，全市场秒筛"
        body="用可组合的策略对港/美/A 全市场做筛选——涨跌幅、量比、均线、RSI、MACD、连板……命中标的一键发起深度分析。数据全免费，无需付费行情源。"
        points={["18 内置策略 + AI 生成自定义策略", "两阶段粗筛→精算，当日缓存秒开", "A 股涨停池 / 连板数原生支持"]}
        img={shotScreener}
        icon={<Search size={16} />}
      />
      <FeatureSplit
        reverse
        id="analysis"
        eyebrow="分析 · Deep Research"
        title="19 节点多智能体投研流水线"
        body="Regime 判断 → 5 位分析师并行(技术/情绪/新闻/基本面/行业)→ 信号融合 → 事件冲击 → 关键问题 → 研究经理 → 交易员 → 风险共识 → 时间轴预测 → 组合经理决策。每个结论都带数据来源。"
        points={["概率分布 + 期望值 + 凯利仓位", "T+1/5/20/60 分时预测 + 证伪条件", "ETF 自动穿透、跨品种框架分叉"]}
        img={shotReport}
        icon={<Bot size={16} />}
      />
      <FeatureSplit
        id="monitor"
        eyebrow="监控 · Monitor"
        title="规则轮询，自动告警"
        body="价格阈值、技术信号、策略选股池变化——设好规则，后端定时轮询触发，飞书 / 系统弹窗推送。盘后自动分析、定时选股扫描皆可编排。"
        points={["price / signal / strategy 三类规则", "冷却去重、告警历史留痕", "APScheduler 定时任务 + 完成即通知"]}
        img={shotMonitor}
        icon={<Bell size={16} />}
      />
      <WhyGrid />
      <FinalCta onEnter={onEnter} />
      <Footer />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────

function Nav({ onEnter }: { onEnter: () => void }) {
  return (
    <div className="sticky top-0 z-50 border-b border-[var(--color-border)] bg-[var(--color-canvas)]/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1200px] items-center justify-between px-6 py-3.5">
        <LogoLockup size={44} />
        <div className="hidden items-center gap-7 text-sm text-[var(--color-ink-soft)] md:flex">
          <a href="#lifecycle" className="transition-colors hover:text-[var(--color-brand)]">工作流</a>
          <a href="#screener" className="transition-colors hover:text-[var(--color-brand)]">选股</a>
          <a href="#analysis" className="transition-colors hover:text-[var(--color-brand)]">分析</a>
          <a href="#why" className="transition-colors hover:text-[var(--color-brand)]">为什么</a>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={onEnter} className="text-sm font-medium text-[var(--color-ink-soft)] transition-colors hover:text-[var(--color-ink)]">
            登录
          </button>
          <button
            onClick={onEnter}
            className="btn-brand group flex items-center gap-1.5 rounded-lg py-2 pl-4 pr-2 text-sm font-semibold"
          >
            进入工作台
            <span className="grid h-6 w-6 place-items-center rounded-md bg-white/20 transition group-hover:translate-x-0.5">
              <ArrowRight size={14} />
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}

function Hero({ onEnter }: { onEnter: () => void }) {
  return (
    <section className="relative overflow-hidden px-6 pt-16 pb-10 md:pt-24">
      {/* spec hero backdrop: 60px tech grid + two soft accent glows */}
      <div className="grid-pattern pointer-events-none absolute inset-0 opacity-50" />
      <div className="pointer-events-none absolute left-1/4 top-1/4 h-[560px] w-[560px] rounded-full bg-[#10b981]/[0.06] blur-[120px]" />
      <div className="pointer-events-none absolute bottom-0 right-[12%] h-[400px] w-[400px] rounded-full bg-[#10b981]/[0.05] blur-[100px]" />
      {/* faint animated candlestick texture behind the copy, masked to fade out */}
      <div
        className="pointer-events-none absolute inset-x-0 top-0 z-0 h-[560px] opacity-[0.35]"
        style={{
          maskImage: "radial-gradient(130% 100% at 50% 42%, #000 40%, transparent 86%)",
          WebkitMaskImage: "radial-gradient(130% 100% at 50% 42%, #000 40%, transparent 86%)",
        }}
      >
        <KlineBackground className="h-full w-full" />
      </div>

      <div className="relative z-10 mx-auto max-w-[1200px]">
        <div className="grid items-center gap-10 lg:grid-cols-[1.25fr_1fr]">
          <div className="text-center lg:text-left">
            {/* spec badge pill */}
            <div className="reveal mb-7 inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)]/60 px-4 py-2 backdrop-blur">
              <span className="animate-pulse-glow h-2 w-2 rounded-full bg-[var(--color-brand)]" />
              <span className="text-xs uppercase tracking-[0.18em] text-[var(--color-ink-soft)]">AI 股票投研平台</span>
            </div>
            <h1 className="reveal font-display text-[clamp(2.6rem,5.6vw,4.4rem)] font-black leading-[1.05] tracking-[-0.02em]">
              让 <span className="gradient-text">AI</span> 读懂
              <br className="hidden sm:block" />
              每一支股票
            </h1>
            <p className="reveal mx-auto mt-5 max-w-[52ch] text-lg leading-relaxed text-[var(--color-ink-soft)] lg:mx-0" style={{ transitionDelay: "120ms" }}>
              全市场选股、19 节点多智能体深度分析、规则监控告警、绩效复盘——港 / 美 / A 股全支持，全程免费数据源。
            </p>
            <p className="reveal tnum mx-auto mt-2 max-w-[52ch] text-sm text-[var(--color-ink-faint)] lg:mx-0" style={{ transitionDelay: "160ms" }}>
              AI-Powered Stock Intelligence
            </p>
            <div className="reveal mt-8 flex items-center justify-center gap-3 lg:justify-start" style={{ transitionDelay: "200ms" }}>
              <button
                onClick={onEnter}
                className="btn-brand group flex items-center gap-2 rounded-lg py-3 pl-6 pr-3 font-semibold"
              >
                免费开始使用
                <span className="grid h-7 w-7 place-items-center rounded-md bg-white/20 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5">
                  <ArrowUpRight size={16} />
                </span>
              </button>
              <a href="#lifecycle" className="btn-outline rounded-lg px-6 py-[10px] font-semibold">
                看看怎么用
              </a>
            </div>
          </div>

          {/* Dromy mascot — brand IP, floating over an accent glow */}
          <div className="reveal relative mx-auto hidden w-fit lg:block" style={{ transitionDelay: "240ms" }}>
            <div className="breathe pointer-events-none absolute left-1/2 top-1/2 h-[320px] w-[320px] rounded-full bg-[#10b981]/[0.14] blur-[80px]" />
            <div className="animate-float relative">
              <img
                src={mascot}
                alt="DromX 吉祥物 Dromy — 手持 K 线平板的小熊猫分析师"
                className="w-[300px] drop-shadow-[0_24px_48px_rgba(1,4,9,0.6)] xl:w-[340px]"
              />
            </div>
            {/* floating AI-score chip, spec tag style */}
            <div className="animate-float absolute -left-6 top-10 flex items-center gap-1.5 rounded-full border border-[var(--color-brand)]/20 bg-[var(--color-brand-tint)] px-3 py-1.5 text-xs font-bold text-[var(--color-brand-dark)] backdrop-blur" style={{ animationDelay: "0.8s" }}>
              <Brain size={13} /> AI Score 95
            </div>
            <div className="animate-float tnum absolute -right-2 bottom-16 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]/90 px-3 py-2 text-xs backdrop-blur" style={{ animationDelay: "1.6s" }}>
              <span className="text-[var(--color-ink-faint)]">NVDA</span>{" "}
              <span className="font-semibold text-[var(--color-brand)]">+3.28%</span>
            </div>
          </div>
        </div>

        {/* floating hero screenshot — gentle bob (outer) + cursor parallax tilt (inner) */}
        <div className="reveal mt-16" style={{ transitionDelay: "300ms" }}>
          <div className="float-slow mx-auto max-w-[1080px]">
            <TiltCard>
              <img src={shotReport} alt="DromX 分析报告界面" className="w-full" />
            </TiltCard>
          </div>
        </div>
      </div>
    </section>
  );
}

/** Subtle 3D tilt that follows the cursor (max ~3°, spring back on leave). */
function TiltCard({ children }: { children: React.ReactNode }) {
  const [t, setT] = useState({ rx: 0, ry: 0 });
  const reduce =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  return (
    <div
      className="glow-green overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] transition-transform duration-300 ease-out will-change-transform"
      style={{
        boxShadow: "0 0 0 1px var(--color-border), 0 40px 80px -20px rgba(1,4,9,0.7), 0 0 60px rgba(16,185,129,0.08)",
        transform: `perspective(1400px) rotateX(${t.rx}deg) rotateY(${t.ry}deg)`,
      }}
      onMouseMove={(e) => {
        if (reduce) return;
        const r = e.currentTarget.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width - 0.5;
        const py = (e.clientY - r.top) / r.height - 0.5;
        setT({ rx: -py * 3, ry: px * 3.5 });
      }}
      onMouseLeave={() => setT({ rx: 0, ry: 0 })}
    >
      {children}
    </div>
  );
}

const TICKERS = [
  "NVDA", "腾讯 00700", "贵州茅台 600519", "MU", "SK海力士 07709", "AAPL",
  "宁德时代 300750", "TSLA", "美团 03690", "比亚迪 002594", "AMD", "中芯国际 00981",
];
function TickerMarquee() {
  const item = (t: string, i: number) => (
    <span key={i} className="tnum flex items-center gap-2 whitespace-nowrap text-sm text-[var(--color-ink-faint)]">
      <span className="h-1 w-1 rounded-full bg-[var(--color-brand)]" /> {t}
    </span>
  );
  return (
    <section className="border-y border-[var(--color-border)] bg-[var(--color-surface)] py-4">
      <div className="mx-auto max-w-[1200px] overflow-hidden px-6">
        <div className="flex w-max marquee gap-8">
          <span className="flex items-center gap-8">{TICKERS.map(item)}</span>
          {/* duplicate half for the seamless -50% loop — hidden from AT */}
          <span className="flex items-center gap-8" aria-hidden="true">{TICKERS.map(item)}</span>
        </div>
      </div>
    </section>
  );
}

const STEPS = [
  { n: "01", icon: <Search size={18} />, title: "选股", body: "策略全市场筛选，命中标的进入分析池。" },
  { n: "02", icon: <Bot size={18} />, title: "分析", body: "19 节点多智能体深度投研，出结构化决策。" },
  { n: "03", icon: <Bell size={18} />, title: "监控", body: "规则轮询触发告警，飞书 / 系统实时推送。" },
  { n: "04", icon: <TrendingUp size={18} />, title: "复盘", body: "按真实行情打分，持续改进决策权重。" },
];
function Lifecycle() {
  return (
    <section id="lifecycle" className="mx-auto max-w-[1200px] px-6 py-24">
      <SectionHead eyebrow="全生命周期" title="选股 → 分析 → 监控 → 复盘" />
      <div className="mt-12 grid gap-4 md:grid-cols-4">
        {STEPS.map((s, i) => (
          <div key={s.n} {...spotlightProps()} className="spotlight reveal group rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 transition-all duration-200 hover:-translate-y-1 hover:border-[var(--color-brand)]/40" style={{ transitionDelay: `${i * 80}ms` }}>
            <div className="flex items-center justify-between">
              <span className="grid h-9 w-9 place-items-center rounded-lg bg-[var(--color-brand-tint)] text-[var(--color-brand-dark)]">{s.icon}</span>
              <span className="tnum text-2xl font-semibold text-[var(--color-border-strong)]">{s.n}</span>
            </div>
            <div className="mt-4 text-lg font-semibold">{s.title}</div>
            <p className="mt-1 text-sm leading-relaxed text-[var(--color-ink-soft)]">{s.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function FeatureSplit({ id, eyebrow, title, body, points, img, icon, reverse }: {
  id: string; eyebrow: string; title: string; body: string; points: string[];
  img: string; icon: React.ReactNode; reverse?: boolean;
}) {
  return (
    <section id={id} className="mx-auto max-w-[1200px] px-6 py-16 md:py-24">
      <div className={`grid items-center gap-12 md:grid-cols-2 ${reverse ? "md:[&>*:first-child]:order-2" : ""}`}>
        <div className="reveal">
          <span className="inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1 text-xs font-medium text-[var(--color-brand-dark)]">
            {icon} {eyebrow}
          </span>
          <h2 className="font-display mt-4 text-[clamp(1.9rem,3.4vw,2.9rem)] font-bold leading-[1.1] tracking-[-0.01em]">{title}</h2>
          <p className="mt-4 max-w-[46ch] leading-relaxed text-[var(--color-ink-soft)]">{body}</p>
          <ul className="mt-6 space-y-2.5">
            {points.map((p) => (
              <li key={p} className="flex items-start gap-2.5 text-sm text-[var(--color-ink)]">
                <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-[var(--color-brand-tint)] text-[var(--color-brand-dark)]">
                  <Sparkles size={11} />
                </span>
                {p}
              </li>
            ))}
          </ul>
        </div>
        <div className="reveal" style={{ transitionDelay: "120ms" }}>
          <div className="overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]" style={{ boxShadow: "0 0 0 1px var(--color-border), 0 30px 60px -24px rgba(1,4,9,0.7)" }}>
            <img src={img} alt={title} className="w-full" />
          </div>
        </div>
      </div>
    </section>
  );
}

/* Why-grid chips use the brand icon set (scripts/reference_ui/icons.svg),
   cropped into tiles — the white app-icon look pops on the dark surface. */
const WHY = [
  { img: iconBolt, title: "全程免费数据源", body: "东财 / 腾讯 / mootdx / yfinance 多供应商路由，无需付费行情 key。" },
  { img: iconCandle, title: "带来源的结论", body: "每个价格、涨幅、目标价都注明计算来源与起止，拒绝幻觉数字。" },
  { img: iconSearch, title: "风险优先", body: "统一止损框架、凯利仓位、尾部风险专家，先算亏多少再算赚多少。" },
  { img: iconGrowth, title: "组合视角", body: "跨品种相关性、因子暴露、集中度——不孤立看单票。" },
  { img: iconGauge, title: "可回测可复盘", body: "历史逐日重跑 AI 决策，按真实行情打分，持续改进权重。" },
  { img: iconAiBrain, title: "港 / 美 / A 股", body: "一套系统三大市场，ETF 自动穿透、A 股涨停连板原生支持。" },
];
function WhyGrid() {
  return (
    <section id="why" className="mx-auto max-w-[1200px] px-6 py-24">
      <SectionHead eyebrow="为什么是 DromX" title="不只是能跑，而是投得对" />
      <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {WHY.map((w, i) => (
          <div key={w.title} {...spotlightProps()} className="spotlight reveal rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 transition-all duration-200 hover:-translate-y-1 hover:border-[var(--color-brand)]/40" style={{ transitionDelay: `${(i % 3) * 80}ms` }}>
            <img src={w.img} alt="" className="h-11 w-11 rounded-[10px] shadow-[0_4px_12px_rgba(1,4,9,0.5)]" />
            <div className="mt-4 font-semibold">{w.title}</div>
            <p className="mt-1.5 text-sm leading-relaxed text-[var(--color-ink-soft)]">{w.body}</p>
          </div>
        ))}
      </div>
      {/* risk / compare / backtest mini-features, spec tag style */}
      <div className="reveal mt-8 flex flex-wrap items-center justify-center gap-3" style={{ transitionDelay: "160ms" }}>
        {[
          { icon: <ShieldCheck size={14} />, t: "统一止损框架" },
          { icon: <GitCompareArrows size={14} />, t: "跨品种相关性" },
          { icon: <FlaskConical size={14} />, t: "历史逐日回测" },
        ].map((x) => (
          <span key={x.t} className="inline-flex items-center gap-1.5 rounded-md border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-1.5 text-sm text-[var(--color-ink-soft)]">
            <span className="text-[var(--color-brand)]">{x.icon}</span> {x.t}
          </span>
        ))}
      </div>
    </section>
  );
}

function FinalCta({ onEnter }: { onEnter: () => void }) {
  return (
    <section className="mx-auto max-w-[1200px] px-6 pb-24">
      <div className="reveal relative overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] px-8 py-20 text-center">
        {/* spec slogan section: tech-gradient at 40% over the dark surface */}
        <div className="tech-gradient animate-gradient pointer-events-none absolute inset-0 opacity-40" />
        <div className="grid-pattern pointer-events-none absolute inset-0 opacity-30" />
        {/* decorative pulsing dots (spec slogan section) */}
        <div className="animate-pulse-glow pointer-events-none absolute left-[12%] top-[18%] h-2 w-2 rounded-full bg-[var(--color-brand)]" />
        <div className="animate-pulse-glow pointer-events-none absolute right-[16%] top-[36%] h-1.5 w-1.5 rounded-full bg-[var(--color-brand)]/60" style={{ animationDelay: "1s" }} />
        <div className="animate-pulse-glow pointer-events-none absolute bottom-[24%] left-[30%] h-1 w-1 rounded-full bg-[var(--color-brand)]/40" style={{ animationDelay: "2s" }} />
        <div className="relative">
          <img src={mascot} alt="" className="animate-float mx-auto mb-6 w-24 drop-shadow-[0_12px_32px_rgba(1,4,9,0.6)]" />
          <h2 className="font-display mx-auto max-w-[20ch] text-[clamp(2rem,4vw,3.2rem)] font-black leading-[1.08] tracking-[-0.01em]">
            现在就开始你的 <span className="gradient-text">AI 投研</span>
          </h2>
          <p className="mx-auto mt-4 max-w-[44ch] text-[var(--color-ink-soft)]">
            无需配置付费数据、无需部署门槛，打开即用。
          </p>
          <button
            onClick={onEnter}
            className="btn-brand group mt-8 inline-flex items-center gap-2 rounded-lg py-3.5 pl-7 pr-3 text-lg font-semibold"
          >
            进入工作台
            <span className="grid h-8 w-8 place-items-center rounded-md bg-white/20 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5">
              <ArrowUpRight size={18} />
            </span>
          </button>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-[var(--color-border)]">
      <div className="mx-auto flex max-w-[1200px] flex-col items-center justify-between gap-4 px-6 py-8 text-sm text-[var(--color-ink-faint)] sm:flex-row">
        <div className="flex items-center gap-2">
          <Logo size={22} className="rounded-md" />
          <span className="font-semibold text-[var(--color-ink-soft)]">DromX</span>
          <span className="text-xs">AI 股票投研平台</span>
        </div>
        <span>让 AI 读懂每一支股票 · 港/美/A 股 · 全免费数据源</span>
      </div>
    </footer>
  );
}

function SectionHead({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div className="reveal text-center">
      <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-brand-dark)]">{eyebrow}</span>
      <h2 className="font-display mx-auto mt-3 max-w-[20ch] text-[clamp(1.9rem,3.6vw,3rem)] font-bold leading-[1.1] tracking-[-0.01em]">{title}</h2>
    </div>
  );
}

// IntersectionObserver-driven scroll reveal for all .reveal elements.
function useRevealOnScroll() {
  useEffect(() => {
    const els = Array.from(document.querySelectorAll<HTMLElement>(".reveal"));
    // Fallback: no IntersectionObserver → just show everything.
    if (typeof IntersectionObserver === "undefined") {
      els.forEach((el) => el.classList.add("is-in"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.classList.add("is-in");
            io.unobserve(e.target);
          }
        }
      },
      { threshold: 0.1, rootMargin: "0px 0px -8% 0px" },
    );
    els.forEach((el) => io.observe(el));
    // Safety net: if anything is still hidden shortly after mount (e.g. observer
    // never fired for above-the-fold items), reveal it so the page is never blank.
    const t = window.setTimeout(() => {
      els.forEach((el) => {
        const r = el.getBoundingClientRect();
        if (r.top < window.innerHeight) el.classList.add("is-in");
      });
    }, 400);
    return () => {
      io.disconnect();
      window.clearTimeout(t);
    };
  }, []);
}

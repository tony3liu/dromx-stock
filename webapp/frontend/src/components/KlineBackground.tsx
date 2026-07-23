import { useEffect, useRef } from "react";

/**
 * Professional candlestick backdrop for the hero — modeled on a real trading
 * chart: thin evenly-spaced candles with wicks, three smooth moving-average
 * overlays (MA5/MA10/MA20), and a volume histogram along the bottom. A gently
 * trending random walk (trend + noise, not pure jitter) scrolls right-to-left.
 * Rendered faint via the parent's opacity+mask so it reads as texture, not a
 * foreground chart. GPU-light single canvas; pauses under reduced-motion.
 */
export function KlineBackground({ className = "" }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const CANDLE_W = 6;
    const GAP = 4;
    const STEP = CANDLE_W + GAP;
    const VOL_FRAC = 0.18;   // bottom fraction reserved for volume bars
    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    let w = 0, h = 0;

    type Bar = { o: number; c: number; hi: number; lo: number; vol: number };
    const bars: Bar[] = [];
    let phase = 0;
    let last = 0.5;

    // Multi-sine baseline → a price series that keeps swinging (trend runs +
    // pullbacks) instead of flattening like a plain random walk. Range ≈ 0.08–0.92.
    function basePrice(p: number): number {
      return 0.5
        + 0.24 * Math.sin(p * 0.045)
        + 0.13 * Math.sin(p * 0.017 + 2.1)
        + 0.06 * Math.sin(p * 0.11 + 0.7);
    }

    function genBar(): Bar {
      phase += 1;
      const o = last;
      let c = basePrice(phase) + (Math.random() - 0.5) * 0.035;
      c = Math.min(0.94, Math.max(0.06, c));
      const bodyHi = Math.max(o, c);
      const bodyLo = Math.min(o, c);
      const hi = Math.min(0.99, bodyHi + Math.random() * 0.03);
      const lo = Math.max(0.01, bodyLo - Math.random() * 0.03);
      // volume tracks candle range so bars have rhythm
      const vol = 0.28 + Math.abs(c - o) * 9 + Math.random() * 0.35;
      last = c;
      return { o, c, hi, lo, vol: Math.min(1, vol) };
    }

    // simple trailing moving average over the `c` series
    function ma(period: number, endIdx: number): number | null {
      if (endIdx < period - 1) return null;
      let s = 0;
      for (let k = 0; k < period; k++) s += bars[endIdx - k].c;
      return s / period;
    }

    function resize() {
      const rect = canvas!.getBoundingClientRect();
      w = rect.width; h = rect.height;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas!.width = Math.floor(w * dpr);
      canvas!.height = Math.floor(h * dpr);
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      const need = Math.ceil(w / STEP) + 24; // extra history so MAs are defined
      while (bars.length < need) bars.push(genBar());
      while (bars.length > need + 4) bars.shift();
    }
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const priceH = () => h * (1 - VOL_FRAC);
    const yOf = (v: number) => priceH() * 0.08 + (1 - v) * priceH() * 0.84;
    const UP = "rgba(16,185,129,0.9)";
    const DOWN = "rgba(248,81,73,0.85)";
    const MA = ["rgba(96,165,250,0.85)", "rgba(240,180,41,0.85)", "rgba(124,107,245,0.8)"];
    const MA_PERIODS = [5, 10, 20];
    // grid lines tuned for the dark canvas (spec border at low alpha)
    const GRID = "rgba(48,54,61,0.5)";

    let offset = 0;
    let acc = 0, lastT = 0;

    function draw() {
      ctx!.clearRect(0, 0, w, h);

      // horizontal gridlines across the price area
      ctx!.strokeStyle = GRID;
      ctx!.lineWidth = 1;
      for (let g = 0; g <= 4; g++) {
        const y = (priceH() * g) / 4;
        ctx!.beginPath(); ctx!.moveTo(0, y); ctx!.lineTo(w, y); ctx!.stroke();
      }

      // candles + volume
      for (let i = 0; i < bars.length; i++) {
        const bd = bars[i];
        const x = i * STEP - offset;
        if (x < -STEP || x > w + STEP) continue;
        const up = bd.c >= bd.o;
        const col = up ? UP : DOWN;
        ctx!.strokeStyle = col;
        ctx!.fillStyle = col;
        // wick
        ctx!.lineWidth = 1;
        ctx!.beginPath();
        ctx!.moveTo(x + CANDLE_W / 2, yOf(bd.hi));
        ctx!.lineTo(x + CANDLE_W / 2, yOf(bd.lo));
        ctx!.stroke();
        // body
        const yo = yOf(bd.o), yc = yOf(bd.c);
        ctx!.fillRect(x, Math.min(yo, yc), CANDLE_W, Math.max(1.5, Math.abs(yc - yo)));
        // volume bar
        const vh = bd.vol * (h * VOL_FRAC * 0.8);
        ctx!.globalAlpha = 0.55;
        ctx!.fillRect(x, h - vh, CANDLE_W, vh);
        ctx!.globalAlpha = 1;
      }

      // moving-average overlays
      for (let m = 0; m < MA_PERIODS.length; m++) {
        ctx!.strokeStyle = MA[m];
        ctx!.lineWidth = 1.5;
        ctx!.beginPath();
        let started = false;
        for (let i = 0; i < bars.length; i++) {
          const v = ma(MA_PERIODS[m], i);
          if (v == null) continue;
          const x = i * STEP - offset + CANDLE_W / 2;
          const y = yOf(v);
          if (!started) { ctx!.moveTo(x, y); started = true; }
          else ctx!.lineTo(x, y);
        }
        ctx!.stroke();
      }
    }

    let raf = 0;
    const SPEED = 22; // px/sec
    function frame(t: number) {
      raf = requestAnimationFrame(frame);
      if (!lastT) lastT = t;
      const dt = Math.min(0.05, (t - lastT) / 1000);
      lastT = t;
      acc += dt;
      if (acc < 1 / 30) return;
      acc = 0;
      offset += SPEED * (1 / 30);
      while (offset >= STEP) {
        offset -= STEP;
        bars.push(genBar());
        bars.shift();
      }
      draw();
    }

    if (reduce) draw();
    else raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, []);

  return <canvas ref={ref} className={className} aria-hidden="true" />;
}

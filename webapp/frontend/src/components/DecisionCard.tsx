import { TrendingUp, Shield, Target, Clock } from "lucide-react";
import { parseDecision } from "../lib/parse";
import { cn, dirClasses, ratingCn, ratingDir } from "../lib/format";
import type { Dir } from "../lib/format";
import { Mascot } from "./Mascot";
import { decisionPose } from "../lib/mascot";

/** Hero decision card: a full-bleed directional gradient band carrying the
 *  verdict as display type, then the executive summary and the key numbers.
 *  This is the single most important surface in the product — it should read
 *  like a verdict, not a form row. */
export function DecisionCard({ decisionMd, rating }: { decisionMd: string; rating?: string | null }) {
  const d = parseDecision(decisionMd);
  // Prefer the markdown's own Rating field; fall back to the backend's parsed
  // rating (parse_rating over the whole decision) so the badge is never empty.
  const effectiveRating = d.rating ?? rating ?? null;
  const dir = ratingDir(effectiveRating);
  const accent = dirClasses[dir];
  const hero = HERO[dir];

  const stats = [
    { icon: Target, label: "目标价", value: d.priceTarget },
    { icon: Shield, label: "止损", value: d.stop },
    { icon: TrendingUp, label: "仓位", value: d.sizing },
    { icon: Clock, label: "周期", value: d.horizon },
  ].filter((s) => s.value);

  const verdictCn = ratingCn(effectiveRating);
  // Show the raw (usually English) rating as a small-caps subtitle when it
  // adds information beyond the Chinese verdict.
  const verdictRaw =
    effectiveRating && /[a-zA-Z]/.test(effectiveRating) && effectiveRating !== verdictCn
      ? effectiveRating.split("·")[0].trim()
      : null;

  return (
    <div
      className="animate-pop overflow-hidden rounded-[var(--radius-card)] bg-[var(--color-surface)]"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      {/* verdict band — directional gradient + mascot reaction */}
      <div
        className="relative overflow-hidden px-6 pb-6 pt-5"
        style={{ background: `linear-gradient(165deg, ${hero.tint} 0%, var(--color-surface) 82%)` }}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-ink-soft)]">
              最终决策
            </div>
            <div className={cn("mt-2.5 text-[38px] font-bold leading-none tracking-tight", accent.text)}>
              {verdictCn}
            </div>
            {verdictRaw && (
              <div className="tnum mt-2 text-[11px] font-medium uppercase tracking-[0.22em] text-[var(--color-ink-faint)]">
                {verdictRaw}
              </div>
            )}
          </div>
          <Mascot
            pose={decisionPose(effectiveRating)}
            animation="float"
            size={72}
            className="shrink-0"
          />
        </div>
      </div>

      <div className="px-6 py-5">
        {d.executiveSummary && (
          <p className="text-[14px] leading-relaxed text-[var(--color-ink)]">{d.executiveSummary}</p>
        )}

        {stats.length > 0 && (
          <div className="mt-5 grid grid-cols-2 gap-2.5">
            {stats.map((s) => (
              <div
                key={s.label}
                className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-2)] px-4 py-3"
              >
                <div className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-[var(--color-ink-faint)]">
                  <s.icon size={12} /> {s.label}
                </div>
                <div className="tnum mt-1.5 text-[22px] font-semibold leading-tight text-[var(--color-ink)]">
                  {s.value}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const HERO: Record<Dir, { tint: string }> = {
  bull: { tint: "var(--color-brand-tint)" },
  bear: { tint: "var(--color-bear-tint)" },
  neutral: { tint: "var(--color-warn-tint)" },
};

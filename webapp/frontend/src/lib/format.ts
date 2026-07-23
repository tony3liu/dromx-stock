// Rating → color/label helpers, shared across badges and cards.

export type Dir = "bull" | "bear" | "neutral";

const RATING_DIR: Record<string, Dir> = {
  buy: "bull",
  overweight: "bull",
  hold: "neutral",
  underweight: "bear",
  sell: "bear",
};

const RATING_CN: Record<string, string> = {
  buy: "买入",
  overweight: "增持",
  hold: "持有",
  underweight: "减持",
  sell: "卖出",
};

export function ratingDir(rating?: string | null): Dir {
  if (!rating) return "neutral";
  return RATING_DIR[rating.trim().toLowerCase()] ?? "neutral";
}

export function ratingCn(rating?: string | null): string {
  if (!rating) return "—";
  return RATING_CN[rating.trim().toLowerCase()] ?? rating;
}

export const dirClasses: Record<Dir, { text: string; bg: string; ring: string }> = {
  bull: { text: "text-[var(--color-bull)]", bg: "bg-[var(--color-brand-tint)]", ring: "ring-[var(--color-bull)]/30" },
  bear: { text: "text-[var(--color-bear)]", bg: "bg-[var(--color-bear-tint)]", ring: "ring-[var(--color-bear)]/30" },
  neutral: { text: "text-[var(--color-warn)]", bg: "bg-[var(--color-warn-tint)]", ring: "ring-[var(--color-neutral)]/30" },
};

export function cn(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

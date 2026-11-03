import { cn, dirClasses, ratingCn, ratingDir } from "../lib/format";

/** Rating pill, coloured by direction (buy/overweight green, hold amber, sell red). */
export function RatingBadge({
  rating,
  size = "md",
}: {
  rating?: string | null;
  size?: "sm" | "md" | "lg";
}) {
  const dir = ratingDir(rating);
  const c = dirClasses[dir];
  const sz =
    size === "lg"
      ? "text-base px-4 py-1.5"
      : size === "sm"
        ? "text-xs px-2 py-0.5"
        : "text-sm px-3 py-1";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-semibold ring-1",
        c.bg,
        c.text,
        c.ring,
        sz,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", `bg-current`)} />
      {rating ? `${rating} · ${ratingCn(rating)}` : "—"}
    </span>
  );
}

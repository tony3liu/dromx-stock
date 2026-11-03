import type { InputHTMLAttributes } from "react";
import { cn } from "../../lib/format";

/** Shared text input styling. `tone` picks the resting background:
 *  - surface: page-level forms on cards (default)
 *  - inset:   sits on a tinted surface, lifts to surface on focus
 *  - white:   sits inside a tinted container that is already surface-2
 *  `size` md = compact table/form density, lg = roomier marketing/forms. */
export function Input({
  tone = "surface",
  size = "md",
  fullWidth = true,
  className,
  ...rest
}: {
  tone?: "surface" | "inset" | "white";
  size?: "md" | "lg";
  fullWidth?: boolean;
} & Omit<InputHTMLAttributes<HTMLInputElement>, "size">) {
  return (
    <input
      className={cn(
        "rounded-[var(--radius-control)] border border-[var(--color-border)] text-[var(--color-ink)] outline-none transition focus:border-[var(--color-brand)]",
        fullWidth && "w-full",
        size === "lg" ? "px-3.5 py-2.5" : "px-3 py-2 text-sm",
        tone === "inset"
          ? "bg-[var(--color-surface-2)] focus:bg-[var(--color-surface)]"
          : tone === "white"
            ? "bg-[var(--color-surface)]"
            : "bg-[var(--color-surface)]",
        className,
      )}
      {...rest}
    />
  );
}

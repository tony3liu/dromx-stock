import type { CSSProperties, HTMLAttributes, ReactNode } from "react";
import { cn } from "../../lib/format";

/** Standard surface card: card radius + surface bg + the hairline card shadow
 *  (which itself carries the 1px border ring). Replaces the repeated
 *  `rounded-[var(--radius-card)] bg-[var(--color-surface)]` + shadow-card combo. */
export function Card({
  className,
  style,
  children,
  ...rest
}: {
  className?: string;
  style?: CSSProperties;
  children?: ReactNode;
} & HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-[var(--radius-card)] bg-[var(--color-surface)]", className)}
      style={{ boxShadow: "var(--shadow-card)", ...style }}
      {...rest}
    >
      {children}
    </div>
  );
}

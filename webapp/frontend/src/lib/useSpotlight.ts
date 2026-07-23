import type { MouseEvent } from "react";

/**
 * Cursor-tracking props for the .spotlight card effect: writes --mx/--my CSS
 * vars so the ::before radial glow follows the pointer. Spread onto any
 * element that also has className "spotlight".
 */
export function spotlightProps() {
  return {
    onMouseMove: (e: MouseEvent<HTMLElement>) => {
      const r = e.currentTarget.getBoundingClientRect();
      e.currentTarget.style.setProperty("--mx", `${e.clientX - r.left}px`);
      e.currentTarget.style.setProperty("--my", `${e.clientY - r.top}px`);
    },
  };
}

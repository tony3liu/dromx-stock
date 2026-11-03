// Shared recharts tooltip styling so every chart in the app renders the same
// hover card (radius + hairline border + font size on the design tokens).
export const TOOLTIP_CONTENT_STYLE = {
  borderRadius: 12,
  border: "1px solid var(--color-border)",
  fontSize: 12,
} as const;

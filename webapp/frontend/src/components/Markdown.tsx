import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Provenance display. Engine reports carry several provenance markers, of very
// uneven value to a reader. We normalise them by KIND:
//   - `Link: <url>` lines (incl. the deterministic 参考来源 appendix the news
//     node appends) → a green, clickable "查看原文 ↗" link.
//   - `【来源：…URL…】` / `【StockTwits · 2026-06-24】` (with OR without the
//     来源： prefix) → URL ones become a green link; the rest a quiet grey label.
//   - `【来源：技术快照 / 情绪 / 新闻标题 / 数据块 …】` → DROPPED. These are
//     generic placeholders or hang off nearly every number — pure noise.
//   - `[data]` / `[knowledge]` (and 【…】 variants) meta-tags the industry
//     analyst emits per claim → DROPPED. Honesty discipline for the model, but
//     clutter for the reader.

const DATA_TAG_HREF = "#__data__:";
const URL_RE = /(https?:\/\/\S+)/;
// 【来源：X】 whose X is a generic placeholder or per-number snapshot → drop.
const NOISE_SOURCE_RE = /技术快照|情绪|新闻标题|数据块|内部数据|快照|价格数据/;
// Per-claim honesty meta-tags like [data] / [knowledge] / 【knowledge】 → drop.
const META_TAG_RE = /\s*[[【]\s*(?:data|knowledge)\s*[\]】]/gi;
// A 【…】 is a citation when it either starts with 来源： or looks like a
// "<source> · <date>" attribution (carries the ` · ` middot). This catches both
// 【来源：StockTwits · 2026-06-24】 and the prefix-less 【StockTwits · 2026-06-24】,
// while leaving non-citation brackets like 【23%】 untouched.
const CITATION_TAG_RE = /[ \t]*【\s*(?:来源[：:]\s*)?([^】]+)】/g;
const IS_CITATION_BODY = /来源|·|\bhttps?:\/\//;

/** Rewrite provenance markers into link syntax we intercept in the `a` renderer. */
function enhanceMarkdown(md: string): string {
  let out = md;

  // `Link: https://…` (start of line, optional indent) → a labelled link.
  out = out.replace(
    /^[ \t]*Link:\s*(https?:\/\/\S+)\s*$/gim,
    (_m, url) => `[查看原文 ↗](${url})`,
  );

  // Drop [data] / [knowledge] meta-tags (won't touch markdown links, which are
  // never literally "[data](url)").
  out = out.replace(META_TAG_RE, "");

  // Normalise citation tags (with or without the 来源： prefix).
  out = out.replace(CITATION_TAG_RE, (whole, content) => {
    const raw = String(content).trim();

    // Only treat it as a citation if it had the 来源： prefix (captured already)
    // OR the body looks like an attribution (has a middot / URL). Otherwise it's
    // an ordinary 【…】 (e.g. 【23%】) — leave it as-is.
    const hadPrefix = /【\s*来源[：:]/.test(whole);
    if (!hadPrefix && !IS_CITATION_BODY.test(raw)) return whole;

    // Carries a real URL → green clickable link.
    const url = raw.match(URL_RE)?.[1];
    if (url) {
      const label = raw.replace(URL_RE, "").replace(/[·\s|—-]+$/, "").trim() || "查看原文";
      return ` [${label} ↗](${url})`;
    }

    // Generic placeholder / per-number snapshot → drop entirely.
    if (NOISE_SOURCE_RE.test(raw)) return "";

    // Real publisher / filing → quiet grey label (encoded into a sentinel href).
    const label = raw.replace(/[[\]]/g, "");
    return `[${label}](${DATA_TAG_HREF}${encodeURIComponent(raw)})`;
  });

  return out;
}

/** A quiet, non-clickable grey label for a real-but-unlinkable source. */
function DataTag({ text }: { text: string }) {
  return (
    <span className="mx-0.5 inline-flex items-center rounded bg-[var(--color-surface-2)] px-1 align-baseline text-[0.7em] font-normal text-[var(--color-ink-faint)]">
      {text}
    </span>
  );
}

/** External source link → opens in a new tab, styled as a subtle green pill. */
function SourceLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-0.5 rounded-md bg-[var(--color-surface-2)] px-1.5 py-px text-[0.8em] font-medium text-[var(--color-brand-dark)] no-underline transition-colors hover:bg-[var(--color-brand-tint)]"
    >
      {children}
    </a>
  );
}

/** Renders engine markdown report sections with the app's .md typography,
 *  rendering provenance markers by kind (external link vs internal data label). */
export function Markdown({ children }: { children: string }) {
  const enhanced = useMemo(() => enhanceMarkdown(children), [children]);
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ href, children }) {
            if (href && href.startsWith(DATA_TAG_HREF)) {
              return <DataTag text={decodeURIComponent(href.slice(DATA_TAG_HREF.length))} />;
            }
            return <SourceLink href={href ?? "#"}>{children}</SourceLink>;
          },
        }}
      >
        {enhanced}
      </ReactMarkdown>
    </div>
  );
}

import { useMemo, useState } from "react";
import { Users } from "lucide-react";
import type React from "react";
import type { AppContent, Locale } from "../i18n/content";
import type { Swarm } from "../data/swarms";

type SwarmCenterPageProps = {
  locale: Locale;
  nav: React.ReactNode;
  swarms: Swarm[];
  t: AppContent;
  onUseSwarm: () => void;
};

function SwarmCenterPage({ locale, nav, swarms, t, onUseSwarm }: SwarmCenterPageProps) {
  const sx = t.swarmsCenter;
  const [searchTerm, setSearchTerm] = useState("");

  const totalAgents = useMemo(
    () => new Set(swarms.flatMap((s) => s.agentNames)).size,
    [swarms]
  );

  const visible = useMemo(() => {
    if (!searchTerm.trim()) return swarms;
    const needle = searchTerm.toLowerCase();
    return swarms.filter((s) =>
      [s.name, s.description, ...s.agentNames].some((v) =>
        v.toLowerCase().includes(needle)
      )
    );
  }, [swarms, searchTerm]);

  return (
    <main className="console-shell skills-shell" lang={locale}>
      {nav}
      <section className="skills-workbench">
        <div className="skills-header" style={{ marginBottom: "20px" }}>
          <span className="section-label">{sx.eyebrow}</span>
          <h1>{sx.title}</h1>
          <p>{sx.description}</p>
        </div>

        <div className="skills-summary skills-summary-strip">
          <span>{sx.swarmCount(swarms.length)}</span>
          <span>{sx.agentCount(totalAgents)}</span>
        </div>

        <div className="skills-toolbar">
          <div className="store-search-wrap" style={{ flex: 1 }}>
            <input
              className="store-search-input"
              aria-label={sx.searchPlaceholder}
              placeholder={sx.searchPlaceholder}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>

        <section className="console-section" aria-label={sx.title}>
          {visible.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)", border: "1px dashed var(--border-color)", borderRadius: "8px" }}>
              {sx.emptyState}
            </div>
          ) : (
            <div className="agent-registry" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "14px" }}>
              {visible.map((swarm) => (
                <article key={swarm.id} className="role-card agent-card">
                  <div className="role-top">
                    <div>
                      <h2>{swarm.name}</h2>
                      <span style={{ fontSize: "12px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
                        <Users size={12} />
                        {swarm.agentNames.length} {sx.agents}
                      </span>
                    </div>
                  </div>
                  {swarm.description ? (
                    <p style={{ fontSize: "13px", color: "var(--text-muted)", lineHeight: 1.4 }}>{swarm.description}</p>
                  ) : (
                    <p style={{ fontSize: "13px", color: "var(--text-muted)", fontStyle: "italic", lineHeight: 1.4 }}>
                      {locale === "en" ? "No description" : "无描述"}
                    </p>
                  )}
                  <div className="role-skills">
                    {swarm.agentNames.slice(0, 4).map((name) => (
                      <span key={name} className="summary-chip" style={{ fontSize: "11px" }}>
                        {name}
                      </span>
                    ))}
                    {swarm.agentNames.length > 4 && (
                      <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                        +{swarm.agentNames.length - 4}
                      </span>
                    )}
                  </div>
                  <div className="agent-actions" style={{ marginTop: "8px" }}>
                    <button
                      className="console-action is-primary agent-action-main"
                      type="button"
                      onClick={onUseSwarm}
                    >
                      {sx.useSwarm}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

export default SwarmCenterPage;

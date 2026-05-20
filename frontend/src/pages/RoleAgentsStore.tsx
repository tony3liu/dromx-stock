import { useMemo, useState } from "react";
import type { AppContent, Locale, StoreAgent } from "../i18n/content";

type StoreFilter = "all" | "free" | "paid" | "purchased";

type RoleAgentsStoreProps = {
  locale: Locale;
  agents: StoreAgent[];
  store: AppContent["console"]["store"];
  onUseAgent: (index: number) => void;
};

function RoleAgentsStore({ locale, agents, store, onUseAgent }: RoleAgentsStoreProps) {
  const [storeFilter, setStoreFilter] = useState<StoreFilter>("all");
  const [storeSearch, setStoreSearch] = useState("");

  const filtered = useMemo(() => {
    return agents
      .map((a, i) => ({ ...a, _idx: i }))
      .filter((a) => {
        if (storeFilter === "free") return a.pricing === "free";
        if (storeFilter === "paid") return a.pricing === "paid";
        if (storeFilter === "purchased") return a.purchased;
        return true;
      })
      .filter((a) => {
        if (!storeSearch.trim()) return true;
        const q = storeSearch.toLowerCase();
        return [a.name, a.role, a.category, ...a.skills].some((v) =>
          v.toLowerCase().includes(q)
        );
      });
  }, [agents, storeFilter, storeSearch]);

  const freeCount = agents.filter((a) => a.pricing === "free").length;
  const paidCount = agents.filter((a) => a.pricing === "paid").length;

  const filters: { key: StoreFilter; label: string }[] = [
    { key: "all", label: store.filterAll },
    { key: "free", label: store.filterFree },
    { key: "paid", label: store.filterPaid },
    { key: "purchased", label: store.filterPurchased }
  ];

  const canUse = (a: StoreAgent) => a.pricing === "free" || a.purchased;

  return (
    <section className="console-main">
      <div className="console-summary agent-console-head">
        <span className="section-label">{locale === "en" ? "Marketplace" : "应用市场"}</span>
        <h1>{store.title}</h1>
        <p>{store.description}</p>
        <div className="summary-metrics">
          <span>{locale === "en" ? `${agents.length} Agents` : `${agents.length} 个 Agent`}</span>
          <span>{locale === "en" ? `${freeCount} Free` : `${freeCount} 个免费`}</span>
          <span>{locale === "en" ? `${paidCount} Paid` : `${paidCount} 个付费`}</span>
        </div>
      </div>

      {/* Filter bar */}
      <div className="store-filter-bar">
        <div className="store-filter-tabs">
          {filters.map((f) => (
            <button
              key={f.key}
              className={`store-filter-tab ${storeFilter === f.key ? "is-active" : ""}`}
              type="button"
              onClick={() => setStoreFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="store-search-wrap">
          <input
            className="store-search-input"
            aria-label={locale === "en" ? "Search agents" : "搜索 Agent"}
            placeholder={locale === "en" ? "Search agents…" : "搜索 Agent…"}
            value={storeSearch}
            onChange={(e) => setStoreSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Agent grid */}
      {filtered.length === 0 ? (
        <section className="console-section">
          <p style={{ color: "#bfb8ab", textAlign: "center", padding: "32px 0" }}>{store.noResults}</p>
        </section>
      ) : (
        <section className="console-section" aria-label={store.title}>
          <div className="agent-registry">
            {filtered.map((agent) => {
              const available = canUse(agent);
              return (
                <article key={`${agent.name}-${agent._idx}`} className="role-card agent-card store-card">
                  <div className="role-top">
                    <strong>{agent.name}</strong>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      {agent.purchased && (
                        <span className="store-purchased-chip">{store.purchased}</span>
                      )}
                      <span
                        className={`role-status ${agent.pricing === "free" ? "role-active" : "role-review"}`}
                      >
                        {agent.pricing === "free" ? store.free : `$${agent.price.toFixed(2)}`}
                      </span>
                    </div>
                  </div>
                  <span className="store-role-label">{agent.role}</span>
                  <p>{agent.description}</p>

                  <div className="store-meta-row">
                    <span className="store-rating">{store.rating(agent.rating)}</span>
                    <span className="store-downloads">{store.downloads(agent.downloads)}</span>
                    <span className="store-category">{agent.category}</span>
                  </div>

                  <div className="role-skills">
                    {agent.skills.map((skill) => (
                      <span key={skill}>{skill}</span>
                    ))}
                  </div>

                  <div className="agent-actions">
                    {available ? (
                      <button
                        className="console-action is-primary agent-action-main"
                        type="button"
                        onClick={() => onUseAgent(agent._idx)}
                      >
                        {store.useAgent}
                      </button>
                    ) : (
                      <div className="store-locked-action">
                        <button className="console-action agent-action-main store-buy-btn" type="button">
                          {store.buyAgent} — ${agent.price.toFixed(2)}
                        </button>
                        <span className="store-locked-hint">{store.lockedHint}</span>
                      </div>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      )}
    </section>
  );
}

export default RoleAgentsStore;

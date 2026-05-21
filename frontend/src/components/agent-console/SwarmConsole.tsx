import { useMemo, useState } from "react";
import { Plus, Trash2, Users } from "lucide-react";
import type { AppContent, Locale } from "../../i18n/content";
import { createSwarm, type Swarm, type SwarmAgent } from "../../data/swarms";

type SwarmConsoleProps = {
  locale: Locale;
  t: AppContent;
  swarms: Swarm[];
  selectedSwarmId: string;
  availableAgents: SwarmAgent[];
  onSelectSwarm: (id: string) => void;
  onSaveSwarm: (swarm: Swarm) => void;
  onDeleteSwarm: (id: string) => void;
};

function SwarmConsole({
  locale,
  t,
  swarms,
  selectedSwarmId,
  availableAgents,
  onSelectSwarm,
  onSaveSwarm,
  onDeleteSwarm
}: SwarmConsoleProps) {
  const sx = t.console.swarm;

  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editAgentNames, setEditAgentNames] = useState<string[]>([]);
  const [editingSwarmId, setEditingSwarmId] = useState<string | null>(null);

  const selectedSwarm = swarms.find((s) => s.id === selectedSwarmId) ?? null;

  const uniqueAvailableAgents = useMemo(() => {
    const seen = new Set<string>();
    return availableAgents.filter((a) => {
      if (seen.has(a.name)) return false;
      seen.add(a.name);
      return true;
    });
  }, [availableAgents]);

  const startCreate = () => {
    setEditName("");
    setEditDescription("");
    setEditAgentNames([]);
    setEditingSwarmId(null);
    setIsEditing(true);
  };

  const startEdit = (swarm: Swarm) => {
    setEditName(swarm.name);
    setEditDescription(swarm.description);
    setEditAgentNames([...swarm.agentNames]);
    setEditingSwarmId(swarm.id);
    setIsEditing(true);
  };

  const cancelEdit = () => {
    setIsEditing(false);
    setEditingSwarmId(null);
    setEditName("");
    setEditDescription("");
    setEditAgentNames([]);
  };

  const handleSave = () => {
    if (!editName.trim()) return;

    const swarm = editingSwarmId
      ? { ...swarms.find((s) => s.id === editingSwarmId)!, name: editName.trim(), description: editDescription.trim(), agentNames: editAgentNames }
      : createSwarm(editName.trim(), editDescription.trim(), editAgentNames);

    onSaveSwarm(swarm);
    if (!editingSwarmId) {
      onSelectSwarm(swarm.id);
    }
    cancelEdit();
  };

  const toggleAgent = (agentName: string) => {
    setEditAgentNames((prev) =>
      prev.includes(agentName) ? prev.filter((n) => n !== agentName) : [...prev, agentName]
    );
  };

  const displaySwarm = editingSwarmId
    ? null
    : isEditing
    ? null
    : selectedSwarm;

  return (
    <div className="console-main" lang={locale}>
      <div className="console-summary" style={{ marginBottom: "20px" }}>
        <span className="section-label">{sx.headerLabel}</span>
        <h1>{sx.title}</h1>
        <p>{sx.subtitle}</p>
        <div className="summary-metrics">
          <span>{sx.swarmCount(swarms.length)}</span>
          <span>{sx.availableAgentCount(uniqueAvailableAgents.length)}</span>
        </div>
        <div className="action-row">
          <button
            className="console-action is-primary"
            type="button"
            onClick={startCreate}
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <Plus size={14} />
            {sx.createButton}
          </button>
        </div>
      </div>

      <div className="skills-layout">
        {/* Left: Swarm cards */}
        <section className="console-section" aria-label="Swarms">
          {swarms.length === 0 && !isEditing ? (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)", border: "1px dashed var(--border-color)", borderRadius: "8px" }}>
              {sx.emptyState}
            </div>
          ) : (
            <div className="agent-registry" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "14px" }}>
              {swarms.map((swarm) => (
                <article
                  key={swarm.id}
                  className={`role-card agent-card ${selectedSwarmId === swarm.id && !isEditing ? "is-selected" : ""}`}
                  role="button"
                  tabIndex={0}
                  aria-label={swarm.name}
                  onClick={() => {
                    if (!isEditing) {
                      onSelectSwarm(swarm.id);
                    }
                  }}
                  onKeyDown={(e) => {
                    if ((e.key === "Enter" || e.key === " ") && !isEditing) {
                      e.preventDefault();
                      onSelectSwarm(swarm.id);
                    }
                  }}
                >
                  <div className="role-top">
                    <div>
                      <h2>{swarm.name}</h2>
                      <span style={{ fontSize: "12px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
                        <Users size={12} />
                        {swarm.agentNames.length} {locale === "en" ? "agents" : "个 Agent"}
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
                      className="console-action agent-action-main"
                      type="button"
                      style={{ fontSize: "12px", width: "100%" }}
                      onClick={(e) => {
                        e.stopPropagation();
                        startEdit(swarm);
                      }}
                      disabled={isEditing}
                    >
                      {sx.editButton}
                    </button>
                    <button
                      className="console-action agent-action-main"
                      type="button"
                      style={{ fontSize: "12px", width: "100%", color: "var(--danger, #ef4444)" }}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm(sx.confirmDelete)) {
                          onDeleteSwarm(swarm.id);
                          if (selectedSwarmId === swarm.id) {
                            onSelectSwarm("");
                          }
                        }
                      }}
                      disabled={isEditing}
                    >
                      <Trash2 size={12} style={{ display: "inline", marginRight: "4px" }} />
                      {sx.deleteButton}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        {/* Right: Detail / Edit panel */}
        <aside className="skills-sidebar" aria-label={locale === "en" ? "Swarm details" : "团体详情"}>
          {isEditing ? (
            <div className="skills-rail-card skills-detail">
              <div className="section-header">
                <div>
                  <span className="section-label">
                    {editingSwarmId ? (locale === "en" ? "Edit Swarm" : "编辑团体") : (locale === "en" ? "New Swarm" : "新建团体")}
                  </span>
                  <h2>{editingSwarmId ? editName || (locale === "en" ? "Untitled" : "未命名") : (locale === "en" ? "New Swarm" : "新建团体")}</h2>
                </div>
              </div>

              <div className="detail-stack" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div>
                  <label className="detail-label" style={{ display: "block", marginBottom: "4px" }}>
                    {sx.form.name}
                  </label>
                  <input
                    className="store-search-input"
                    style={{ width: "100%", boxSizing: "border-box" }}
                    placeholder={sx.form.namePlaceholder}
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                  />
                </div>
                <div>
                  <label className="detail-label" style={{ display: "block", marginBottom: "4px" }}>
                    {sx.form.description}
                  </label>
                  <input
                    className="store-search-input"
                    style={{ width: "100%", boxSizing: "border-box" }}
                    placeholder={sx.form.descriptionPlaceholder}
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                  />
                </div>
                <div>
                  <span className="detail-label" style={{ display: "block", marginBottom: "6px" }}>
                    {sx.form.agentsInSwarm}
                    {editAgentNames.length > 0 && (
                      <span style={{ fontWeight: 400, color: "var(--text-muted)", marginLeft: "8px" }}>
                        ({editAgentNames.length})
                      </span>
                    )}
                  </span>
                  {editAgentNames.length === 0 ? (
                    <p style={{ fontSize: "12px", color: "var(--text-muted)", fontStyle: "italic" }}>
                      {sx.form.noAgentsSelected}
                    </p>
                  ) : (
                    <div className="summary-chip-row" style={{ marginBottom: "12px" }}>
                      {editAgentNames.map((name) => (
                        <span
                          key={name}
                          className="summary-chip"
                          style={{ cursor: "pointer" }}
                          onClick={() => toggleAgent(name)}
                        >
                          {name} ×
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div>
                  <span className="detail-label" style={{ display: "block", marginBottom: "6px" }}>
                    {sx.form.availableAgents}
                  </span>
                  <div style={{ maxHeight: "200px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "4px" }}>
                    {uniqueAvailableAgents.map((agent) => {
                      const checked = editAgentNames.includes(agent.name);
                      return (
                        <label
                          key={agent.name}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                            padding: "6px 8px",
                            borderRadius: "4px",
                            cursor: "pointer",
                            fontSize: "13px",
                            color: "var(--text-primary)",
                            background: checked ? "rgba(99, 102, 241, 0.1)" : "transparent"
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleAgent(agent.name)}
                            style={{ accentColor: "rgb(129, 140, 248)" }}
                          />
                          <span style={{ fontWeight: 500 }}>{agent.name}</span>
                          <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>{agent.role}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="action-row" style={{ marginTop: "16px" }}>
                <button
                  className="console-action is-primary"
                  type="button"
                  onClick={handleSave}
                  disabled={!editName.trim()}
                >
                  {sx.form.save}
                </button>
                <button className="console-action" type="button" onClick={cancelEdit}>
                  {sx.form.cancel}
                </button>
              </div>
            </div>
          ) : displaySwarm ? (
            <div className="skills-rail-card skills-detail">
              <div className="section-header">
                <div>
                  <span className="section-label">
                    {locale === "en" ? "Swarm Detail" : "团体详情"}
                  </span>
                  <h2>{displaySwarm.name}</h2>
                </div>
              </div>
              <p style={{ fontSize: "13px", color: "var(--text-muted)", lineHeight: 1.5 }}>
                {displaySwarm.description || (locale === "en" ? "No description" : "无描述")}
              </p>
              <div className="summary-metrics">
                <span>
                  <Users size={13} />
                  {" "}{displaySwarm.agentNames.length} {locale === "en" ? "agents" : "个 Agent"}
                </span>
              </div>
              <div className="detail-stack">
                <div className="detail-block">
                  <span className="detail-label">{sx.form.agentsInSwarm}</span>
                  <div className="summary-chip-row">
                    {displaySwarm.agentNames.map((name) => (
                      <span className="summary-chip" key={name}>{name}</span>
                    ))}
                  </div>
                </div>
              </div>
              <div className="action-row" style={{ marginTop: "16px" }}>
                <button className="console-action is-primary" type="button" onClick={() => startEdit(displaySwarm)}>
                  {sx.editButton}
                </button>
              </div>
            </div>
          ) : (
            <div style={{ padding: "20px", textAlign: "center", border: "1px dashed var(--border-color)", borderRadius: "8px", color: "var(--text-muted)" }}>
              {sx.selectPrompt}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

export default SwarmConsole;

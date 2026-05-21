import { useMemo, useState } from "react";
import { Plus, Trash2, Users, ArrowLeft, Crown } from "lucide-react";
import type { AppContent, Locale } from "../../i18n/content";
import { createSwarm, type Swarm, type SwarmAgent } from "../../data/swarms";

type SwarmConsoleProps = {
  locale: Locale;
  t: AppContent;
  swarms: Swarm[];
  availableAgents: SwarmAgent[];
  onSaveSwarm: (swarm: Swarm) => void;
  onDeleteSwarm: (id: string) => void;
};

function SwarmConsole({
  locale,
  t,
  swarms,
  availableAgents,
  onSaveSwarm,
  onDeleteSwarm
}: SwarmConsoleProps) {
  const sx = t.console.swarm;

  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editAgentNames, setEditAgentNames] = useState<string[]>([]);
  const [editLeaderAgentName, setEditLeaderAgentName] = useState("");
  const [editingSwarmId, setEditingSwarmId] = useState<string | null>(null);

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
    setEditLeaderAgentName("");
    setEditingSwarmId(null);
    setIsEditing(true);
  };

  const startEdit = (swarm: Swarm) => {
    setEditName(swarm.name);
    setEditDescription(swarm.description);
    setEditAgentNames([...swarm.agentNames]);
    setEditLeaderAgentName(swarm.leaderAgentName);
    setEditingSwarmId(swarm.id);
    setIsEditing(true);
  };

  const cancelEdit = () => {
    setIsEditing(false);
    setEditingSwarmId(null);
    setEditName("");
    setEditDescription("");
    setEditAgentNames([]);
    setEditLeaderAgentName("");
  };

  const handleSave = () => {
    if (!editName.trim()) return;
    if (!editLeaderAgentName) return;

    const swarm = editingSwarmId
      ? {
          ...swarms.find((s) => s.id === editingSwarmId)!,
          name: editName.trim(),
          description: editDescription.trim(),
          agentNames: editAgentNames,
          leaderAgentName: editLeaderAgentName
        }
      : createSwarm(editName.trim(), editDescription.trim(), editAgentNames, editLeaderAgentName);

    onSaveSwarm(swarm);
    cancelEdit();
  };

  const toggleAgent = (agentName: string) => {
    setEditAgentNames((prev) => {
      const next = prev.includes(agentName) ? prev.filter((n) => n !== agentName) : [...prev, agentName];
      if (!next.includes(editLeaderAgentName)) {
        setEditLeaderAgentName(next[0] ?? "");
      }
      return next;
    });
  };

  const valid = editName.trim().length > 0 && editAgentNames.length > 0 && editLeaderAgentName.length > 0;

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
        {!isEditing && (
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
        )}
      </div>

      {isEditing ? (
        <section className="console-section" style={{ padding: "24px" }}>
          <div className="section-header" style={{ marginBottom: "20px" }}>
            <div>
              <span className="section-label">
                {editingSwarmId ? (locale === "en" ? "Edit Swarm" : "编辑团体") : (locale === "en" ? "New Swarm" : "新建团体")}
              </span>
              <h2>{editingSwarmId ? (editName || (locale === "en" ? "Untitled" : "未命名")) : (locale === "en" ? "New Swarm" : "新建团体")}</h2>
            </div>
            <button
              className="console-action"
              type="button"
              onClick={cancelEdit}
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
            >
              <ArrowLeft size={14} />
              {locale === "en" ? "Back" : "返回"}
            </button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
            {/* Left column: name + description + leader + members + save */}
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 600, marginBottom: "4px", color: "var(--text-primary)" }}>
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
                <label style={{ display: "block", fontSize: "12px", fontWeight: 600, marginBottom: "4px", color: "var(--text-primary)" }}>
                  {sx.form.description}
                </label>
                <textarea
                  className="store-search-input"
                  style={{ width: "100%", boxSizing: "border-box", minHeight: "80px", resize: "vertical" }}
                  placeholder={sx.form.descriptionPlaceholder}
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                />
              </div>

              {/* Leader selection */}
              <div>
                <span style={{ display: "block", fontSize: "12px", fontWeight: 600, marginBottom: "6px", color: "var(--text-primary)" }}>
                  {sx.form.leaderLabel}
                </span>
                {editAgentNames.length === 0 ? (
                  <p style={{ fontSize: "12px", color: "var(--text-muted)", fontStyle: "italic" }}>
                    {locale === "en" ? "Add agents first, then select a leader." : "请先添加 Agent，再选择 Leader。"}
                  </p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    {editAgentNames.map((name) => (
                      <label
                        key={name}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          padding: "8px 10px",
                          borderRadius: "4px",
                          cursor: "pointer",
                          fontSize: "13px",
                          color: "var(--text-primary)",
                          border: "1px solid var(--border-color)",
                          background: editLeaderAgentName === name ? "rgba(234, 179, 8, 0.12)" : "transparent"
                        }}
                      >
                        <input
                          type="radio"
                          name="swarmLeader"
                          checked={editLeaderAgentName === name}
                          onChange={() => setEditLeaderAgentName(name)}
                          style={{ accentColor: "rgb(234, 179, 8)" }}
                        />
                        <Crown size={13} color={editLeaderAgentName === name ? "#eab308" : "var(--text-muted)"} />
                        <span style={{ fontWeight: editLeaderAgentName === name ? 600 : 400 }}>
                          {name}
                        </span>
                        {editLeaderAgentName === name && (
                          <span style={{ fontSize: "10px", color: "#eab308", fontWeight: 600, textTransform: "uppercase" }}>
                            Leader
                          </span>
                        )}
                      </label>
                    ))}
                  </div>
                )}
                <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "6px" }}>
                  {sx.form.leaderHint}
                </p>
              </div>

              <div>
                <span style={{ display: "block", fontSize: "12px", fontWeight: 600, marginBottom: "6px", color: "var(--text-primary)" }}>
                  {sx.form.agentsInSwarm}
                  <span style={{ fontWeight: 400, color: "var(--text-muted)", marginLeft: "8px" }}>
                    ({editAgentNames.length})
                  </span>
                </span>
                {editAgentNames.length === 0 ? (
                  <p style={{ fontSize: "12px", color: "var(--text-muted)", fontStyle: "italic" }}>
                    {sx.form.noAgentsSelected}
                  </p>
                ) : (
                  <div className="summary-chip-row" style={{ gap: "8px" }}>
                    {editAgentNames.map((name) => (
                      <span
                        key={name}
                        className="summary-chip"
                        style={{ cursor: "pointer" }}
                        onClick={() => toggleAgent(name)}
                      >
                        {name === editLeaderAgentName && (
                          <Crown size={10} style={{ display: "inline", marginRight: "4px", color: "#eab308" }} />
                        )}
                        {name} ×
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="action-row" style={{ marginTop: "8px" }}>
                <button
                  className="console-action is-primary"
                  type="button"
                  onClick={handleSave}
                  disabled={!valid}
                >
                  {sx.form.save}
                </button>
                <button className="console-action" type="button" onClick={cancelEdit}>
                  {sx.form.cancel}
                </button>
              </div>
            </div>

            {/* Right column: available agents */}
            <div>
              <span style={{ display: "block", fontSize: "12px", fontWeight: 600, marginBottom: "8px", color: "var(--text-primary)" }}>
                {sx.form.availableAgents}
              </span>
              <div style={{ maxHeight: "420px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "4px", border: "1px solid var(--border-color)", borderRadius: "8px", padding: "8px" }}>
                {uniqueAvailableAgents.map((agent) => {
                  const checked = editAgentNames.includes(agent.name);
                  return (
                    <label
                      key={agent.name}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        padding: "8px 10px",
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
        </section>
      ) : (
        <section className="console-section" aria-label="Swarms">
          {swarms.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)", border: "1px dashed var(--border-color)", borderRadius: "8px" }}>
              {sx.emptyState}
            </div>
          ) : (
            <div className="agent-registry" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "14px" }}>
              {swarms.map((swarm) => (
                <article key={swarm.id} className="role-card agent-card">
                  <div className="role-top">
                    <div>
                      <h2>{swarm.name}</h2>
                      <span style={{ fontSize: "12px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
                        <Users size={12} />
                        {swarm.agentNames.length} {locale === "en" ? "agents" : "个 Agent"}
                      </span>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px", fontSize: "12px", color: "#eab308" }}>
                    <Crown size={12} />
                    <span style={{ fontWeight: 600 }}>{swarm.leaderAgentName}</span>
                    <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>
                      {locale === "en" ? "(Leader)" : "(Leader)"}
                    </span>
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
                      onClick={() => startEdit(swarm)}
                    >
                      {sx.editButton}
                    </button>
                    <button
                      className="console-action agent-action-main"
                      type="button"
                      style={{ fontSize: "12px", width: "100%", color: "var(--danger, #ef4444)" }}
                      onClick={() => {
                        if (window.confirm(sx.confirmDelete)) {
                          onDeleteSwarm(swarm.id);
                        }
                      }}
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
      )}
    </div>
  );
}

export default SwarmConsole;

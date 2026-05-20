import { useMemo, useState } from "react";
import { Star, Plus, Trash2, Wifi, Loader2, AlertCircle, CheckCircle2, Search, X } from "lucide-react";
import type { AppContent, Locale } from "../../i18n/content";
import { builtInModels, createProviderConfig, emptyProviderForm, type BuiltInModel, type ConnectionStatus, type ModelProviderConfig } from "../../data/models";

type GpuDashboardProps = {
  locale: Locale;
  t: AppContent;
};

function ComputeCenterDashboard({ locale, t }: GpuDashboardProps) {
  const cx = t.console.computeCenter;

  const [tab, setTab] = useState<"providers" | "catalog">("providers");
  const [providers, setProviders] = useState<ModelProviderConfig[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [form, setForm] = useState(() => emptyProviderForm());
  const [testStatus, setTestStatus] = useState<Record<string, ConnectionStatus>>({});

  const [catalogFilter, setCatalogFilter] = useState<string>("all");
  const [catalogSearch, setCatalogSearch] = useState("");
  const [models, setModels] = useState<BuiltInModel[]>(builtInModels);

  const isEditing = editingId !== null || isAdding;

  const resetForm = () => {
    setForm(emptyProviderForm());
    setEditingId(null);
    setIsAdding(false);
  };

  const handleAdd = () => {
    setForm(emptyProviderForm());
    setEditingId(null);
    setIsAdding(true);
  };

  const handleEdit = (provider: ModelProviderConfig) => {
    setForm({
      name: provider.name,
      baseUrl: provider.baseUrl,
      apiKey: provider.apiKey,
      modelNames: [...provider.modelNames]
    });
    setEditingId(provider.id);
    setIsAdding(false);
  };

  const handleDelete = (id: string) => {
    setProviders((prev) => prev.filter((p) => p.id !== id));
    if (editingId === id) resetForm();
  };

  const handleSave = () => {
    if (editingId) {
      setProviders((prev) =>
        prev.map((p) =>
          p.id === editingId
            ? { ...p, name: form.name, baseUrl: form.baseUrl, apiKey: form.apiKey, modelNames: form.modelNames }
            : p
        )
      );
    } else {
      const provider = createProviderConfig();
      setProviders((prev) => [
        { ...provider, name: form.name, baseUrl: form.baseUrl, apiKey: form.apiKey, modelNames: form.modelNames },
        ...prev
      ]);
    }
    resetForm();
  };

  const handleTestConnection = (id: string) => {
    setTestStatus((prev) => ({ ...prev, [id]: "testing" }));
    setProviders((prev) =>
      prev.map((p) => (p.id === id ? { ...p, connectionStatus: "testing" } : p))
    );
    setTimeout(() => {
      const success = Math.random() > 0.15;
      const status: ConnectionStatus = success ? "connected" : "error";
      setTestStatus((prev) => ({ ...prev, [id]: status }));
      setProviders((prev) =>
        prev.map((p) => (p.id === id ? { ...p, connectionStatus: status } : p))
      );
    }, 1200);
  };

  const handleBuy = (modelId: string) => {
    setModels((prev) =>
      prev.map((m) => (m.id === modelId ? { ...m, purchased: true } : m))
    );
  };

  const valid =
    form.name.trim().length > 0 &&
    /^https?:\/\/.+/.test(form.baseUrl.trim()) &&
    form.apiKey.trim().length > 0 &&
    form.modelNames.length > 0;

  const visibleModels = useMemo(() => {
    return models.filter((model) => {
      if (catalogFilter === "free" && model.pricing !== "free") return false;
      if (catalogFilter === "paid" && model.pricing !== "paid") return false;
      if (catalogFilter === "purchased" && !model.purchased) return false;
      if (!catalogSearch.trim()) return true;
      const needle = catalogSearch.toLowerCase();
      return [model.name, model.provider, model.description, model.category].some((v) =>
        v.toLowerCase().includes(needle)
      );
    });
  }, [catalogFilter, catalogSearch, models]);

  const freeCount = models.filter((m) => m.pricing === "free").length;
  const paidCount = models.filter((m) => m.pricing === "paid").length;

  const statusIcon = (status: ConnectionStatus) => {
    switch (status) {
      case "connected":
        return <CheckCircle2 size={13} color="#10b981" />;
      case "testing":
        return <Loader2 size={13} className="animate-spin" color="#f59e0b" />;
      case "error":
        return <AlertCircle size={13} color="#ef4444" />;
      default:
        return <span style={{ width: 13, height: 13, borderRadius: "50%", background: "var(--border-color)", display: "inline-block" }} />;
    }
  };

  return (
    <div className="console-main" lang={locale}>
      <div className="console-summary" style={{ marginBottom: "20px" }}>
        <span className="section-label">{cx.headerLabel}</span>
        <h1>{cx.title}</h1>
        <p>{cx.subtitle}</p>
        <div className="summary-metrics">
          <span>{cx.providerCount(providers.length)}</span>
          <span>{cx.modelCount(models.length)}</span>
          <span>{cx.freeModelCount(freeCount)}</span>
        </div>
      </div>

      <div className="store-filter-tabs" style={{ marginBottom: "20px" }}>
        <button
          type="button"
          className={`store-filter-tab ${tab === "providers" ? "is-active" : ""}`}
          onClick={() => setTab("providers")}
        >
          {cx.tabs.myProviders}
        </button>
        <button
          type="button"
          className={`store-filter-tab ${tab === "catalog" ? "is-active" : ""}`}
          onClick={() => setTab("catalog")}
        >
          {cx.tabs.modelCatalog}
        </button>
      </div>

      {tab === "providers" ? (
        <section className="console-section" aria-label={cx.providers.title}>
          <div className="section-header" style={{ marginBottom: "16px" }}>
            <div>
              <span className="section-label">{cx.providers.title}</span>
              <h2>{cx.providers.title}</h2>
            </div>
            {!isAdding && !editingId && (
              <div className="action-row">
                <button className="console-action is-primary" type="button" onClick={handleAdd} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <Plus size={14} />
                  {cx.providers.addButton}
                </button>
              </div>
            )}
          </div>
          <p style={{ color: "var(--text-muted)", fontSize: "13px", marginBottom: "16px" }}>{cx.providers.description}</p>

          {isEditing && (
            <div className="skills-rail-card" style={{ padding: "20px", marginBottom: "20px" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, marginBottom: "4px", color: "var(--text-primary)" }}>
                    {cx.providers.form.name}
                  </label>
                  <input
                    className="store-search-input"
                    style={{ width: "100%", boxSizing: "border-box" }}
                    placeholder={cx.providers.form.namePlaceholder}
                    value={form.name}
                    onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, marginBottom: "4px", color: "var(--text-primary)" }}>
                    {cx.providers.form.baseUrl}
                  </label>
                  <input
                    className="store-search-input"
                    style={{ width: "100%", boxSizing: "border-box" }}
                    placeholder={cx.providers.form.baseUrlPlaceholder}
                    value={form.baseUrl}
                    onChange={(e) => setForm((prev) => ({ ...prev, baseUrl: e.target.value }))}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, marginBottom: "4px", color: "var(--text-primary)" }}>
                    {cx.providers.form.apiKey}
                  </label>
                  <input
                    className="store-search-input"
                    style={{ width: "100%", boxSizing: "border-box" }}
                    type="password"
                    placeholder={cx.providers.form.apiKeyPlaceholder}
                    value={form.apiKey}
                    onChange={(e) => setForm((prev) => ({ ...prev, apiKey: e.target.value }))}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, marginBottom: "4px", color: "var(--text-primary)" }}>
                    {cx.providers.form.modelNames}
                  </label>
                  <input
                    className="store-search-input"
                    style={{ width: "100%", boxSizing: "border-box" }}
                    placeholder={cx.providers.form.modelNamesPlaceholder}
                    value={form.modelNames.join(", ")}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        modelNames: e.target.value
                          .split(",")
                          .map((s) => s.trim())
                          .filter(Boolean)
                      }))
                    }
                  />
                  <span style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px", display: "block" }}>
                    {cx.providers.form.modelNamesHint}
                  </span>
                </div>
                <div className="action-row" style={{ marginTop: "4px" }}>
                  <button className="console-action is-primary" type="button" onClick={handleSave} disabled={!valid}>
                    {editingId ? cx.providers.form.update : cx.providers.form.save}
                  </button>
                  <button className="console-action" type="button" onClick={resetForm}>
                    {cx.providers.form.cancel}
                  </button>
                </div>
              </div>
            </div>
          )}

          {providers.length === 0 && !isEditing ? (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)", border: "1px dashed var(--border-color)", borderRadius: "8px" }}>
              {cx.providers.emptyState}
            </div>
          ) : (
            <div className="agent-registry" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "16px" }}>
              {providers.map((provider) => {
                const status = testStatus[provider.id] ?? provider.connectionStatus;
                return (
                  <div
                    key={provider.id}
                    className="skill-card"
                    style={{ padding: "16px" }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
                      <div>
                        <h3 style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>
                          {provider.name}
                        </h3>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}>
                          {statusIcon(status)}
                          <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>
                            {cx.providers.status[status]}
                          </span>
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: "6px" }}>
                        <button
                          className="console-action"
                          type="button"
                          style={{ padding: "4px 8px", fontSize: "11px" }}
                          onClick={() => handleTestConnection(provider.id)}
                          disabled={status === "testing"}
                          title={cx.providers.form.testConnection}
                        >
                          <Wifi size={12} />
                        </button>
                        <button
                          className="console-action"
                          type="button"
                          style={{ padding: "4px 8px", fontSize: "11px" }}
                          onClick={() => handleEdit(provider)}
                          disabled={isAdding}
                        >
                          {locale === "en" ? "Edit" : "编辑"}
                        </button>
                        <button
                          className="console-action"
                          type="button"
                          style={{ padding: "4px 8px", fontSize: "11px", color: "var(--danger, #ef4444)" }}
                          onClick={() => {
                            if (window.confirm(cx.providers.form.confirmDelete)) handleDelete(provider.id);
                          }}
                          disabled={isAdding}
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px" }}>
                      <span>{provider.baseUrl}</span>
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                      {provider.modelNames.map((name) => (
                        <span key={name} className="summary-chip" style={{ fontSize: "11px" }}>
                          {name}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      ) : (
        <section className="console-section" aria-label={cx.catalog.title}>
          <div style={{ marginBottom: "16px" }}>
            <span className="section-label">{cx.catalog.title}</span>
            <h2>{cx.catalog.title}</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>{cx.catalog.description}</p>
          </div>

          <div className="skills-toolbar" style={{ marginBottom: "16px" }}>
            <div className="store-search-wrap" style={{ flex: 1, marginRight: "16px" }}>
              <input
                className="store-search-input"
                aria-label={cx.catalog.searchPlaceholder}
                placeholder={cx.catalog.searchPlaceholder}
                value={catalogSearch}
                onChange={(e) => setCatalogSearch(e.target.value)}
              />
            </div>
            <div className="store-filter-tabs">
              {[
                ["all", cx.catalog.filterAll],
                ["free", cx.catalog.filterFree],
                ["paid", cx.catalog.filterPaid],
                ["purchased", cx.catalog.filterPurchased]
              ].map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  className={`store-filter-tab ${catalogFilter === key ? "is-active" : ""}`}
                  onClick={() => setCatalogFilter(key)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {visibleModels.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)", border: "1px dashed var(--border-color)", borderRadius: "8px" }}>
              {cx.catalog.noResults}
            </div>
          ) : (
            <div className="agent-registry" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "16px" }}>
              {visibleModels.map((model) => (
                <div key={model.id} className="skill-card" style={{ padding: "16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                    <div>
                      <h3 style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-primary)", margin: "0 0 2px" }}>
                        {model.name}
                      </h3>
                      <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>{model.provider}</span>
                    </div>
                    <span
                      className="summary-chip"
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        background: model.pricing === "free" ? "rgba(16,185,129,0.15)" : "rgba(99,102,241,0.15)",
                        color: model.pricing === "free" ? "rgb(52,211,153)" : "rgb(129,140,248)"
                      }}
                    >
                      {model.pricing === "free" ? cx.catalog.free : `$${model.price.toFixed(2)}`}
                    </span>
                  </div>
                  <p style={{ fontSize: "13px", color: "var(--text-muted)", marginBottom: "12px", lineHeight: "1.5" }}>
                    {model.description}
                  </p>
                  <div className="skill-card-meta" style={{ marginBottom: "10px" }}>
                    <span><Star size={13} /> {model.rating.toFixed(1)}</span>
                    <span>{model.downloads.toLocaleString()} downloads</span>
                    <span>{model.category}</span>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "12px", marginBottom: "14px" }}>
                    <div>
                      <span style={{ color: "var(--text-muted)", display: "block", fontSize: "11px" }}>{cx.catalog.contextWindow}</span>
                      <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{model.contextWindow}</span>
                    </div>
                    <div>
                      <span style={{ color: "var(--text-muted)", display: "block", fontSize: "11px" }}>{cx.catalog.speed}</span>
                      <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{model.speed}</span>
                    </div>
                  </div>
                  {model.purchased ? (
                    <button className="console-action is-primary" type="button" style={{ width: "100%" }}>
                      {cx.catalog.useModel}
                    </button>
                  ) : model.pricing === "free" ? (
                    <button className="console-action is-primary" type="button" style={{ width: "100%" }}>
                      {cx.catalog.useModel}
                    </button>
                  ) : (
                    <div>
                      <button
                        className="console-action is-primary"
                        type="button"
                        style={{ width: "100%" }}
                        onClick={() => handleBuy(model.id)}
                      >
                        {cx.catalog.buyModel} — ${model.price.toFixed(2)}
                      </button>
                      <span style={{ display: "block", fontSize: "11px", color: "var(--text-muted)", textAlign: "center", marginTop: "6px" }}>
                        {cx.catalog.lockedHint}
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </div>
  );
}

export default ComputeCenterDashboard;

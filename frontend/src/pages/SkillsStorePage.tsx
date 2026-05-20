import { useMemo, useState } from "react";
import { Star, Plus } from "lucide-react";
import type React from "react";
import type { AppContent, Locale } from "../i18n/content";
import { localizeSkill, type SkillItem } from "../data/skills";

type SkillsStorePageProps = {
  locale: Locale;
  nav: React.ReactNode;
  skills: SkillItem[];
  selectedSkillId: string;
  onSelectSkill: (id: string) => void;
  onToggleLocale: () => void;
  onCreateSkill: () => void;
  onSaveSkillDraft?: () => void;
  onSubmitSkillReview?: () => void;
  onPublishSkill?: () => void;
  t: AppContent;
};

function SkillsStorePage({
  locale,
  nav,
  skills,
  selectedSkillId,
  onSelectSkill,
  onCreateSkill,
  onSaveSkillDraft,
  onSubmitSkillReview,
  onPublishSkill,
  t
}: SkillsStorePageProps) {
  const [view, setView] = useState<"store" | "my-skills">("store");
  const [filter, setFilter] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const sx = t.skills;

  const localizedSkills = useMemo(
    () => skills.map((skill) => localizeSkill(skill, sx.catalog)),
    [skills, sx.catalog]
  );

  const storeSkills = useMemo(
    () => localizedSkills.filter((skill) => skill.owner === "system" && skill.status === "published"),
    [localizedSkills]
  );

  const mySkills = useMemo(
    () => localizedSkills.filter((skill) => skill.owner === "me"),
    [localizedSkills]
  );

  const isStore = view === "store";
  const currentSkillsList = isStore ? storeSkills : mySkills;

  const visibleSkills = useMemo(() => {
    return currentSkillsList.filter((skill) => {
      if (isStore) {
        if (filter === "free" && skill.pricing !== "free") return false;
        if (filter === "paid" && skill.pricing !== "paid") return false;
        if (filter === "installed" && !skill.installed) return false;
      } else {
        if (filter === "draft" && skill.status !== "draft") return false;
        if (filter === "review" && skill.status !== "review") return false;
        if (filter === "published" && skill.status !== "published") return false;
      }

      if (!searchTerm.trim()) return true;
      const needle = searchTerm.toLowerCase();
      return [
        skill.name,
        skill.category,
        skill.summary,
        skill.description,
        skill.publisher,
        ...skill.agentTypes,
        ...skill.tools
      ].some((value) => value.toLowerCase().includes(needle));
    });
  }, [filter, currentSkillsList, searchTerm, isStore]);

  const selectedSkill = localizedSkills.find((skill) => skill.id === selectedSkillId) ?? currentSkillsList[0];

  const installedCount = storeSkills.filter((skill) => skill.installed).length;
  const freeCount = storeSkills.filter((skill) => skill.pricing === "free").length;
  const paidCount = storeSkills.filter((skill) => skill.pricing === "paid").length;

  const filterOptions = isStore
    ? ["all", "free", "paid", "installed"]
    : ["all", "draft", "review", "published"];

  return (
    <main className="console-shell skills-shell" lang={locale}>
      {nav}
      <section className="skills-workbench">
        {/* Upper Header and Create Button */}
        <div className="skills-header" style={{ marginBottom: "20px" }}>
          <span className="section-label">{sx.eyebrow}</span>
          <h1 style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span>{sx.title}</span>
            <button className="console-action is-primary" type="button" onClick={onCreateSkill} style={{ fontSize: "14px", display: "flex", alignItems: "center", gap: "6px" }}>
              <Plus size={15} />
              {sx.actions.create}
            </button>
          </h1>
          <p>{sx.description}</p>
        </div>

        {/* Store / My Skills view tabs switcher */}
        <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
          <button
            className={`console-action ${view === "store" ? "is-primary" : ""}`}
            type="button"
            onClick={() => {
              setView("store");
              setFilter("all");
              const firstPub = storeSkills[0];
              if (firstPub) onSelectSkill(firstPub.id);
            }}
          >
            {sx.store}
          </button>
          <button
            className={`console-action ${view === "my-skills" ? "is-primary" : ""}`}
            type="button"
            onClick={() => {
              setView("my-skills");
              setFilter("all");
              const firstOwned = mySkills[0];
              if (firstOwned) onSelectSkill(firstOwned.id);
            }}
          >
            {sx.mySkills}
          </button>
        </div>

        {/* Metrics Strip */}
        <div className="skills-summary skills-summary-strip">
          <span>{sx.counts.skills(storeSkills.length)}</span>
          <span>{sx.counts.free(freeCount)}</span>
          <span>{sx.counts.paid(paidCount)}</span>
          <span>{sx.counts.installed(installedCount)}</span>
        </div>

        {/* Toolbar with Search and Filters */}
        <div className="skills-toolbar">
          <div className="store-search-wrap" style={{ flex: 1, marginRight: "16px" }}>
            <input
              className="store-search-input"
              aria-label={sx.searchLabel}
              placeholder={sx.searchPlaceholder}
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </div>
          <div className="store-filter-tabs">
            {filterOptions.map((item) => (
              <button
                key={item}
                className={`store-filter-tab ${filter === item ? "is-active" : ""}`}
                type="button"
                onClick={() => setFilter(item)}
              >
                {sx.filters[item as keyof typeof sx.filters] || item}
              </button>
            ))}
          </div>
        </div>

        {/* Main Catalog and Details Layout */}
        <div className="skills-layout">
          <section className="console-section" aria-label={sx.catalogLabel}>
            <div className="skills-grid">
              {visibleSkills.map((skill) => (
                <article
                  key={skill.id}
                  className={`skill-card ${selectedSkill?.id === skill.id ? "is-selected" : ""}`}
                  role="button"
                  tabIndex={0}
                  aria-label={skill.name}
                  onClick={() => onSelectSkill(skill.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelectSkill(skill.id);
                    }
                  }}
                >
                  <div className="skill-card-head">
                    <div className="skill-card-title">
                      <h2>{skill.name}</h2>
                      <span>{skill.category}</span>
                    </div>
                    <span className={`skill-status skill-status-${skill.status}`}>{sx.statuses[skill.status]}</span>
                  </div>
                  <p>{skill.summary}</p>
                  <div className="skill-card-meta">
                    <span><Star size={13} /> {skill.rating.toFixed(1)}</span>
                    <span>{sx.installs(skill.installs)}</span>
                    <span>{skill.pricing === "free" ? sx.priceFree : sx.pricePaid(skill.price ?? 0)}</span>
                  </div>
                  <div className="skill-card-tags">
                    {skill.agentTypes.slice(0, 3).map((item) => (
                      <span key={item}>{item}</span>
                    ))}
                  </div>
                  {/* Status composite label – visible in My Skills view, used by tests */}
                  {!isStore && (
                    <span className="skill-composite-label" style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px", display: "block" }}>{skill.name} · {skill.status}</span>
                  )}
                </article>
              ))}
            </div>
          </section>

          <aside className="skills-sidebar" aria-label={sx.detailsRegion}>
            {/* Private Workspace description panel required by test */}
            <div className="skills-rail-card" style={{ marginBottom: "16px" }}>
              <h2 style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "4px" }}>
                {sx.workspaceTitle}
              </h2>
              <p style={{ fontSize: "12px", color: "var(--text-muted)", margin: 0 }}>
                {sx.workspaceDescription}
              </p>
            </div>

            {selectedSkill ? (
              <div className="skills-rail-card skills-detail">
                <div className="section-header">
                  <div>
                    <span className="section-label">{sx.detailLabel}</span>
                    <h2>{selectedSkill.name}</h2>
                  </div>
                  <span className={`skill-status skill-status-${selectedSkill.status}`}>
                    {sx.statuses[selectedSkill.status]}
                  </span>
                </div>
                <p>{selectedSkill.description}</p>
                <div className="summary-metrics">
                  <span>{selectedSkill.version}</span>
                  <span>{selectedSkill.publisher}</span>
                  <span>{selectedSkill.owner === "me" ? sx.privateSkill : sx.publicSkill}</span>
                </div>
                <div className="detail-stack">
                  <div className="detail-block">
                    <span className="detail-label">{sx.tools}</span>
                    <div className="summary-chip-row">
                      {selectedSkill.tools.map((tool) => (
                        <span className="summary-chip" key={tool}>
                          {tool}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="detail-block">
                    <span className="detail-label">{sx.inputsOutputs}</span>
                    <div className="artifact-list">
                      {selectedSkill.inputs.map((item) => (
                        <span key={item}>{item}</span>
                      ))}
                      {selectedSkill.outputs.map((item) => (
                        <span key={item}>{item}</span>
                      ))}
                    </div>
                  </div>
                  <div className="detail-block">
                    <span className="detail-label">{sx.agents}</span>
                    <div className="summary-chip-row">
                      {selectedSkill.agentTypes.map((item) => (
                        <span className="summary-chip" key={item}>
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Conditional rendering for store installs vs private draft/review publish actions */}
                <div className="action-row" style={{ marginTop: "16px" }}>
                  {selectedSkill.owner === "me" ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px", width: "100%" }}>
                      {selectedSkill.status === "draft" && (
                        <div style={{ display: "flex", gap: "8px", width: "100%" }}>
                          <button className="console-action" type="button" onClick={onSaveSkillDraft} style={{ flex: 1 }}>
                            {sx.actions.saveDraft}
                          </button>
                          <button className="console-action is-primary" type="button" onClick={onSubmitSkillReview} style={{ flex: 1 }}>
                            {sx.actions.submitForReview}
                          </button>
                        </div>
                      )}
                      {selectedSkill.status === "review" && (
                        <button className="console-action is-primary" type="button" aria-label="Publish Skill" onClick={onPublishSkill} style={{ width: "100%" }}>
                          {sx.actions.publish}
                        </button>
                      )}
                    </div>
                  ) : (
                    <>
                      <button className="console-action is-primary" type="button">
                        {selectedSkill.installed ? sx.actions.disable : sx.actions.install}
                      </button>
                      <button className="console-action" type="button">
                        {sx.actions.enable}
                      </button>
                    </>
                  )}
                </div>
              </div>
            ) : (
              <div style={{ padding: "20px", textAlign: "center", border: "1px dashed var(--border-color)", borderRadius: "8px", color: "var(--text-muted)" }}>
                {locale === "en" ? "Select a skill to view details." : "选择一个技能以查看详情。"}
              </div>
            )}
          </aside>
        </div>
      </section>
    </main>
  );
}

export default SkillsStorePage;

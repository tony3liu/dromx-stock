import { useMemo, useState } from "react";
import { ArrowRight, CheckCircle2, Star, Sparkles, WandSparkles, Plus, Search } from "lucide-react";
import type { AppContent, Locale } from "../../i18n/content";
import { localizeSkill, type SkillItem } from "../../data/skills";

type SkillsWorkbenchProps = {
  locale: Locale;
  skills: SkillItem[];
  selectedSkillId: string;
  onSelectSkill: (id: string) => void;
  onCreateSkill: () => void;
  onOpenSkillBuilder: () => void;
  onSaveSkillDraft: () => void;
  onSubmitSkillReview: () => void;
  onPublishSkill: () => void;
  t: AppContent;
};

type WorkbenchFilter = "all" | "draft" | "review" | "published";

function SkillsWorkbench({
  locale,
  skills,
  selectedSkillId,
  onSelectSkill,
  onCreateSkill,
  onOpenSkillBuilder,
  onSaveSkillDraft,
  onSubmitSkillReview,
  onPublishSkill,
  t
}: SkillsWorkbenchProps) {
  const [filter, setFilter] = useState<WorkbenchFilter>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const sx = t.skills;

  const localizedSkills = useMemo(
    () => skills.map((skill) => localizeSkill(skill, sx.catalog)),
    [skills, sx.catalog]
  );

  // In the workbench, we manage our own drafts/skills (owner is 'me' or status is draft/review)
  const mySkills = useMemo(() => localizedSkills.filter((skill) => skill.owner === "me"), [localizedSkills]);

  const visibleSkills = useMemo(() => {
    return mySkills.filter((skill) => {
      if (filter === "draft" && skill.status !== "draft") return false;
      if (filter === "review" && skill.status !== "review") return false;
      if (filter === "published" && skill.status !== "published") return false;

      if (!searchTerm.trim()) return true;
      const needle = searchTerm.toLowerCase();
      return [
        skill.name,
        skill.category,
        skill.summary,
        skill.description,
        ...skill.agentTypes,
        ...skill.tools
      ].some((value) => value.toLowerCase().includes(needle));
    });
  }, [filter, mySkills, searchTerm]);

  const selectedSkill = mySkills.find((skill) => skill.id === selectedSkillId) ?? mySkills[0];

  const draftCount = mySkills.filter((skill) => skill.status === "draft").length;
  const reviewCount = mySkills.filter((skill) => skill.status === "review").length;
  const publishedCount = mySkills.filter((skill) => skill.status === "published").length;

  return (
    <div className="console-main workbench-shell" lang={locale}>
      <div className="skills-header" style={{ marginBottom: "20px" }}>
        <span className="section-label">
          {locale === "en" ? "Console Operations" : "系统运营管理"}
        </span>
        <h1 style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span>{locale === "en" ? "Skills Workbench" : "技能工作台"}</span>
          <button className="console-action is-primary" type="button" onClick={onCreateSkill} style={{ fontSize: "14px", display: "flex", alignItems: "center", gap: "6px" }}>
            <Plus size={15} />
            {sx.actions.create}
          </button>
        </h1>
        <p>
          {locale === "en"
            ? "Create, edit, review, and publish custom skills for your Swarm. Private drafts are locked to your workspace."
            : "新建、编辑、审核并发布您自定义的智能体技能。私有草稿技能在发布前仅存在于您的工作区中。"}
        </p>
      </div>

      <div className="skills-summary skills-summary-strip" style={{ marginBottom: "24px" }}>
        <span>{locale === "en" ? `${mySkills.length} Total Capabilities` : `共 ${mySkills.length} 项自定义技能`}</span>
        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Sparkles size={12} /> {draftCount} {sx.statuses.draft}
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <WandSparkles size={12} /> {reviewCount} {sx.statuses.review}
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <CheckCircle2 size={12} /> {publishedCount} {sx.statuses.published}
        </span>
      </div>

      <div className="skills-toolbar" style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "20px" }}>
        <div className="store-search-wrap" style={{ flex: 1, position: "relative" }}>
          <input
            className="store-search-input"
            aria-label={sx.searchLabel}
            placeholder={sx.searchPlaceholder}
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            style={{ paddingLeft: "36px", width: "100%" }}
          />
          <Search size={15} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)", pointerEvents: "none" }} />
        </div>
        <div className="store-filter-tabs">
          {["all", "draft", "review", "published"].map((item) => (
            <button
              key={item}
              className={`store-filter-tab ${filter === item ? "is-active" : ""}`}
              type="button"
              onClick={() => setFilter(item as WorkbenchFilter)}
            >
              {sx.filters[item as keyof typeof sx.filters] || (locale === "en" ? "All" : "全部")}
            </button>
          ))}
        </div>
      </div>

      <div className="skills-layout">
        <section className="console-section" aria-label={sx.catalogLabel}>
          {visibleSkills.length > 0 ? (
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
                </article>
              ))}
            </div>
          ) : (
            <div style={{ padding: "40px 20px", textAlign: "center", border: "1px dashed var(--border-color)", borderRadius: "8px", color: "var(--text-muted)" }}>
              {locale === "en" ? "No custom skills match this filter." : "没有匹配此筛选器的自定义技能。"}
            </div>
          )}
        </section>

        <aside className="skills-sidebar" aria-label={sx.detailsRegion}>
          {selectedSkill ? (
            <>
              <div className="skills-rail-card skills-detail" style={{ marginBottom: "16px" }}>
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
                  <span>{locale === "en" ? "Workspace Draft" : "工作区草稿"}</span>
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
                </div>
                <div className="action-row" style={{ marginTop: "16px" }}>
                  <button className="console-action is-primary" type="button" onClick={onOpenSkillBuilder} style={{ flex: 1 }}>
                    {sx.actions.openBuilder}
                  </button>
                </div>
              </div>

              <div className="skills-rail-card skills-detail">
                <div className="section-header">
                  <div>
                    <span className="section-label">{sx.capabilityLoop}</span>
                    <h2>{sx.publishPath}</h2>
                  </div>
                </div>
                <div className="publish-steps" style={{ display: "flex", alignItems: "center", gap: "8px", margin: "14px 0", fontSize: "12px", color: "var(--text-muted)" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: "4px", color: selectedSkill.status === "draft" ? "var(--text-primary)" : "inherit", fontWeight: selectedSkill.status === "draft" ? 600 : 400 }}>
                    <Sparkles size={11} /> {sx.statuses.draft}
                  </span>
                  <ArrowRight size={11} />
                  <span style={{ display: "flex", alignItems: "center", gap: "4px", color: selectedSkill.status === "review" ? "var(--text-primary)" : "inherit", fontWeight: selectedSkill.status === "review" ? 600 : 400 }}>
                    <WandSparkles size={11} /> {sx.statuses.review}
                  </span>
                  <ArrowRight size={11} />
                  <span style={{ display: "flex", alignItems: "center", gap: "4px", color: selectedSkill.status === "published" ? "var(--text-primary)" : "inherit", fontWeight: selectedSkill.status === "published" ? 600 : 400 }}>
                    <CheckCircle2 size={11} /> {sx.statuses.published}
                  </span>
                </div>
                <div className="action-row" style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "12px" }}>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button className="console-action" type="button" onClick={onSaveSkillDraft} style={{ flex: 1 }} disabled={selectedSkill.status !== "draft"}>
                      {sx.actions.saveDraft}
                    </button>
                    <button className="console-action" type="button" onClick={onSubmitSkillReview} style={{ flex: 1 }} disabled={selectedSkill.status !== "draft"}>
                      {sx.actions.submitReview}
                    </button>
                  </div>
                  <button className="console-action is-primary" type="button" onClick={onPublishSkill} style={{ width: "100%" }} disabled={selectedSkill.status !== "review"}>
                    {sx.actions.publish}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div style={{ padding: "20px", textAlign: "center", border: "1px dashed var(--border-color)", borderRadius: "8px", color: "var(--text-muted)" }}>
              {locale === "en" ? "Select a custom skill to view detail metrics." : "选择一项自定义技能以查看详情属性。"}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

export default SkillsWorkbench;

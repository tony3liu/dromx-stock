import { useMemo, useState } from "react";
import { Star } from "lucide-react";
import type React from "react";
import type { AppContent, Locale } from "../i18n/content";
import { localizeSkill, type SkillItem } from "../data/skills";

type SkillsCenterPageProps = {
  locale: Locale;
  nav: React.ReactNode;
  skills: SkillItem[];
  selectedSkillId: string;
  onSelectSkill: (id: string) => void;
  t: AppContent;
};

function SkillsCenterPage({
  locale,
  nav,
  skills,
  selectedSkillId,
  onSelectSkill,
  t
}: SkillsCenterPageProps) {
  const [filter, setFilter] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const sx = t.skills;

  const localizedSkills = useMemo(
    () => skills.map((skill) => localizeSkill(skill, sx.catalog)),
    [skills, sx.catalog]
  );

  const publishedSkills = useMemo(
    () => localizedSkills.filter((skill) => skill.owner === "system" && skill.status === "published"),
    [localizedSkills]
  );

  const visibleSkills = useMemo(() => {
    return publishedSkills.filter((skill) => {
      if (filter === "free" && skill.pricing !== "free") return false;
      if (filter === "paid" && skill.pricing !== "paid") return false;
      if (filter === "installed" && !skill.installed) return false;

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
  }, [filter, publishedSkills, searchTerm]);

  const selectedSkill = localizedSkills.find((skill) => skill.id === selectedSkillId) ?? publishedSkills[0];

  const freeCount = publishedSkills.filter((skill) => skill.pricing === "free").length;
  const paidCount = publishedSkills.filter((skill) => skill.pricing === "paid").length;
  const installedCount = publishedSkills.filter((skill) => skill.installed).length;

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
          <span>{sx.counts.skills(publishedSkills.length)}</span>
          <span>{sx.counts.free(freeCount)}</span>
          <span>{sx.counts.paid(paidCount)}</span>
          <span>{sx.counts.installed(installedCount)}</span>
        </div>

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
            {["all", "free", "paid", "installed"].map((item) => (
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
                </article>
              ))}
            </div>
          </section>

          <aside className="skills-sidebar" aria-label={sx.detailsRegion}>
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
                  <span>{sx.publicSkill}</span>
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

                <div className="action-row" style={{ marginTop: "16px" }}>
                  <button className="console-action is-primary" type="button">
                    {selectedSkill.installed ? sx.actions.disable : sx.actions.install}
                  </button>
                  <button className="console-action" type="button">
                    {sx.actions.enable}
                  </button>
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

export default SkillsCenterPage;

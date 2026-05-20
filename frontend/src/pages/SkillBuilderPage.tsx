import type React from "react";
import type { AppContent, Locale } from "../i18n/content";
import { localizeSkill, type SkillItem } from "../data/skills";
import Breadcrumbs from "../components/Breadcrumbs";
import { CheckCircle2, WandSparkles } from "lucide-react";

type SkillBuilderPageProps = {
  locale: Locale;
  nav: React.ReactNode;
  onBackToStore: () => void;
  onSaveDraft: () => void;
  onSubmitReview: () => void;
  onPublish: () => void;
  skill: SkillItem;
  t: AppContent;
  onNavigate: (path: string) => void;
};

function SkillBuilderPage({ locale, nav, onBackToStore, onSaveDraft, onSubmitReview, onPublish, skill, t, onNavigate }: SkillBuilderPageProps) {
  const sx = t.skills;
  const bx = sx.builder;
  const localizedSkill = localizeSkill(skill, sx.catalog);

  return (
    <main className="builder-shell skills-builder-shell" lang={locale}>
      {nav}
      <section className="builder-workbench">
        <Breadcrumbs
          items={[
            { label: bx.breadcrumbConsole, path: "/console" },
            { label: bx.breadcrumbSkills, path: "/skills" },
            { label: bx.breadcrumbBuilder }
          ]}
          onNavigate={onNavigate}
        />

        <div className="builder-hero">
          <div className="builder-hero-copy">
            <span className="section-label">{bx.eyebrow}</span>
            <h1>{bx.title}</h1>
            <p>{bx.description}</p>
          </div>
          <div className="builder-status-card">
            <strong>{sx.statuses[localizedSkill.status]}</strong>
            <span>{localizedSkill.owner === "me" ? bx.mySkill : localizedSkill.publisher}</span>
          </div>
        </div>

        <div className="builder-grid">
          <div className="builder-main">
            <div className="builder-section">
              <div className="builder-section-head">
                <h2>{bx.details}</h2>
                <span className={`skill-status skill-status-${localizedSkill.status}`}>{sx.statuses[localizedSkill.status]}</span>
              </div>
              <div className="builder-list">
                <label className="builder-field">
                  <span>{bx.name}</span>
                  <input type="text" defaultValue={localizedSkill.name} />
                </label>
                <label className="builder-field">
                  <span>{bx.summary}</span>
                  <textarea rows={3} defaultValue={localizedSkill.summary} />
                </label>
                <label className="builder-field">
                  <span>{bx.toolsMcp}</span>
                  <textarea rows={3} defaultValue={localizedSkill.tools.join(", ")} />
                </label>
              </div>
            </div>

            <div className="builder-section">
              <div className="builder-section-head">
                <h2>{bx.inputsOutputs}</h2>
              </div>
              <div className="builder-list">
                <label className="builder-field">
                  <span>{bx.inputs}</span>
                  <textarea rows={3} defaultValue={localizedSkill.inputs.join(", ")} />
                </label>
                <label className="builder-field">
                  <span>{bx.outputs}</span>
                  <textarea rows={3} defaultValue={localizedSkill.outputs.join(", ")} />
                </label>
              </div>
            </div>
          </div>

          <aside className="builder-aside">
            <div className="builder-section builder-stick">
              <div className="builder-section-head">
                <h2>{bx.publishFlow}</h2>
              </div>
              <div className="publish-steps">
                <span><CheckCircle2 size={13} /> {sx.statuses.draft}</span>
                <WandSparkles size={13} />
                <span><WandSparkles size={13} /> {sx.statuses.review}</span>
                <CheckCircle2 size={13} />
                <span><CheckCircle2 size={13} /> {sx.statuses.published}</span>
              </div>
              <div className="action-row builder-actions">
                <button className="console-action is-primary" type="button" onClick={onSaveDraft}>
                  {sx.actions.saveDraft}
                </button>
                <button className="console-action" type="button" onClick={onSubmitReview}>
                  {sx.actions.submitForReview}
                </button>
                <button className="console-action" type="button" onClick={onPublish}>
                  {sx.actions.publish}
                </button>
                <button className="console-action" type="button" onClick={onBackToStore}>
                  {sx.actions.backToSkills}
                </button>
              </div>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}

export default SkillBuilderPage;

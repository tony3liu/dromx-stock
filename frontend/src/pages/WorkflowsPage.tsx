import type { AppContent, Locale, WorkflowData } from "../i18n/content";

type WorkflowsPageProps = {
  locale: Locale;
  workflows: WorkflowData[];
  wf: AppContent["console"]["workflows"];
  onCreateWorkflow: () => void;
  onEditWorkflow: (index: number) => void;
};

function WorkflowsPage({ locale, workflows, wf, onCreateWorkflow, onEditWorkflow }: WorkflowsPageProps) {
  const totalSteps = workflows.reduce((sum, w) => sum + w.steps.length, 0);
  const publishedCount = workflows.filter((w) => w.status === "published").length;

  return (
    <section className="console-main">
      <div className="console-summary agent-console-head">
        <span className="section-label">{locale === "en" ? "Workflow Operations" : "工作流操作"}</span>
        <h1>{wf.title}</h1>
        <p>{wf.description}</p>
        <div className="summary-metrics">
          <span>{locale === "en" ? `${workflows.length} Workflows` : `${workflows.length} 个工作流`}</span>
          <span>{locale === "en" ? `${totalSteps} Total Steps` : `${totalSteps} 个步骤`}</span>
          <span>{locale === "en" ? `${publishedCount} Published` : `${publishedCount} 个已发布`}</span>
        </div>
        <div className="action-row">
          <button className="console-action is-primary" type="button" onClick={onCreateWorkflow}>
            {wf.createLabel}
          </button>
        </div>
      </div>

      <section className="console-section" aria-label={locale === "en" ? "Workflows" : "工作流"}>
        <div className="section-header">
          <h2>{locale === "en" ? "All Workflows" : "全部工作流"}</h2>
        </div>

        {workflows.length === 0 ? (
          <div className="agent-registry">
            <article className="role-card agent-card">
              <strong style={{ color: "#f4efe3" }}>{locale === "en" ? "No workflows yet" : "暂无工作流"}</strong>
              <p>{locale === "en" ? "Create your first workflow to get started." : "创建第一个工作流开始使用。"}</p>
            </article>
          </div>
        ) : (
          <div className="agent-registry">
            {workflows.map((workflow, index) => (
              <article key={workflow.name} className="role-card agent-card">
                <div className="role-top">
                  <strong>{workflow.name}</strong>
                  <span className={`role-status workflow-${workflow.status}`}>
                    {workflow.status === "draft" ? wf.statusDraft : wf.statusPublished}
                  </span>
                </div>
                <p>{workflow.description}</p>
                <div className="agent-card-metrics">
                  <span>{wf.stepCount(workflow.steps.length)}</span>
                </div>
                <div className="agent-actions">
                  <button
                    className="console-action is-primary agent-action-main"
                    type="button"
                    onClick={() => onEditWorkflow(index)}
                  >
                    {wf.editLabel}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}

export default WorkflowsPage;

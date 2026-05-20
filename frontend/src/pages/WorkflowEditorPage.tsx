import { useState } from "react";
import type React from "react";
import type { AppContent, Locale, WorkflowData, WorkflowStep, WorkflowStepType } from "../i18n/content";

type WorkflowEditorPageProps = {
  workflow?: WorkflowData;
  breadcrumbs: React.ReactNode;
  locale: Locale;
  nav: React.ReactNode;
  wf: AppContent["console"]["workflows"];
  stepTypes: AppContent["console"]["workflowStepTypes"];
};

type EditableStep = WorkflowStep;

let stepIdCounter = 0;
function nextStepId(): string {
  stepIdCounter += 1;
  return `step-${Date.now()}-${stepIdCounter}`;
}

const STEP_TYPES: WorkflowStepType[] = ["start", "llm", "http-request", "code", "condition", "knowledge", "end"];

const CONFIG_FIELD_LABELS: Record<string, { en: string; zh: string }> = {
  inputs: { en: "Input Variables", zh: "输入变量" },
  model: { en: "Model", zh: "模型" },
  systemPrompt: { en: "System Prompt", zh: "系统提示词" },
  temperature: { en: "Temperature", zh: "温度" },
  maxTokens: { en: "Max Tokens", zh: "最大 Token 数" },
  method: { en: "Method", zh: "请求方法" },
  url: { en: "URL", zh: "URL" },
  headers: { en: "Headers", zh: "请求头" },
  body: { en: "Body", zh: "请求体" },
  language: { en: "Language", zh: "语言" },
  code: { en: "Code", zh: "代码" },
  variable: { en: "Variable", zh: "变量" },
  operator: { en: "Operator", zh: "运算符" },
  value: { en: "Value", zh: "值" },
  trueBranch: { en: "True Branch Label", zh: "True 分支标签" },
  falseBranch: { en: "False Branch Label", zh: "False 分支标签" },
  knowledgeBase: { en: "Knowledge Base", zh: "知识库" },
  query: { en: "Query", zh: "查询" },
  topK: { en: "Top K", zh: "Top K" },
  outputs: { en: "Output Variables", zh: "输出变量" },
  snippet: { en: "Snippet", zh: "代码片段" }
};

function fieldLabel(field: string, locale: Locale): string {
  const entry = CONFIG_FIELD_LABELS[field];
  return entry ? entry[locale === "en" ? "en" : "zh"] : field;
}

function createDefaultStep(type: WorkflowStepType): EditableStep {
  const config: Record<string, string> = {};
  if (type === "start") config.inputs = "";
  if (type === "llm") { config.model = ""; config.systemPrompt = ""; config.temperature = "0.7"; config.maxTokens = "4096"; }
  if (type === "http-request") { config.method = "GET"; config.url = ""; config.headers = ""; config.body = ""; }
  if (type === "code") { config.language = "python"; config.code = ""; }
  if (type === "condition") { config.variable = ""; config.operator = "equals"; config.value = ""; config.trueBranch = ""; config.falseBranch = ""; }
  if (type === "knowledge") { config.knowledgeBase = ""; config.query = ""; config.topK = "5"; }
  if (type === "end") config.outputs = "";
  return { id: nextStepId(), type, title: "", config };
}

function WorkflowEditorPage({ workflow, breadcrumbs, locale, nav, wf, stepTypes }: WorkflowEditorPageProps) {
  const initial = workflow;
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [status, setStatus] = useState<WorkflowData["status"]>(initial?.status ?? "draft");
  const [steps, setSteps] = useState<EditableStep[]>(
    initial?.steps.map((s) => ({ ...s, config: { ...s.config } })) ?? []
  );

  const updateStep = (index: number, patch: Partial<EditableStep>) => {
    setSteps((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  };

  const updateStepConfig = (index: number, key: string, value: string) => {
    setSteps((prev) =>
      prev.map((s, i) => (i === index ? { ...s, config: { ...s.config, [key]: value } } : s))
    );
  };

  const addStep = () => {
    setSteps((prev) => [...prev, createDefaultStep("llm")]);
  };

  const removeStep = (index: number) => {
    setSteps((prev) => prev.filter((_, i) => i !== index));
  };

  const moveStep = (index: number, direction: -1 | 1) => {
    setSteps((prev) => {
      const target = index + direction;
      if (target < 0 || target >= prev.length) return prev;
      const next = [...prev];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  };

  const handleTypeChange = (index: number, newType: WorkflowStepType) => {
    setSteps((prev) =>
      prev.map((s, i) => (i === index ? createDefaultStep(newType) : s))
    );
  };

  const statusBadgeClass = status === "published" ? "role-active" : "role-queued";

  return (
    <main className="builder-shell" lang={locale}>
      <div className="builder-sticky-head">
        {nav}
        {breadcrumbs}
      </div>

      <section className="builder-hero">
        <div className="builder-hero-copy">
          <span className="section-label">{locale === "en" ? "Workflow Editor" : "工作流编辑器"}</span>
          <label className="builder-field">
            <span>{locale === "en" ? "Workflow Name" : "工作流名称"}</span>
            <input
              aria-label={locale === "en" ? "Workflow name" : "工作流名称"}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="builder-field">
            <span>{locale === "en" ? "Description" : "描述"}</span>
            <textarea
              aria-label={locale === "en" ? "Description" : "描述"}
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </label>
        </div>
        <div className="builder-status-card">
          <strong>{locale === "en" ? "Status" : "状态"}</strong>
          <span className={`role-status ${statusBadgeClass}`}>
            {status === "draft" ? wf.statusDraft : wf.statusPublished}
          </span>
        </div>
      </section>

      <div className="builder-toolbar">
        <div className="builder-toolbar-meta">
          <span>{wf.stepCount(steps.length)}</span>
        </div>
        <div className="builder-toolbar-actions">
          <button
            className="console-action is-primary"
            type="button"
            onClick={() => setStatus(status === "draft" ? "published" : "draft")}
          >
            {status === "draft" ? wf.publish : wf.unpublish}
          </button>
          <button className="console-action" type="button">
            {wf.duplicate}
          </button>
          <button className="console-action" type="button">
            {wf.runDebug}
          </button>
        </div>
      </div>

      <div className="builder-grid">
        <div className="builder-main">
          {/* Steps section */}
          <section className="builder-section">
            <div className="builder-section-head">
              <h2>{locale === "en" ? "Workflow Steps" : "工作流步骤"}</h2>
              <button className="console-action is-primary" type="button" onClick={addStep}>
                {wf.addStep}
              </button>
            </div>

            {steps.length === 0 ? (
              <article className="builder-item">
                <strong>{locale === "en" ? "No steps yet" : "暂无步骤"}</strong>
                <p>{wf.noSteps}</p>
              </article>
            ) : (
              <div className="builder-list">
                {steps.map((step, index) => {
                  const typeInfo = stepTypes[step.type as WorkflowStepType];
                  const fields = typeInfo ? [...typeInfo.fields] : [];
                  // Also include snippet field for code steps
                  if (step.type === "code" && !fields.includes("snippet")) fields.push("snippet");

                  return (
                    <article key={step.id} className="builder-item workflow-step-card">
                      <div className="builder-section-head">
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <span className="step-number">{wf.stepNumber(index + 1)}</span>
                          <select
                            className="step-type-select"
                            aria-label={locale === "en" ? "Step type" : "步骤类型"}
                            value={step.type}
                            onChange={(e) => handleTypeChange(index, e.target.value as WorkflowStepType)}
                          >
                            {STEP_TYPES.map((t) => (
                              <option key={t} value={t}>
                                {stepTypes[t].label}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div className="step-order-buttons">
                          <button
                            className="console-action"
                            type="button"
                            aria-label={wf.moveUp}
                            disabled={index === 0}
                            onClick={() => moveStep(index, -1)}
                          >
                            &#9650;
                          </button>
                          <button
                            className="console-action"
                            type="button"
                            aria-label={wf.moveDown}
                            disabled={index === steps.length - 1}
                            onClick={() => moveStep(index, 1)}
                          >
                            &#9660;
                          </button>
                          <button
                            className="console-action"
                            type="button"
                            aria-label={wf.removeStep}
                            onClick={() => removeStep(index)}
                          >
                            &#10005;
                          </button>
                        </div>
                      </div>

                      <label className="builder-field">
                        <span>{locale === "en" ? "Step Title" : "步骤标题"}</span>
                        <input
                          aria-label={locale === "en" ? "Step title" : "步骤标题"}
                          value={step.title}
                          onChange={(e) => updateStep(index, { title: e.target.value })}
                        />
                      </label>

                      {fields.length > 0 && (
                        <div className="step-config">
                          {fields.map((field) => (
                            <label key={field} className="builder-field">
                              <span>{fieldLabel(field, locale)}</span>
                              {field === "code" || field === "body" || field === "systemPrompt" ? (
                                <textarea
                                  aria-label={fieldLabel(field, locale)}
                                  rows={4}
                                  value={step.config[field] ?? ""}
                                  onChange={(e) => updateStepConfig(index, field, e.target.value)}
                                />
                              ) : (
                                <input
                                  aria-label={fieldLabel(field, locale)}
                                  value={step.config[field] ?? ""}
                                  onChange={(e) => updateStepConfig(index, field, e.target.value)}
                                />
                              )}
                            </label>
                          ))}
                        </div>
                      )}
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        </div>

        <aside className="builder-aside">
          <section className="builder-section">
            <div className="builder-section-head">
              <h2>{wf.debugTitle}</h2>
            </div>
            <div className="builder-debug-stack">
              <div className="builder-debug-item">
                <span>{locale === "en" ? "Status" : "状态"}</span>
                <strong>{locale === "en" ? "No debug session" : "无调试会话"}</strong>
              </div>
            </div>
            <p style={{ color: "#b8b0a3", lineHeight: "1.55" }}>{wf.debugPlaceholder}</p>
          </section>

        </aside>
      </div>
    </main>
  );
}

export default WorkflowEditorPage;

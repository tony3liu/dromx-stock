import { useMemo, useState } from "react";
import type React from "react";
import type { Locale, RoleAgent } from "../i18n/content";

type AgentBuilderPageProps = {
  agent?: RoleAgent;
  breadcrumbs: React.ReactNode;
  locale: Locale;
  nav: React.ReactNode;
};

type EditableItem = {
  title: string;
  detail: string;
};

type EditableSkill = {
  name: string;
  detail: string;
};

function AgentBuilderPage({ agent, breadcrumbs, locale, nav }: AgentBuilderPageProps) {
  const initialDraft = useMemo(
    () =>
      agent ?? {
        name: locale === "en" ? "New Role Agent" : "新建角色 Agent",
        role: locale === "en" ? "Untitled role" : "未命名角色",
        status: "idle",
        skills: [],
        currentTask: locale === "en" ? "Define the role before release." : "先定义角色，再进入发布流程。",
        memorySignal: locale === "en" ? "No memory yet" : "暂无记忆"
      },
    [agent, locale]
  );

  const [name, setName] = useState(initialDraft.name);
  const [role, setRole] = useState(initialDraft.role);
  const [currentTask, setCurrentTask] = useState(initialDraft.currentTask);
  const [workflows, setWorkflows] = useState<EditableItem[]>([
    {
      title: locale === "en" ? "Lead qualification" : "线索判断",
      detail: locale === "en" ? "Route qualified leads into outbound sequences." : "把符合条件的线索路由到外呼序列。"
    },
    {
      title: locale === "en" ? "Outbound sequence" : "外呼序列",
      detail: locale === "en" ? "Coordinate message, timing, and follow-up steps." : "协调消息、时机和跟进步骤。"
    }
  ]);
  const [skills, setSkills] = useState<EditableSkill[]>(
    initialDraft.skills.length
      ? initialDraft.skills.map((skill) => ({
          name: skill,
          detail: locale === "en" ? "Reusable capability bound to this role." : "绑定到该角色的可复用能力。"
        }))
      : []
  );
  const [mcpTools, setMcpTools] = useState<EditableItem[]>([
    { title: "CRM MCP", detail: locale === "en" ? "Lead and pipeline access." : "线索与管道访问。" },
    { title: "Browser Tool", detail: locale === "en" ? "Browse sources and validate facts." : "浏览来源并校验事实。" },
    { title: "Spreadsheet Tool", detail: locale === "en" ? "Structure operating numbers." : "结构化经营数字。" }
  ]);

  const draft = {
    ...initialDraft,
    name,
    role,
    currentTask,
    skills
  };

  const addWorkflow = () => {
    setWorkflows((items) => [
      ...items,
      {
        title: `${locale === "en" ? "Workflow" : "工作流"} ${items.length + 1}`,
        detail: locale === "en" ? "Describe the new operational step." : "描述新的操作步骤。"
      }
    ]);
  };

  const addSkill = () => {
    setSkills((items) => [
      ...items,
      {
        name: locale === "en" ? "New skill" : "新技能",
        detail: locale === "en" ? "Describe what this skill lets the agent do." : "描述这个技能让 Agent 能做什么。"
      }
    ]);
  };

  const addMcpTool = () => {
    setMcpTools((items) => [
      ...items,
      {
        title: `MCP ${items.length + 1}`,
        detail: locale === "en" ? "Attach a tool integration." : "接入一个工具集成。"
      }
    ]);
  };

  return (
    <main className="builder-shell" lang={locale}>
      <div className="builder-sticky-head">
        {nav}
        {breadcrumbs}
      </div>

      <section className="builder-hero">
        <div className="builder-hero-copy">
          <span className="section-label">{locale === "en" ? "Editing Role Agent" : "正在编辑角色 Agent"}</span>
          <h1>{draft.name} Builder</h1>
          <p>{draft.role}</p>
        </div>
        <div className="builder-status-card">
          <strong>{locale === "en" ? "Release State" : "发布状态"}</strong>
          <span className={`role-status role-${draft.status}`}>{draft.status}</span>
        </div>
      </section>

      <section className="builder-toolbar" aria-label={locale === "en" ? "Builder actions" : "编辑器操作"}>
        <div className="builder-toolbar-meta">
          <span>{draft.memorySignal}</span>
          <span>{locale === "en" ? "2 workflows" : "2 个工作流"}</span>
          <span>{locale === "en" ? "2 skills" : "2 个技能"}</span>
          <span>{locale === "en" ? "3 MCP tools" : "3 个 MCP 工具"}</span>
        </div>
        <div className="builder-toolbar-actions">
          <button className="console-action is-primary" type="button">
            {locale === "en" ? "Publish" : "发布"}
          </button>
          <button className="console-action" type="button">
            {locale === "en" ? "Unpublish" : "下架"}
          </button>
          <button className="console-action" type="button">
            {locale === "en" ? "Duplicate" : "复制"}
          </button>
          <button className="console-action is-primary" type="button">
            {locale === "en" ? "Run Debug" : "运行调试"}
          </button>
        </div>
      </section>

      <section className="builder-grid">
        <div className="builder-main">
          <section className="builder-section builder-overview">
            <div className="builder-section-head">
              <h2>{locale === "en" ? "Overview" : "概览"}</h2>
            </div>
            <label className="builder-field">
              <span>{locale === "en" ? "Agent name" : "Agent 名称"}</span>
              <input aria-label="Agent name" value={name} onChange={(event) => setName(event.target.value)} />
            </label>
            <label className="builder-field">
              <span>{locale === "en" ? "Role identity" : "角色身份"}</span>
              <input aria-label="Role identity" value={role} onChange={(event) => setRole(event.target.value)} />
            </label>
            <label className="builder-field">
              <span>{locale === "en" ? "Current task" : "当前任务"}</span>
              <textarea
                aria-label="Current task"
                rows={3}
                value={currentTask}
                onChange={(event) => setCurrentTask(event.target.value)}
              />
            </label>
          </section>

          <section className="builder-section">
            <div className="builder-section-head">
              <h2>{locale === "en" ? "Workflows" : "工作流"}</h2>
              <button className="console-action is-primary" type="button" onClick={addWorkflow}>
                {locale === "en" ? "Add Workflow" : "添加工作流"}
              </button>
            </div>
            <div className="builder-list">
              {workflows.map((workflow, index) => (
                <article className="builder-item" key={`${workflow.title}-${index}`}>
                  <label className="builder-field">
                    <span>{`${locale === "en" ? "Workflow" : "工作流"} ${index + 1} title`}</span>
                    <input
                      aria-label={`Workflow ${index + 1} title`}
                      value={workflow.title}
                      onChange={(event) => {
                        const nextTitle = event.target.value;
                        setWorkflows((items) =>
                          items.map((item, currentIndex) =>
                            currentIndex === index ? { ...item, title: nextTitle } : item
                          )
                        );
                      }}
                    />
                  </label>
                  <label className="builder-field">
                    <span>{locale === "en" ? "Description" : "描述"}</span>
                    <textarea
                      aria-label={`Workflow ${index + 1} description`}
                      rows={3}
                      value={workflow.detail}
                      onChange={(event) => {
                        const nextDetail = event.target.value;
                        setWorkflows((items) =>
                          items.map((item, currentIndex) =>
                            currentIndex === index ? { ...item, detail: nextDetail } : item
                          )
                        );
                      }}
                    />
                  </label>
                </article>
              ))}
            </div>
          </section>

          <section className="builder-section">
            <div className="builder-section-head">
              <h2>{locale === "en" ? "Skills" : "技能"}</h2>
              <button className="console-action is-primary" type="button" onClick={addSkill}>
                {locale === "en" ? "Add Skill" : "添加技能"}
              </button>
            </div>
            <div className="builder-list">
              {skills.length ? (
                skills.map((skill, index) => (
                  <article className="builder-item" key={`${skill}-${index}`}>
                    <label className="builder-field">
                      <span>{`${locale === "en" ? "Skill" : "技能"} ${index + 1}`}</span>
                      <input
                        aria-label={`Skill ${index + 1}`}
                        value={skill.name}
                        onChange={(event) => {
                          const nextName = event.target.value;
                          setSkills((items) =>
                            items.map((item, currentIndex) =>
                              currentIndex === index ? { ...item, name: nextName } : item
                            )
                          );
                        }}
                      />
                    </label>
                    <label className="builder-field">
                      <span>{locale === "en" ? "Capability note" : "能力说明"}</span>
                      <textarea
                        aria-label={`Skill ${index + 1} note`}
                        rows={3}
                        value={skill.detail}
                        onChange={(event) => {
                          const nextDetail = event.target.value;
                          setSkills((items) =>
                            items.map((item, currentIndex) =>
                              currentIndex === index ? { ...item, detail: nextDetail } : item
                            )
                          );
                        }}
                      />
                    </label>
                  </article>
                ))
              ) : (
                <article className="builder-item">
                  <strong>{locale === "en" ? "Add your first skill" : "添加第一个技能"}</strong>
                  <p>{locale === "en" ? "Start with a capability that makes this role useful." : "先定义一个让该角色可用的能力。"}</p>
                </article>
              )}
            </div>
          </section>

          <section className="builder-section">
            <div className="builder-section-head">
              <h2>{locale === "en" ? "MCP & Tools" : "MCP 与工具"}</h2>
              <button className="console-action is-primary" type="button" onClick={addMcpTool}>
                {locale === "en" ? "Bind MCP Tool" : "绑定 MCP 工具"}
              </button>
            </div>
            <div className="builder-list">
              {mcpTools.map((tool, index) => (
                <article className="builder-item" key={`${tool.title}-${index}`}>
                  <label className="builder-field">
                    <span>{`${locale === "en" ? "Tool" : "工具"} ${index + 1}`}</span>
                    <input
                      aria-label={`Tool ${index + 1}`}
                      value={tool.title}
                      onChange={(event) => {
                        const nextTitle = event.target.value;
                        setMcpTools((items) =>
                          items.map((item, currentIndex) =>
                            currentIndex === index ? { ...item, title: nextTitle } : item
                          )
                        );
                      }}
                    />
                  </label>
                  <label className="builder-field">
                    <span>{locale === "en" ? "Access note" : "访问说明"}</span>
                    <textarea
                      aria-label={`Tool ${index + 1} access note`}
                      rows={3}
                      value={tool.detail}
                      onChange={(event) => {
                        const nextDetail = event.target.value;
                        setMcpTools((items) =>
                          items.map((item, currentIndex) =>
                            currentIndex === index ? { ...item, detail: nextDetail } : item
                          )
                        );
                      }}
                    />
                  </label>
                </article>
              ))}
            </div>
          </section>
        </div>

        <aside className="builder-aside">
          <section className="builder-section">
            <div className="builder-section-head">
              <h2>{locale === "en" ? "Debug Console" : "调试控制台"}</h2>
            </div>
            <p>
              {locale === "en"
                ? "Run a sample task, inspect workflow steps, skill calls, tool usage, and output quality."
                : "运行样例任务，检查工作流步骤、技能调用、工具使用和输出质量。"}
            </p>
            <div className="builder-debug-stack">
              <div className="builder-debug-item">
                <span>{locale === "en" ? "Signal" : "信号"}</span>
                <strong>{locale === "en" ? "Ready to test" : "可开始测试"}</strong>
              </div>
              <div className="builder-debug-item">
                <span>{locale === "en" ? "Checks" : "检查项"}</span>
                <strong>{locale === "en" ? "Workflow, skill, tool" : "工作流、技能、工具"}</strong>
              </div>
            </div>
          </section>

        </aside>
      </section>
    </main>
  );
}

export default AgentBuilderPage;

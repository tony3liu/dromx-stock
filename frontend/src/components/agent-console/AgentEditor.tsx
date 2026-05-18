import type { Locale, RoleAgent } from "../../i18n/content";

type AgentEditorProps = {
  agent: RoleAgent;
  locale: Locale;
};

function AgentEditor({ agent, locale }: AgentEditorProps) {
  return (
    <section className="console-section role-editor" aria-label={`${agent.name} editor`}>
      <div className="section-header">
        <div>
          <span className="section-label">{locale === "en" ? "Editing Role Agent" : "正在编辑角色 Agent"}</span>
          <h2>{agent.name} Builder</h2>
        </div>
      </div>
      <div className="editor-identity">
        <strong>{agent.role}</strong>
        <p>{agent.currentTask}</p>
      </div>

      <section className="editor-block">
        <div className="editor-block-head">
          <h2>{locale === "en" ? "Workflows" : "工作流"}</h2>
          <button className="console-action" type="button">
            {locale === "en" ? "Add Workflow" : "添加工作流"}
          </button>
        </div>
        <div className="editor-list">
          <span>{locale === "en" ? "Lead qualification" : "线索判断"}</span>
          <span>{locale === "en" ? "Outbound sequence" : "外呼序列"}</span>
        </div>
      </section>

      <section className="editor-block">
        <div className="editor-block-head">
          <h2>{locale === "en" ? "Skills" : "技能"}</h2>
          <button className="console-action" type="button">
            {locale === "en" ? "Add Skill" : "添加技能"}
          </button>
        </div>
        <div className="editor-list">
          {agent.skills.map((skill) => (
            <span key={skill}>{skill}</span>
          ))}
        </div>
      </section>

      <section className="editor-block">
        <div className="editor-block-head">
          <h2>{locale === "en" ? "MCP & Tools" : "MCP 与工具"}</h2>
          <button className="console-action" type="button">
            {locale === "en" ? "Bind MCP Tool" : "绑定 MCP 工具"}
          </button>
        </div>
        <div className="editor-list">
          <span>CRM MCP</span>
          <span>Browser Tool</span>
          <span>Spreadsheet Tool</span>
        </div>
      </section>

      <section className="editor-block debug-block">
        <div className="editor-block-head">
          <h2>{locale === "en" ? "Debug Console" : "调试控制台"}</h2>
          <button className="console-action is-primary" type="button">
            {locale === "en" ? "Run Debug" : "运行调试"}
          </button>
        </div>
        <p>
          {locale === "en"
            ? "Test this role Agent against a sample task and inspect workflow steps, skill calls, MCP usage, and output quality."
            : "用样例任务测试该角色 Agent，并检查工作流步骤、技能调用、MCP 使用和输出质量。"}
        </p>
      </section>
    </section>
  );
}

export default AgentEditor;

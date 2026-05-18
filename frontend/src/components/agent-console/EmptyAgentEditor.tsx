import type { Locale } from "../../i18n/content";

type EmptyAgentEditorProps = {
  locale: Locale;
};

function EmptyAgentEditor({ locale }: EmptyAgentEditorProps) {
  return (
    <section className="console-section empty-editor">
      <span className="section-label">{locale === "en" ? "Agent Builder" : "Agent 构建器"}</span>
      <h2>{locale === "en" ? "Select a role Agent to edit" : "选择一个角色 Agent 进行编辑"}</h2>
      <p>
        {locale === "en"
          ? "Open an Agent to configure workflows, skills, MCP tools, memory, debug runs, and release state."
          : "打开一个 Agent 后，可以配置工作流、技能、MCP 工具、记忆、调试运行和发布状态。"}
      </p>
    </section>
  );
}

export default EmptyAgentEditor;

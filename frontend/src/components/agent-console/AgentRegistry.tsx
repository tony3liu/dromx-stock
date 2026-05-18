import type { AppContent, Locale } from "../../i18n/content";

type AgentRegistryProps = {
  locale: Locale;
  onSelectAgent: (index: number) => void;
  roleAgentsTitle: string;
  roles: AppContent["console"]["roles"];
  selectedAgentIndex: number;
};

function AgentRegistry({ locale, onSelectAgent, roleAgentsTitle, roles, selectedAgentIndex }: AgentRegistryProps) {
  return (
    <section className="console-section">
      <div className="section-header">
        <div>
          <span className="section-label">{locale === "en" ? "Agent Registry" : "Agent 注册表"}</span>
          <h2>{roleAgentsTitle}</h2>
        </div>
      </div>
      <div className="agent-registry">
        {roles.map((agent, index) => (
          <article className={`role-card agent-card ${index === selectedAgentIndex ? "is-selected" : ""}`} key={agent.name}>
            <div className="role-top">
              <div>
                <h2>{agent.name}</h2>
                <span>{agent.role}</span>
              </div>
              <span className={`role-status role-${agent.status}`}>{agent.status}</span>
            </div>
            <p>{agent.currentTask}</p>
            <div className="agent-card-metrics">
              <span>{index + 2} workflows</span>
              <span>{agent.skills.length} skills</span>
              <span>{index + 1} MCP</span>
              <span>{agent.memorySignal}</span>
            </div>
            <div className="role-skills">
              {agent.skills.map((skill) => (
                <span key={skill}>{skill}</span>
              ))}
            </div>
            <div className="agent-actions">
              <button
                className="console-action is-primary"
                type="button"
                aria-label={`Edit ${agent.name}`}
                onClick={() => onSelectAgent(index)}
              >
                {locale === "en" ? "Edit" : "编辑"}
              </button>
              <button
                className="console-action"
                type="button"
                aria-label={`Debug ${agent.name}`}
                onClick={() => onSelectAgent(index)}
              >
                {locale === "en" ? "Debug" : "调试"}
              </button>
              <button className="console-action" type="button" aria-label={`Publish ${agent.name}`}>
                {locale === "en" ? "Publish" : "发布"}
              </button>
              <button className="console-action" type="button" aria-label={`Unpublish ${agent.name}`}>
                {locale === "en" ? "Unpublish" : "下架"}
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default AgentRegistry;

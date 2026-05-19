import type { AppContent, Locale } from "../../i18n/content";

type AgentRegistryProps = {
  locale: Locale;
  onOpenAgentBuilder: (index: number) => void;
  onSelectAgent: (index: number) => void;
  roleAgentsTitle: string;
  roles: Array<AppContent["console"]["roles"][number] & { originalIndex?: number }>;
  selectedAgentIndex: number;
};

function AgentRegistry({ locale, onOpenAgentBuilder, onSelectAgent, roleAgentsTitle, roles, selectedAgentIndex }: AgentRegistryProps) {
  return (
    <section className="console-section" aria-label={roleAgentsTitle}>
      <div className="section-header">
        <div>
          <span className="section-label">{locale === "en" ? "Agent Registry" : "Agent 注册表"}</span>
          <h2>{roleAgentsTitle}</h2>
        </div>
      </div>
      <div className="agent-registry">
        {roles.map((agent, index) => (
          <article
            className={`role-card agent-card ${(agent.originalIndex ?? index) === selectedAgentIndex ? "is-selected" : ""}`}
            key={agent.name}
            role="button"
            tabIndex={0}
            aria-label={agent.name}
            onClick={() => onSelectAgent(agent.originalIndex ?? index)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelectAgent(agent.originalIndex ?? index);
              }
            }}
          >
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
                className="console-action is-primary agent-action-main"
                type="button"
                aria-label={`Edit ${agent.name}`}
                onClick={(event) => {
                  event.stopPropagation();
                  onOpenAgentBuilder(agent.originalIndex ?? index);
                }}
              >
                {locale === "en" ? "Edit" : "编辑"}
              </button>
              <button
                className="console-action agent-action-secondary"
                type="button"
                aria-label={`Debug ${agent.name}`}
                onClick={(event) => {
                  event.stopPropagation();
                  onOpenAgentBuilder(agent.originalIndex ?? index);
                }}
              >
                {locale === "en" ? "Debug" : "调试"}
              </button>
              <div className="agent-actions-tertiary">
                <button className="console-action agent-action-tertiary" type="button" aria-label={`Publish ${agent.name}`} onClick={(event) => event.stopPropagation()}>
                  {locale === "en" ? "Publish" : "发布"}
                </button>
                <button className="console-action agent-action-tertiary" type="button" aria-label={`Unpublish ${agent.name}`} onClick={(event) => event.stopPropagation()}>
                  {locale === "en" ? "Unpublish" : "下架"}
                </button>
                <button className="console-action agent-action-tertiary" type="button" aria-label={`Copy ${agent.name}`} onClick={(event) => event.stopPropagation()}>
                  {locale === "en" ? "Copy" : "复制"}
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default AgentRegistry;

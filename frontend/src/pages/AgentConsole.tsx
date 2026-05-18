import type { AppContent, Locale, RoleAgent } from "../i18n/content";
import AgentConsoleSummary from "../components/agent-console/AgentConsoleSummary";
import AgentEditor from "../components/agent-console/AgentEditor";
import AgentRegistry from "../components/agent-console/AgentRegistry";
import ConsoleHeader from "../components/agent-console/ConsoleHeader";
import ConsoleSidebar from "../components/agent-console/ConsoleSidebar";
import EmptyAgentEditor from "../components/agent-console/EmptyAgentEditor";

type AgentConsoleProps = {
  isEditingAgent: boolean;
  locale: Locale;
  onBackHome: () => void;
  onSelectAgent: (index: number) => void;
  onToggleLocale: () => void;
  selectedAgent: RoleAgent;
  selectedAgentIndex: number;
  t: AppContent;
};

function AgentConsole({
  isEditingAgent,
  locale,
  onBackHome,
  onSelectAgent,
  onToggleLocale,
  selectedAgent,
  selectedAgentIndex,
  t
}: AgentConsoleProps) {
  return (
    <main className="console-shell" lang={locale}>
      <ConsoleHeader onBackHome={onBackHome} onToggleLocale={onToggleLocale} t={t} />
      <section className="console-grid">
        <ConsoleSidebar items={t.console.nav} />

        <section className="console-main">
          <AgentConsoleSummary locale={locale} />
          <AgentRegistry
            locale={locale}
            onSelectAgent={onSelectAgent}
            roleAgentsTitle={t.console.roleAgents}
            roles={t.console.roles}
            selectedAgentIndex={selectedAgentIndex}
          />
        </section>

        <aside className="console-aside">
          {isEditingAgent ? <AgentEditor agent={selectedAgent} locale={locale} /> : <EmptyAgentEditor locale={locale} />}
        </aside>
      </section>
    </main>
  );
}

export default AgentConsole;

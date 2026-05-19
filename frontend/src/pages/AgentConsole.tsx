import type { AppContent, Locale } from "../i18n/content";
import AgentConsoleSummary from "../components/agent-console/AgentConsoleSummary";
import AgentRegistry from "../components/agent-console/AgentRegistry";
import ConsoleSidebar from "../components/agent-console/ConsoleSidebar";
import type React from "react";

type AgentConsoleProps = {
  locale: Locale;
  nav: React.ReactNode;
  onCreateAgent: () => void;
  onFilterStatus: () => void;
  onOpenAgentBuilder: (index: number) => void;
  onSearchRoles: () => void;
  onSearchTermChange: (value: string) => void;
  onSelectAgent: (index: number) => void;
  roleFilter: "all" | "active" | "review" | "queued";
  roles: AppContent["console"]["roles"];
  searchInputRef: React.RefObject<HTMLInputElement | null>;
  searchTerm: string;
  selectedAgentIndex: number;
  t: AppContent;
};

function AgentConsole({
  locale,
  nav,
  onCreateAgent,
  onFilterStatus,
  onOpenAgentBuilder,
  onSearchRoles,
  onSearchTermChange,
  onSelectAgent,
  roleFilter,
  roles,
  searchInputRef,
  searchTerm,
  selectedAgentIndex,
  t
}: AgentConsoleProps) {
  return (
    <main className="console-shell" lang={locale}>
      {nav}
      <section className="console-grid">
        <ConsoleSidebar items={t.console.nav} />

        <section className="console-main">
          <AgentConsoleSummary
            locale={locale}
            onCreateAgent={onCreateAgent}
            onFilterStatus={onFilterStatus}
            onSearchRoles={onSearchRoles}
            onSearchTermChange={onSearchTermChange}
            roleFilter={roleFilter}
            searchInputRef={searchInputRef}
            searchTerm={searchTerm}
          />
          <AgentRegistry
            locale={locale}
            roleAgentsTitle={t.console.roleAgents}
            roles={roles}
            selectedAgentIndex={selectedAgentIndex}
            onOpenAgentBuilder={onOpenAgentBuilder}
            onSelectAgent={onSelectAgent}
          />
        </section>
      </section>
    </main>
  );
}

export default AgentConsole;

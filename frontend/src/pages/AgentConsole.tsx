import type { AppContent, Locale, StoreAgent, WorkflowData } from "../i18n/content";
import AgentConsoleSummary from "../components/agent-console/AgentConsoleSummary";
import AgentRegistry from "../components/agent-console/AgentRegistry";
import ConsoleSidebar from "../components/agent-console/ConsoleSidebar";
import RoleAgentsStore from "./RoleAgentsStore";
import WorkflowsPage from "./WorkflowsPage";
import type React from "react";

type ConsoleSection = "agents" | "workflows" | "store";

type AgentConsoleProps = {
  locale: Locale;
  nav: React.ReactNode;
  activeFilters: Set<"active" | "review" | "queued">;
  availableStatuses: Array<"active" | "review" | "queued">;
  consoleSection: ConsoleSection;
  isSearchVisible: boolean;
  selectedAgentIndex: number;
  searchTerm: string;
  searchInputRef: React.RefObject<HTMLInputElement | null>;
  roles: Array<AppContent["console"]["roles"][number] & { originalIndex?: number }>;
  workflows: WorkflowData[];
  storeAgents: StoreAgent[];
  store: AppContent["console"]["store"];
  t: AppContent;
  onCreateAgent: () => void;
  onToggleFilter: (status: "active" | "review" | "queued") => void;
  onOpenAgentBuilder: (index: number) => void;
  onToggleSearch: () => void;
  onSearchTermChange: (value: string) => void;
  onSelectAgent: (index: number) => void;
  onNavigateSection: (section: ConsoleSection) => void;
  onCreateWorkflow: () => void;
  onEditWorkflow: (index: number) => void;
  onUseAgent: (index: number) => void;
};

function AgentConsole({
  locale,
  nav,
  activeFilters,
  availableStatuses,
  consoleSection,
  isSearchVisible,
  searchTerm,
  searchInputRef,
  roles,
  workflows,
  storeAgents,
  store,
  t,
  onCreateAgent,
  onToggleFilter,
  onOpenAgentBuilder,
  onToggleSearch,
  onSearchTermChange,
  onSelectAgent,
  onNavigateSection,
  onCreateWorkflow,
  onEditWorkflow,
  onUseAgent,
  selectedAgentIndex
}: AgentConsoleProps) {
  const navItems = [...t.console.nav];
  const activeNavIndex =
    consoleSection === "agents" ? 1 : consoleSection === "workflows" ? 2 : 3;

  const handleNav = (index: number) => {
    if (index === 1) onNavigateSection("agents");
    else if (index === 2) onNavigateSection("workflows");
    else if (index === 3) onNavigateSection("store");
  };

  return (
    <main className="console-shell" lang={locale}>
      {nav}
      <section className="console-grid">
        <ConsoleSidebar items={navItems} activeIndex={activeNavIndex} onNavigate={handleNav} />

        {consoleSection === "agents" ? (
          <section className="console-main">
            <AgentConsoleSummary
              locale={locale}
              activeFilters={activeFilters}
              availableStatuses={availableStatuses}
              isSearchVisible={isSearchVisible}
              onCreateAgent={onCreateAgent}
              onToggleFilter={onToggleFilter}
              onToggleSearch={onToggleSearch}
              onSearchTermChange={onSearchTermChange}
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
        ) : consoleSection === "workflows" ? (
          <WorkflowsPage
            locale={locale}
            workflows={workflows}
            wf={t.console.workflows}
            onCreateWorkflow={onCreateWorkflow}
            onEditWorkflow={onEditWorkflow}
          />
        ) : (
          <RoleAgentsStore
            locale={locale}
            agents={storeAgents}
            store={store}
            onUseAgent={onUseAgent}
          />
        )}
      </section>
    </main>
  );
}

export default AgentConsole;

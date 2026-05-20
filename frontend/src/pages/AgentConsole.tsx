import type { AppContent, Locale, StoreAgent, WorkflowData } from "../i18n/content";
import AgentConsoleSummary from "../components/agent-console/AgentConsoleSummary";
import AgentRegistry from "../components/agent-console/AgentRegistry";
import ConsoleSidebar from "../components/agent-console/ConsoleSidebar";
import WorkflowsPage from "./WorkflowsPage";
import SkillsWorkbench from "../components/agent-console/SkillsWorkbench";
import GpuDashboard from "../components/agent-console/GpuDashboard";
import type { SkillItem } from "../data/skills";
import type React from "react";

type ConsoleSection = "agents" | "skills" | "workflows" | "gpu" | "swarm";

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
  skills: SkillItem[];
  selectedSkillId: string;
  onSelectSkill: (id: string) => void;
  onCreateSkill: () => void;
  onOpenSkillBuilder: () => void;
  onSaveSkillDraft: () => void;
  onSubmitSkillReview: () => void;
  onPublishSkill: () => void;
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
  selectedAgentIndex,
  skills,
  selectedSkillId,
  onSelectSkill,
  onCreateSkill,
  onOpenSkillBuilder,
  onSaveSkillDraft,
  onSubmitSkillReview,
  onPublishSkill
}: AgentConsoleProps) {
  const navItems = [...t.console.nav];
  const activeNavIndex =
    consoleSection === "agents"
      ? 0
      : consoleSection === "swarm"
      ? 1
      : consoleSection === "skills"
      ? 2
      : consoleSection === "workflows"
      ? 3
      : 4;

  const handleNav = (index: number) => {
    if (index === 0) onNavigateSection("agents");
    else if (index === 1) onNavigateSection("swarm");
    else if (index === 2) onNavigateSection("skills");
    else if (index === 3) onNavigateSection("workflows");
    else if (index === 4) onNavigateSection("gpu");
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
        ) : consoleSection === "skills" ? (
          <SkillsWorkbench
            locale={locale}
            skills={skills}
            selectedSkillId={selectedSkillId}
            onSelectSkill={onSelectSkill}
            onCreateSkill={onCreateSkill}
            onOpenSkillBuilder={onOpenSkillBuilder}
            onSaveSkillDraft={onSaveSkillDraft}
            onSubmitSkillReview={onSubmitSkillReview}
            onPublishSkill={onPublishSkill}
            t={t}
          />
        ) : consoleSection === "workflows" ? (
          <WorkflowsPage
            locale={locale}
            workflows={workflows}
            wf={t.console.workflows}
            onCreateWorkflow={onCreateWorkflow}
            onEditWorkflow={onEditWorkflow}
          />
        ) : consoleSection === "swarm" ? (
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
              roles={t.console.roles.map((role, index) => ({ ...role, originalIndex: index }))}
              selectedAgentIndex={selectedAgentIndex}
              onOpenAgentBuilder={onOpenAgentBuilder}
              onSelectAgent={onSelectAgent}
            />
          </section>
        ) : (
          <GpuDashboard
            locale={locale}
            t={t}
          />
        )}
      </section>
    </main>
  );
}

export default AgentConsole;

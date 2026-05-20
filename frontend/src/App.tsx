import { useEffect, useMemo, useRef, useState } from "react";
import AppHeader from "./components/AppHeader";
import Breadcrumbs from "./components/Breadcrumbs";
import AgentBuilderPage from "./pages/AgentBuilderPage";
import AgentConsole from "./pages/AgentConsole";
import LandingPage from "./pages/LandingPage";
import WorkflowEditorPage from "./pages/WorkflowEditorPage";
import { content, type Locale } from "./i18n/content";

type RouteState =
  | { path: "/" }
  | { path: "/console" }
  | { path: "/agents/new" }
  | { path: "/agents/:index/edit"; index: number }
  | { path: "/workflows/new" }
  | { path: "/workflows/:index/edit"; index: number };

type AgentStatus = "active" | "review" | "queued";
type ConsoleSection = "agents" | "workflows" | "store";

function parseRoute(pathname: string): RouteState {
  if (pathname === "/console") return { path: "/console" };
  if (pathname === "/agents/new") return { path: "/agents/new" };
  if (pathname === "/workflows/new") return { path: "/workflows/new" };

  const agentMatch = pathname.match(/^\/agents\/(\d+)\/edit$/);
  if (agentMatch) {
    return { path: "/agents/:index/edit", index: Number(agentMatch[1]) };
  }

  const workflowMatch = pathname.match(/^\/workflows\/(\d+)\/edit$/);
  if (workflowMatch) {
    return { path: "/workflows/:index/edit", index: Number(workflowMatch[1]) };
  }

  return { path: "/" };
}

function App() {
  const [locale, setLocale] = useState<Locale>("en");
  const [route, setRoute] = useState<RouteState>(() => parseRoute(window.location.pathname));
  const [selectedAgentIndex, setSelectedAgentIndex] = useState(0);
  const [selectedWorkflowIndex, setSelectedWorkflowIndex] = useState(0);
  const [activeFilters, setActiveFilters] = useState<Set<AgentStatus>>(new Set());
  const [isSearchVisible, setIsSearchVisible] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [consoleSection, setConsoleSection] = useState<ConsoleSection>("agents");
  const searchInputRef = useRef<HTMLInputElement>(null);

  const t = content[locale];

  const navigate = (path: string) => {
    const nextRoute = parseRoute(path);
    window.history.pushState({}, "", path);
    setRoute(nextRoute);
    if (nextRoute.path === "/agents/:index/edit") {
      setSelectedAgentIndex(nextRoute.index);
    }
    if (nextRoute.path === "/workflows/:index/edit") {
      setSelectedWorkflowIndex(nextRoute.index);
    }
    window.scrollTo({ behavior: "auto", left: 0, top: 0 });
  };

  useEffect(() => {
    const onPopState = () => {
      const nextRoute = parseRoute(window.location.pathname);
      setRoute(nextRoute);
      if (nextRoute.path === "/agents/:index/edit") {
        setSelectedAgentIndex(nextRoute.index);
      }
      if (nextRoute.path === "/workflows/:index/edit") {
        setSelectedWorkflowIndex(nextRoute.index);
      }
      window.scrollTo({ behavior: "auto", left: 0, top: 0 });
    };

    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const header = (
    <AppHeader
      navItems={[
        { label: t.nav.console, path: "/console", active: route.path === "/console" }
      ]}
      onNavigate={(path) => {
        navigate(path);
      }}
      onToggleLocale={() => setLocale(locale === "en" ? "zh" : "en")}
      switchLabel={t.switchTo}
      variant={route.path === "/" ? "landing" : "workspace"}
    />
  );

  const availableStatuses: AgentStatus[] = ["active", "review", "queued"];

  const filteredRoles = useMemo(() => {
    return t.console.roles
      .map((role, index) => ({ ...role, originalIndex: index }))
      .filter((role) => {
        if (activeFilters.size > 0 && !activeFilters.has(role.status as AgentStatus)) {
          return false;
        }

        if (!searchTerm.trim()) {
          return true;
        }

        const needle = searchTerm.toLowerCase();
        return [role.name, role.role, role.currentTask, ...role.skills].some((value) =>
          value.toLowerCase().includes(needle)
        );
      });
  }, [activeFilters, searchTerm, t.console.roles]);

  const handleToggleFilter = (status: AgentStatus) => {
    setActiveFilters((prev: Set<AgentStatus>) => {
      const next = new Set(prev);
      if (next.has(status)) {
        next.delete(status);
      } else {
        next.add(status);
      }
      return next;
    });
  };

  const handleToggleSearch = () => {
    if (isSearchVisible) {
      setIsSearchVisible(false);
      setSearchTerm("");
    } else {
      setIsSearchVisible(true);
      setTimeout(() => searchInputRef.current?.focus(), 0);
    }
  };

  if (route.path === "/console") {
    return (
      <AgentConsole
        locale={locale}
        nav={header}
        activeFilters={activeFilters}
        availableStatuses={availableStatuses}
        consoleSection={consoleSection}
        isSearchVisible={isSearchVisible}
        selectedAgentIndex={selectedAgentIndex}
        searchTerm={searchTerm}
        searchInputRef={searchInputRef}
        roles={filteredRoles}
        workflows={t.console.workflowList as unknown as Array<typeof t.console.workflowList[number]>}
        storeAgents={[...t.console.storeAgents]}
        store={t.console.store}
        t={t}
        onCreateAgent={() => navigate("/agents/new")}
        onToggleFilter={handleToggleFilter}
        onOpenAgentBuilder={(index) => navigate(`/agents/${index}/edit`)}
        onToggleSearch={handleToggleSearch}
        onSearchTermChange={setSearchTerm}
        onSelectAgent={(index) => setSelectedAgentIndex(index)}
        onNavigateSection={(section) => setConsoleSection(section)}
        onCreateWorkflow={() => navigate("/workflows/new")}
        onEditWorkflow={(index) => navigate(`/workflows/${index}/edit`)}
        onUseAgent={(index) => navigate(`/agents/${index}/edit`)}
      />
    );
  }

  if (route.path === "/agents/new" || route.path === "/agents/:index/edit") {
    const agent = route.path === "/agents/:index/edit" ? t.console.roles[selectedAgentIndex] : undefined;
    const builderTitle = agent?.name ?? (locale === "en" ? "New Role Agent" : "新建角色 Agent");
    return (
      <AgentBuilderPage
        agent={agent}
        breadcrumbs={
          <Breadcrumbs
            items={[
              { label: locale === "en" ? "Console" : "控制台", path: "/console" },
              { label: builderTitle }
            ]}
            onNavigate={navigate}
          />
        }
        locale={locale}
        nav={header}
      />
    );
  }

  if (route.path === "/workflows/new" || route.path === "/workflows/:index/edit") {
    const workflow =
      route.path === "/workflows/:index/edit" ? t.console.workflowList[selectedWorkflowIndex] : undefined;
    const editorTitle = workflow?.name ?? (locale === "en" ? "New Workflow" : "新建工作流");
    return (
      <WorkflowEditorPage
        workflow={workflow as Parameters<typeof WorkflowEditorPage>[0]["workflow"]}
        breadcrumbs={
          <Breadcrumbs
            items={[
              { label: locale === "en" ? "Console" : "控制台", path: "/console" },
              { label: editorTitle }
            ]}
            onNavigate={navigate}
          />
        }
        locale={locale}
        nav={header}
        wf={t.console.workflows}
        stepTypes={t.console.workflowStepTypes}
      />
    );
  }

  return <LandingPage locale={locale} nav={header} onOpenConsole={() => navigate("/console")} t={t} />;
}

export default App;

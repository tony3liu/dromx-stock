import { useEffect, useMemo, useRef, useState } from "react";
import { Monitor } from "lucide-react";
import AppHeader from "./components/AppHeader";
import Breadcrumbs from "./components/Breadcrumbs";
import AgentBuilderPage from "./pages/AgentBuilderPage";
import AgentConsole from "./pages/AgentConsole";
import LandingPage from "./pages/LandingPage";
import SkillBuilderPage from "./pages/SkillBuilderPage";
import SkillsCenterPage from "./pages/SkillsCenterPage";
import SwarmCenterPage from "./pages/SwarmCenterPage";
import WorkflowEditorPage from "./pages/WorkflowEditorPage";
import RoleAgentsStore from "./pages/RoleAgentsStore";
import { content, type Locale } from "./i18n/content";
import { createSkillDraft, skillCatalog, type SkillItem } from "./data/skills";
import { createSwarm, defaultSwarms, type Swarm, type SwarmAgent } from "./data/swarms";

type RouteState =
  | { path: "/" }
  | { path: "/agents" }
  | { path: "/console" }
  | { path: "/skills" }
  | { path: "/swarms" }
  | { path: "/skills/new" }
  | { path: "/agents/new" }
  | { path: "/agents/:index/edit"; index: number }
  | { path: "/workflows/new" }
  | { path: "/workflows/:index/edit"; index: number };

type AgentStatus = "active" | "review" | "queued";
type ConsoleSection = "agents" | "skills" | "workflows" | "computeCenter" | "swarm";

function parseRoute(pathname: string): RouteState {
  if (pathname === "/console") return { path: "/console" };
  if (pathname === "/skills") return { path: "/skills" };
  if (pathname === "/swarms") return { path: "/swarms" };
  if (pathname === "/agents") return { path: "/agents" };
  if (pathname === "/skills/new") return { path: "/skills/new" };
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
  const [locale, setLocale] = useState<Locale>("zh");
  const [route, setRoute] = useState<RouteState>(() => parseRoute(window.location.pathname));
  const [selectedAgentIndex, setSelectedAgentIndex] = useState(0);
  const [selectedWorkflowIndex, setSelectedWorkflowIndex] = useState(0);
  const [skills, setSkills] = useState<SkillItem[]>(() => skillCatalog);
  const [selectedSkillId, setSelectedSkillId] = useState(skillCatalog[0]?.id ?? "");
  const [activeFilters, setActiveFilters] = useState<Set<AgentStatus>>(new Set());
  const [isSearchVisible, setIsSearchVisible] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [consoleSection, setConsoleSection] = useState<ConsoleSection>("agents");
  const [swarms, setSwarms] = useState<Swarm[]>(() => defaultSwarms);
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

  const consoleActive =
    route.path === "/console" ||
    route.path === "/agents/new" ||
    route.path === "/agents/:index/edit" ||
    route.path.startsWith("/workflows") ||
    route.path.startsWith("/skills/new");

  const header = (
    <AppHeader
      navItems={[
        { label: t.nav.agents, path: "/agents", active: route.path === "/agents" },
        { label: t.nav.swarms, path: "/swarms", active: route.path === "/swarms" },
        { label: t.nav.skills, path: "/skills", active: route.path === "/skills" }
      ]}
      rightAction={
        <a
          className={consoleActive ? "is-active" : ""}
          href="/console"
          aria-current={consoleActive ? "page" : undefined}
          onClick={(event) => {
            event.preventDefault();
            navigate("/console");
          }}
          style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
        >
          <Monitor size={14} />
          {t.nav.console}
        </a>
      }
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

  const availableAgents = useMemo<SwarmAgent[]>(() => {
    const consoleAgents: SwarmAgent[] = t.console.roles.map((r) => ({
      name: r.name,
      role: r.role,
      skills: r.skills
    }));
    const ownedStoreAgents: SwarmAgent[] = t.console.storeAgents
      .filter((a) => a.pricing === "free" || a.purchased)
      .map((a) => ({
        name: a.name,
        role: a.role,
        skills: a.skills
      }));
    // Deduplicate by name
    const seen = new Set<string>();
    return [...consoleAgents, ...ownedStoreAgents].filter((a) => {
      if (seen.has(a.name)) return false;
      seen.add(a.name);
      return true;
    });
  }, [t.console.roles, t.console.storeAgents]);

  const handleSaveSwarm = (swarm: Swarm) => {
    setSwarms((prev) => {
      const idx = prev.findIndex((s) => s.id === swarm.id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = swarm;
        return next;
      }
      return [swarm, ...prev];
    });
  };

  const handleDeleteSwarm = (id: string) => {
    setSwarms((prev) => prev.filter((s) => s.id !== id));
  };

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

  const selectedSkill = skills.find((skill) => skill.id === selectedSkillId) ?? skills[0] ?? createSkillDraft();

  const handleCreateSkill = () => {
    const nextDraft = createSkillDraft();
    setSkills((prev) => [nextDraft, ...prev]);
    setSelectedSkillId(nextDraft.id);
    navigate("/skills/new");
  };

  const handleSaveSkillDraft = () => {
    setSkills((prev) =>
      prev.map((skill) =>
        skill.id === selectedSkillId
          ? {
              ...skill,
              status: "draft",
              owner: "me",
              installed: false,
              enabled: false
            }
          : skill
      )
    );
  };

  const handleSubmitSkillReview = () => {
    setSkills((prev) =>
      prev.map((skill) =>
        skill.id === selectedSkillId
          ? {
              ...skill,
              status: "review",
              owner: "me"
            }
          : skill
      )
    );
  };

  const handlePublishSkill = () => {
    setSkills((prev) =>
      prev.map((skill) =>
        skill.id === selectedSkillId
          ? {
              ...skill,
              status: "published",
              owner: "me"
            }
          : skill
      )
    );
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
        swarms={swarms}
        availableAgents={availableAgents}
        onSaveSwarm={handleSaveSwarm}
        onDeleteSwarm={handleDeleteSwarm}
        onCreateWorkflow={() => navigate("/workflows/new")}
        onEditWorkflow={(index) => navigate(`/workflows/${index}/edit`)}
        onUseAgent={(index) => navigate(`/agents/${index}/edit`)}
        skills={skills}
        selectedSkillId={selectedSkillId}
        onSelectSkill={setSelectedSkillId}
        onCreateSkill={handleCreateSkill}
        onOpenSkillBuilder={() => navigate("/skills/new")}
        onSaveSkillDraft={handleSaveSkillDraft}
        onSubmitSkillReview={handleSubmitSkillReview}
        onPublishSkill={handlePublishSkill}
      />
    );
  }

  if (route.path === "/agents") {
    return (
      <main className="console-shell" lang={locale}>
        {header}
        <section style={{ padding: "0 0 24px" }}>
          <RoleAgentsStore
            locale={locale}
            agents={[...t.console.storeAgents]}
            store={t.console.store}
            onUseAgent={() => navigate("/console")}
          />
        </section>
      </main>
    );
  }

  if (route.path === "/swarms") {
    return (
      <SwarmCenterPage
        locale={locale}
        nav={header}
        swarms={swarms}
        t={t}
        onUseSwarm={() => {
          navigate("/console");
          setConsoleSection("swarm");
        }}
      />
    );
  }

  if (route.path === "/skills") {
    return (
      <SkillsCenterPage
        locale={locale}
        nav={header}
        skills={skills}
        selectedSkillId={selectedSkillId}
        onSelectSkill={setSelectedSkillId}
        t={t}
      />
    );
  }

  if (route.path === "/skills/new") {
    const builderSkill = selectedSkill.owner === "me" ? selectedSkill : createSkillDraft();

    return (
      <SkillBuilderPage
        locale={locale}
        nav={header}
        onSaveDraft={handleSaveSkillDraft}
        onSubmitReview={handleSubmitSkillReview}
        onPublish={handlePublishSkill}
        onBackToStore={() => {
          navigate("/console");
          setConsoleSection("skills");
        }}
        onNavigate={navigate}
        skill={builderSkill}
        t={t}
      />
    );
  }

  if (route.path === "/agents/new" || route.path === "/agents/:index/edit") {
    let agent = undefined;
    if (route.path === "/agents/:index/edit") {
      if (selectedAgentIndex < t.console.roles.length) {
        agent = t.console.roles[selectedAgentIndex];
      } else if (selectedAgentIndex < t.console.storeAgents.length) {
        const sa = t.console.storeAgents[selectedAgentIndex];
        agent = {
          name: sa.name,
          role: sa.role,
          status: sa.status,
          skills: sa.skills,
          currentTask: sa.description,
          memorySignal: "0 memory objects"
        };
      }
    }
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

import { useEffect, useMemo, useRef, useState } from "react";
import AppHeader from "./components/AppHeader";
import Breadcrumbs from "./components/Breadcrumbs";
import AgentBuilderPage from "./pages/AgentBuilderPage";
import AgentConsole from "./pages/AgentConsole";
import LandingPage from "./pages/LandingPage";
import { content, type Locale } from "./i18n/content";

type RouteState =
  | { path: "/" }
  | { path: "/console" }
  | { path: "/agents/new" }
  | { path: "/agents/:index/edit"; index: number };

type RoleFilter = "all" | "active" | "review" | "queued";

function parseRoute(pathname: string): RouteState {
  if (pathname === "/console") return { path: "/console" };
  if (pathname === "/agents/new") return { path: "/agents/new" };

  const editMatch = pathname.match(/^\/agents\/(\d+)\/edit$/);
  if (editMatch) {
    return { path: "/agents/:index/edit", index: Number(editMatch[1]) };
  }

  return { path: "/" };
}

function App() {
  const [locale, setLocale] = useState<Locale>("en");
  const [route, setRoute] = useState<RouteState>(() => parseRoute(window.location.pathname));
  const [selectedAgentIndex, setSelectedAgentIndex] = useState(0);
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);

  const t = content[locale];

  const navigate = (path: string) => {
    const nextRoute = parseRoute(path);
    window.history.pushState({}, "", path);
    setRoute(nextRoute);
    if (nextRoute.path === "/agents/:index/edit") {
      setSelectedAgentIndex(nextRoute.index);
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

  const filteredRoles = useMemo(() => {
    return t.console.roles
      .map((role, index) => ({ ...role, originalIndex: index }))
      .filter((role) => {
        if (roleFilter !== "all" && role.status !== roleFilter) {
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
  }, [roleFilter, searchTerm, t.console.roles]);

  if (route.path === "/console") {
    return (
      <AgentConsole
        locale={locale}
        nav={header}
        onCreateAgent={() => navigate("/agents/new")}
        onFilterStatus={() => {
          setRoleFilter((value) => (value === "all" ? "active" : value === "active" ? "review" : value === "review" ? "queued" : "all"));
        }}
        onOpenAgentBuilder={(index) => navigate(`/agents/${index}/edit`)}
        onSearchRoles={() => searchInputRef.current?.focus()}
        onSearchTermChange={setSearchTerm}
        onSelectAgent={(index) => setSelectedAgentIndex(index)}
        onToggleLocale={() => setLocale(locale === "en" ? "zh" : "en")}
        roleFilter={roleFilter}
        roles={filteredRoles}
        searchInputRef={searchInputRef}
        searchTerm={searchTerm}
        selectedAgentIndex={selectedAgentIndex}
        t={t}
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

  return <LandingPage locale={locale} nav={header} onOpenConsole={() => navigate("/console")} t={t} />;
}

export default App;

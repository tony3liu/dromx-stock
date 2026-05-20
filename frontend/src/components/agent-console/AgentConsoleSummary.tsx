import { useEffect, useRef, useState } from "react";
import type React from "react";
import type { Locale } from "../../i18n/content";

type AgentStatus = "active" | "review" | "queued";

const STATUS_LABEL: Record<AgentStatus, { en: string; zh: string }> = {
  active: { en: "Active", zh: "活跃" },
  review: { en: "Review", zh: "待审阅" },
  queued: { en: "Queued", zh: "排队中" }
};

type AgentConsoleSummaryProps = {
  locale: Locale;
  activeFilters: Set<AgentStatus>;
  availableStatuses: AgentStatus[];
  isSearchVisible: boolean;
  onCreateAgent: () => void;
  onToggleFilter: (status: AgentStatus) => void;
  onToggleSearch: () => void;
  onSearchTermChange: (value: string) => void;
  searchInputRef: React.RefObject<HTMLInputElement | null>;
  searchTerm: string;
};

function AgentConsoleSummary({
  locale,
  activeFilters,
  availableStatuses,
  isSearchVisible,
  onCreateAgent,
  onToggleFilter,
  onToggleSearch,
  onSearchTermChange,
  searchInputRef,
  searchTerm
}: AgentConsoleSummaryProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isDropdownOpen) return;
    const handleClick = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [isDropdownOpen]);

  const filterCount = activeFilters.size;
  const filterLabel = locale === "en" ? "Filter Status" : "筛选状态";

  return (
    <div className="console-summary agent-console-head">
      <span className="section-label">{locale === "en" ? "Role Agent Operations" : "角色 Agent 操作台"}</span>
      <h1>{locale === "en" ? "Role Agent Console" : "角色 Agent 控制台"}</h1>
      <p>
        {locale === "en"
          ? "Manage every professional role Agent as a digital labor unit: edit its workflows, skills, MCP tools, memory, debug runs, and release state."
          : "以数字劳动力资源的方式管理每一个职业角色 Agent：编辑工作流、技能、MCP 工具、记忆、调试运行和发布状态。"}
      </p>
      <div className="summary-metrics">
        <span>{locale === "en" ? "4 Role Agents" : "4 个角色 Agent"}</span>
        <span>{locale === "en" ? "9 Workflows" : "9 个工作流"}</span>
        <span>{locale === "en" ? "12 Skills" : "12 个技能"}</span>
        <span>{locale === "en" ? "6 MCP Tools" : "6 个 MCP 工具"}</span>
      </div>
      <div className="action-row">
        <button className="console-action is-primary" type="button" onClick={onCreateAgent}>
          {locale === "en" ? "New Role Agent" : "新建角色 Agent"}
        </button>

        {/* Status filter dropdown */}
        <div className="filter-dropdown" ref={dropdownRef}>
          <button
            className={`console-action${filterCount > 0 ? " has-active-filters" : ""}`}
            type="button"
            onClick={() => setIsDropdownOpen((v) => !v)}
          >
            {filterLabel}
            {filterCount > 0 && <span className="filter-count">{filterCount}</span>}
            <span className={`dropdown-arrow${isDropdownOpen ? " is-open" : ""}`}>&#9662;</span>
          </button>
          {isDropdownOpen && (
            <div className="filter-dropdown-panel">
              {availableStatuses.map((status) => (
                <label key={status} className={`filter-option status-${status}`}>
                  <input
                    type="checkbox"
                    checked={activeFilters.has(status)}
                    onChange={() => onToggleFilter(status)}
                  />
                  <span className={`role-status role-${status}`}>{STATUS_LABEL[status][locale === "en" ? "en" : "zh"]}</span>
                </label>
              ))}
              {filterCount > 0 && (
                <button
                  className="filter-clear"
                  type="button"
                  onClick={() => availableStatuses.forEach((s) => activeFilters.has(s) && onToggleFilter(s))}
                >
                  {locale === "en" ? "Clear all" : "清除全部"}
                </button>
              )}
            </div>
          )}
        </div>

        <button className="console-action" type="button" onClick={onToggleSearch}>
          {locale === "en" ? "Search Roles" : "搜索角色"}
        </button>
      </div>

      {/* Search area */}
      {isSearchVisible && (
        <div className="summary-search-area">
          <div className="summary-search-input-wrap">
            <input
              aria-label={locale === "en" ? "Search role agents" : "搜索角色 Agent"}
              className="summary-search-input"
              placeholder={locale === "en" ? "Search by name, role, task, or skill…" : "按名称、角色、任务或技能搜索…"}
              ref={searchInputRef}
              value={searchTerm}
              onChange={(event) => onSearchTermChange(event.target.value)}
            />
            {searchTerm && (
              <button
                className="summary-search-clear"
                type="button"
                aria-label={locale === "en" ? "Clear search" : "清除搜索"}
                onClick={() => onSearchTermChange("")}
              >
                &#10005;
              </button>
            )}
          </div>
          {searchTerm && (
            <div className="summary-chip-row">
              <span className="summary-chip">
                {locale === "en" ? "Search: " : "搜索："}{searchTerm}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default AgentConsoleSummary;

import type React from "react";
import type { Locale } from "../../i18n/content";

type AgentConsoleSummaryProps = {
  locale: Locale;
  onCreateAgent: () => void;
  onFilterStatus: () => void;
  onSearchRoles: () => void;
  onSearchTermChange: (value: string) => void;
  roleFilter: "all" | "active" | "review" | "queued";
  searchInputRef: React.RefObject<HTMLInputElement | null>;
  searchTerm: string;
};

function AgentConsoleSummary({
  locale,
  onCreateAgent,
  onFilterStatus,
  onSearchRoles,
  onSearchTermChange,
  roleFilter,
  searchInputRef,
  searchTerm
}: AgentConsoleSummaryProps) {
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
        <span>{locale === "en" ? `Filter: ${roleFilter}` : `筛选：${roleFilter}`}</span>
      </div>
      <div className="action-row">
        <button className="console-action is-primary" type="button" onClick={onCreateAgent}>
          {locale === "en" ? "New Role Agent" : "新建角色 Agent"}
        </button>
        <button className="console-action" type="button" onClick={onFilterStatus}>
          {locale === "en" ? "Filter Status" : "筛选状态"}
        </button>
        <button className="console-action" type="button" onClick={onSearchRoles}>
          {locale === "en" ? "Search Roles" : "搜索角色"}
        </button>
      </div>
      {searchTerm ? (
        <div className="summary-chip-row">
          <span className="summary-chip">{searchTerm}</span>
        </div>
      ) : null}
      <input
        aria-label={locale === "en" ? "Search role agents" : "搜索角色 Agent"}
        className="summary-search-input"
        ref={searchInputRef}
        value={searchTerm}
        onChange={(event) => onSearchTermChange(event.target.value)}
      />
    </div>
  );
}

export default AgentConsoleSummary;

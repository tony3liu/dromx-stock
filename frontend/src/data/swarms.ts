export type SwarmAgent = {
  name: string;
  role: string;
  skills: readonly string[] | string[];
};

export type Swarm = {
  id: string;
  name: string;
  description: string;
  agentNames: string[];
  leaderAgentName: string;
  createdAt: string;
};

export function createSwarm(
  name?: string,
  description?: string,
  agentNames?: string[],
  leaderAgentName?: string
): Swarm {
  return {
    id: crypto.randomUUID(),
    name: name ?? "",
    description: description ?? "",
    agentNames: agentNames ?? [],
    leaderAgentName: leaderAgentName ?? (agentNames?.[0] ?? ""),
    createdAt: new Date().toISOString().split("T")[0]
  };
}

export const defaultSwarms: Swarm[] = [
  {
    id: crypto.randomUUID(),
    name: "研发部",
    description: "负责产品核心功能开发与技术架构。",
    agentNames: ["Sales Agent", "Research Analyst"],
    leaderAgentName: "Research Analyst",
    createdAt: "2026-05-01"
  },
  {
    id: crypto.randomUUID(),
    name: "财务部",
    description: "管理财务流程、报表与合规审计。",
    agentNames: ["Finance Controller"],
    leaderAgentName: "Finance Controller",
    createdAt: "2026-05-10"
  },
  {
    id: crypto.randomUUID(),
    name: "测试开发部",
    description: "自动化测试与质量保障。",
    agentNames: ["Data Pipeline Engineer", "Social Media Manager"],
    leaderAgentName: "Data Pipeline Engineer",
    createdAt: "2026-05-15"
  }
];

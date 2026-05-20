export type SkillStatus = "draft" | "review" | "published";
export type SkillText = {
  name: string;
  category: string;
  summary: string;
  description: string;
  agentTypes: string[];
  tools: string[];
  inputs: string[];
  outputs: string[];
  publisher: string;
};

export type SkillItem = {
  id: string;
  name: string;
  category: string;
  summary: string;
  description: string;
  status: SkillStatus;
  pricing: "free" | "paid";
  price?: number;
  rating: number;
  installs: number;
  agentTypes: string[];
  tools: string[];
  inputs: string[];
  outputs: string[];
  version: string;
  publisher: string;
  owner: "system" | "me";
  installed: boolean;
  enabled?: boolean;
};

export type SkillTranslations = Record<string, SkillText>;

export const skillCatalog: SkillItem[] = [
  {
    id: "lead-mapper",
    name: "Lead Mapper",
    category: "Sales",
    summary: "Turns raw prospect signals into structured lead routes.",
    description: "Maps outbound discovery, qualification, and routing into a repeatable sales workflow.",
    status: "published",
    pricing: "free",
    rating: 4.8,
    installs: 1832,
    agentTypes: ["Sales Agent", "Growth Agent"],
    tools: ["CRM Sync", "Spreadsheet Parser"],
    inputs: ["Lead list", "ICP rules", "Signal feed"],
    outputs: ["Qualified leads", "Routing notes"],
    version: "1.2.0",
    publisher: "DromX Labs",
    owner: "system",
    installed: true,
    enabled: true
  },
  {
    id: "content-packager",
    name: "Content Packager",
    category: "Marketing",
    summary: "Shapes positioning notes into channel-ready content.",
    description: "Packages briefs into launches, newsletters, and multi-channel publication plans.",
    status: "published",
    pricing: "paid",
    price: 19.0,
    rating: 4.9,
    installs: 944,
    agentTypes: ["Content Agent", "Brand Agent"],
    tools: ["Outline Generator", "Tone Adapter"],
    inputs: ["Positioning brief", "Voice rules"],
    outputs: ["Draft outline", "Channel variants"],
    version: "2.0.1",
    publisher: "DromX Labs",
    owner: "system",
    installed: false,
    enabled: false
  },
  {
    id: "research-signal",
    name: "Research Signal Scanner",
    category: "Research",
    summary: "Extracts market assumptions from notes and documents.",
    description: "Scans source material, detects patterns, and produces structured market signals.",
    status: "published",
    pricing: "free",
    rating: 4.6,
    installs: 2140,
    agentTypes: ["Research Agent"],
    tools: ["Web Notes", "Source Extractor"],
    inputs: ["Source notes", "Search scope"],
    outputs: ["Signals", "Evidence list"],
    version: "1.1.0",
    publisher: "DromX Labs",
    owner: "system",
    installed: true,
    enabled: true
  },
  {
    id: "finance-guard",
    name: "Finance Guardrails",
    category: "Finance",
    summary: "Keeps budget assumptions and operating metrics aligned.",
    description: "Builds basic financial operating checks and flags mismatches in the model.",
    status: "review",
    pricing: "paid",
    price: 29.0,
    rating: 4.4,
    installs: 320,
    agentTypes: ["Finance Agent"],
    tools: ["Model Checker", "Assumption Diff"],
    inputs: ["Revenue plan", "Cost model"],
    outputs: ["Budget warnings", "Model notes"],
    version: "0.9.0",
    publisher: "DromX Labs",
    owner: "system",
    installed: false,
    enabled: false
  },
  {
    id: "my-launch-draft",
    name: "Launch Brief Builder",
    category: "Marketing",
    summary: "My private draft Skill for launch planning.",
    description: "Draft-only helper for turning launch inputs into a structured campaign brief.",
    status: "draft",
    pricing: "free",
    rating: 0,
    installs: 0,
    agentTypes: ["Content Agent"],
    tools: ["Draft Editor"],
    inputs: ["Launch notes"],
    outputs: ["Campaign brief"],
    version: "0.1.0",
    publisher: "Me",
    owner: "me",
    installed: false,
    enabled: false
  },
  {
    id: "my-research-skill",
    name: "Signal Extractor",
    category: "Research",
    summary: "My own research draft for source extraction.",
    description: "Private workflow for pulling structured signals from raw notes.",
    status: "review",
    pricing: "free",
    rating: 0,
    installs: 0,
    agentTypes: ["Research Agent"],
    tools: ["Notes Parser"],
    inputs: ["Notes", "Prompt template"],
    outputs: ["Structured findings"],
    version: "0.2.0",
    publisher: "Me",
    owner: "me",
    installed: false,
    enabled: false
  }
];

export function createSkillDraft(): SkillItem {
  return {
    id: "my-new-skill",
    name: "Untitled Skill",
    category: "General",
    summary: "Describe the capability in one clear sentence.",
    description: "Draft-only helper for turning launch inputs into a structured skill.",
    status: "draft",
    pricing: "free",
    rating: 0,
    installs: 0,
    agentTypes: ["Agent"],
    tools: ["Draft Editor"],
    inputs: ["Notes"],
    outputs: ["Draft output"],
    version: "0.1.0",
    publisher: "Me",
    owner: "me",
    installed: false,
    enabled: false
  };
}

export function localizeSkill(skill: SkillItem, translations: SkillTranslations): SkillItem {
  const copy = translations[skill.id];

  return copy ? { ...skill, ...copy } : skill;
}

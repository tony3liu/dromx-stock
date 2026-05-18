import {
  Boxes,
  BrainCircuit,
  Cpu,
  Fingerprint,
  Gauge,
  Layers3,
  LockKeyhole,
  ShieldCheck,
  Workflow
} from "lucide-react";

export type Locale = "en" | "zh";

export const content = {
  en: {
    brand: "DromX",
    nav: { platform: "Platform", console: "Console", trust: "Trust" },
    switchTo: "中文",
    heroEyebrow: "Digital labor network for the real world",
    heroTitle: "Infinite productivity for the world",
    heroSubtitle: "Turn real-world capability into digital, structured, collaborative agents",
    heroCopy:
      "DromX digitizes real-world individual and group productivity into role-based agents, long-term memory, and swarm collaboration so human capability can run continuously in the digital world.",
    primaryCta: "Start a Workflow",
    secondaryCta: "View Architecture",
    panelKicker: "Live agent run",
    panelTitle: "DromX Swarm Center",
    objectiveLabel: "Digitized role",
    objectiveText: "A sales operator, content strategist, and finance coordinator working as one swarm.",
    loopLabel: "Evolution path",
    loopTitle: "Reality ability -> digitization -> Agentification -> Swarm collaboration",
    outcomesTitle: "What the network can do",
    outcomes: [
      "Represent real professional roles",
      "Package clear skills and tools",
      "Coordinate across agent teams",
      "Run 7x24 digital labor loops"
    ],
    outcomeCopy: "Each role is digitized, structured, and ready to collaborate as part of a swarm.",
    trustLabel: "Trust layer",
    trustTitle: "Built to make human capability copyable, extensible, and persistent.",
    trustCopy:
      "Every Agent carries a role identity, skill system, tool access, and long-term memory, so capability can exist in the digital world without being trapped by time or scale.",
    finalLabel: "Next step",
    finalTitle: "See the network that runs the work.",
    finalCta: "Enter Console",
    console: {
      nav: ["Overview", "Agent Console", "Role Agents", "Swarms", "Skills", "Memory", "Compute", "Settings"],
      workspace: "Digital Labor Workspace",
      status: "Swarm running",
      activeSwarm: "Active Swarm",
      activeTitle: "Market Expansion Swarm",
      activeObjective:
        "Convert real-world growth, content, research, and finance capability into a coordinated digital labor team.",
      metrics: ["5 Role Agents", "6 Workflow Steps", "12 Memory Updates"],
      roleAgents: "Role Agents",
      workflow: "Workflow Decomposition",
      feed: "Execution Feed",
      output: "Output Preview",
      actions: ["Review Output", "Re-run Step", "Save Workflow"],
      roles: [
        {
          name: "Sales Agent",
          role: "Acquisition operator",
          status: "active",
          skills: ["Lead mapping", "Pipeline design"],
          currentTask: "Translating outbound motion into repeatable steps",
          memorySignal: "23 memory objects"
        },
        {
          name: "Content Agent",
          role: "Narrative strategist",
          status: "review",
          skills: ["Editorial planning", "Channel adaptation"],
          currentTask: "Packaging positioning into a launch content system",
          memorySignal: "18 memory objects"
        },
        {
          name: "Research Agent",
          role: "Market analyst",
          status: "active",
          skills: ["Signal scanning", "Competitor mapping"],
          currentTask: "Extracting market assumptions from source notes",
          memorySignal: "31 memory objects"
        },
        {
          name: "Finance Agent",
          role: "Operating controller",
          status: "queued",
          skills: ["Budget model", "Unit economics"],
          currentTask: "Waiting for revenue model inputs",
          memorySignal: "11 memory objects"
        }
      ],
      steps: [
        { title: "Intent analysis", owner: "Coordinator Agent", status: "completed", description: "Parsed the objective into role-level work streams." },
        { title: "Role mapping", owner: "Role Graph", status: "completed", description: "Matched capabilities to Sales, Content, Research, and Finance Agents." },
        { title: "Skill selection", owner: "Skills Graph", status: "running", description: "Selecting tools and reusable skills for each role." },
        { title: "Task execution", owner: "Agent Swarm", status: "running", description: "Agents are generating artifacts and exchanging memory." },
        { title: "Output synthesis", owner: "Coordinator Agent", status: "waiting", description: "Waiting for role outputs before synthesis." },
        { title: "Human review", owner: "Operator", status: "queued", description: "Final decisions stay available for review." }
      ],
      events: [
        { time: "09:42", title: "Role Agent assigned", detail: "Sales Agent accepted acquisition workflow mapping." },
        { time: "09:45", title: "Skill invoked", detail: "Research Agent invoked market-signal extraction." },
        { time: "09:48", title: "Memory retrieved", detail: "Content Agent loaded brand voice and launch notes." },
        { time: "09:51", title: "Output draft generated", detail: "Coordinator Agent assembled the first swarm summary." }
      ],
      outputSummary:
        "The Swarm is producing a market expansion operating pack: role responsibilities, task sequence, required skills, and a reusable execution memory.",
      artifacts: ["Role map", "Workflow plan", "Launch narrative", "Finance assumptions"]
    },
    platformLayers: [
      {
        icon: BrainCircuit,
        title: "Role Agents",
        label: "Identity layer",
        copy: "Each Agent maps to a real-world occupational role with skills, tools, and clear responsibilities."
      },
      {
        icon: Boxes,
        title: "Skills Graph",
        label: "Capability layer",
        copy: "Skills make role intelligence callable, reusable, and scalable across workflows and organizations."
      },
      {
        icon: Cpu,
        title: "Swarm Runtime",
        label: "Execution layer",
        copy: "Swarm collaboration and persistent memory keep digital labor running continuously across domains."
      }
    ],
    liveRuns: [
      { task: "Translate sales workflows into role Agents", state: "Running", agent: "Sales Agent", progress: "68%" },
      { task: "Package content expertise into Skills", state: "Review", agent: "Content Agent", progress: "92%" },
      { task: "Sync memory across finance operations", state: "Queued", agent: "Finance Agent", progress: "14%" },
      { task: "Map customer service into a role Agent", state: "Running", agent: "Support Agent", progress: "44%" },
      { task: "Promote research skills into the swarm", state: "Queued", agent: "Research Agent", progress: "26%" }
    ],
    useCases: [
      "Professional role modeling",
      "Capability digitization",
      "Swarm collaboration",
      "Long-term memory",
      "24/7 labor network",
      "Cross-domain coordination"
    ],
    businessLoop: ["Reality", "Digitize", "Agentify", "Swarm", "Persist", "Scale"],
    trustItems: [
      [ShieldCheck, "Role identity"],
      [Workflow, "Swarm orchestration"],
      [Gauge, "Capability visibility"],
      [LockKeyhole, "Tool safety"],
      [Fingerprint, "Memory continuity"],
      [Layers3, "Structured labor"]
    ]
  },
  zh: {
    brand: "DromX",
    nav: { platform: "平台", console: "控制台", trust: "信任" },
    switchTo: "EN",
    heroEyebrow: "面向现实世界的数字劳动力网络",
    heroTitle: "让世界拥有无限生产力",
    heroSubtitle: "将现实能力转化为数字化、结构化、可协作的 Agent",
    heroCopy:
      "DromX 将现实世界中个体与群体组织的生产力进行数字化与结构化表达，让职业角色、技能、工具和长期记忆成为可持续运行的数字劳动力。",
    primaryCta: "开始执行",
    secondaryCta: "查看架构",
    panelKicker: "实时智能体运行",
    panelTitle: "DromX Swarm 中心",
    objectiveLabel: "已数字化角色",
    objectiveText: "销售专员、内容策略师和财务协调员作为一个 Swarm 协同工作。",
    loopLabel: "演进路径",
    loopTitle: "现实能力 → 数字化 → Agent 化 → Swarm 协作",
    outcomesTitle: "网络可以完成什么",
    outcomes: ["表达现实职业角色", "封装技能和工具", "跨 Agent 团队协作", "7x24 小时运转"],
    outcomeCopy: "每个角色都被数字化、结构化，并可作为 Swarm 的一部分协作运行。",
    trustLabel: "信任层",
    trustTitle: "让人类能力可复制、可扩展、可持续运行。",
    trustCopy:
      "每个 Agent 都有清晰的职业身份、完整技能体系、可调用工具和长期记忆，使能力能够以数字化方式存在并持续成长。",
    finalLabel: "下一步",
    finalTitle: "进入真正运转的数字劳动力网络。",
    finalCta: "进入控制台",
    console: {
      nav: ["总览", "Agent 控制台", "角色 Agent", "Swarms", "技能", "记忆", "算力", "设置"],
      workspace: "数字劳动力工作区",
      status: "Swarm 运行中",
      activeSwarm: "活跃 Swarm",
      activeTitle: "市场拓展 Swarm",
      activeObjective: "将增长、内容、研究与财务能力转化为一个协同运转的数字劳动力团队。",
      metrics: ["5 个角色 Agent", "6 个工作流步骤", "12 次记忆更新"],
      roleAgents: "角色 Agent",
      workflow: "工作流拆解",
      feed: "执行事件流",
      output: "输出预览",
      actions: ["审阅输出", "重跑步骤", "保存工作流"],
      roles: [
        {
          name: "销售 Agent",
          role: "获客运营者",
          status: "active",
          skills: ["线索映射", "管线设计"],
          currentTask: "将外呼获客动作转化为可复用步骤",
          memorySignal: "23 个记忆对象"
        },
        {
          name: "内容 Agent",
          role: "叙事策略师",
          status: "review",
          skills: ["选题规划", "渠道适配"],
          currentTask: "把定位封装成发布内容系统",
          memorySignal: "18 个记忆对象"
        },
        {
          name: "研究 Agent",
          role: "市场分析师",
          status: "active",
          skills: ["信号扫描", "竞品映射"],
          currentTask: "从资料中提取市场假设",
          memorySignal: "31 个记忆对象"
        },
        {
          name: "财务 Agent",
          role: "经营控制员",
          status: "queued",
          skills: ["预算模型", "单位经济"],
          currentTask: "等待收入模型输入",
          memorySignal: "11 个记忆对象"
        }
      ],
      steps: [
        { title: "意图解析", owner: "协调 Agent", status: "completed", description: "将目标拆解为角色级工作流。" },
        { title: "角色映射", owner: "角色图谱", status: "completed", description: "匹配销售、内容、研究和财务 Agent。" },
        { title: "技能选择", owner: "技能图谱", status: "running", description: "为每个角色选择工具和可复用技能。" },
        { title: "任务执行", owner: "Agent Swarm", status: "running", description: "多个 Agent 正在生成产物并交换记忆。" },
        { title: "输出综合", owner: "协调 Agent", status: "waiting", description: "等待角色输出后进行综合。" },
        { title: "人工审阅", owner: "操作者", status: "queued", description: "关键决策保留给人工审阅。" }
      ],
      events: [
        { time: "09:42", title: "角色 Agent 已分配", detail: "销售 Agent 接受获客流程映射。" },
        { time: "09:45", title: "技能已调用", detail: "研究 Agent 调用市场信号提取能力。" },
        { time: "09:48", title: "记忆已读取", detail: "内容 Agent 加载品牌语气和发布记录。" },
        { time: "09:51", title: "输出草稿已生成", detail: "协调 Agent 生成第一版 Swarm 摘要。" }
      ],
      outputSummary: "Swarm 正在生成市场拓展作业包：角色职责、任务序列、所需技能和可复用执行记忆。",
      artifacts: ["角色地图", "工作流计划", "发布叙事", "财务假设"]
    },
    platformLayers: [
      {
        icon: BrainCircuit,
        title: "角色 Agent",
        label: "身份层",
        copy: "每个 Agent 对应一种现实职业角色，具备技能、工具和清晰职责。"
      },
      {
        icon: Boxes,
        title: "技能图谱",
        label: "能力层",
        copy: "技能让角色智能体具备可调用、可复用、可扩展的能力。"
      },
      {
        icon: Cpu,
        title: "Swarm Runtime",
        label: "执行层",
        copy: "Swarm 协作与长期记忆让数字劳动力能够跨领域持续运转。"
      }
    ],
    liveRuns: [
      { task: "将销售流程转为角色 Agent", state: "运行中", agent: "销售 Agent", progress: "68%" },
      { task: "把内容能力封装成技能", state: "待审阅", agent: "内容 Agent", progress: "92%" },
      { task: "同步财务运营记忆", state: "排队中", agent: "财务 Agent", progress: "14%" },
      { task: "将客户服务映射为角色 Agent", state: "运行中", agent: "支持 Agent", progress: "44%" },
      { task: "把研究技能分发进 Swarm", state: "排队中", agent: "研究 Agent", progress: "26%" }
    ],
    useCases: ["职业角色建模", "能力数字化", "Swarm 协作", "长期记忆", "24/7 劳动力网络", "跨领域协同"],
    businessLoop: ["现实", "数字化", "Agent 化", "Swarm", "持久化", "规模化"],
    trustItems: [
      [ShieldCheck, "角色身份"],
      [Workflow, "Swarm 编排"],
      [Gauge, "能力可见"],
      [LockKeyhole, "工具安全"],
      [Fingerprint, "记忆连续"],
      [Layers3, "结构化劳动力"]
    ]
  }
} as const;

export type AppContent = (typeof content)[Locale];
export type RoleAgent = AppContent["console"]["roles"][number];

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
      nav: ["Overview", "Agent Console", "Workflows", "Role Agents", "Swarms", "Skills", "Memory", "Compute", "Settings"],
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
      artifacts: ["Role map", "Workflow plan", "Launch narrative", "Finance assumptions"],
      workflows: {
        navLabel: "Workflows",
        title: "Workflow Builder",
        description:
          "Design and configure automated workflows as reusable building blocks. Each workflow is a sequence of steps — LLM calls, HTTP requests, code execution, conditions, and knowledge retrieval — that Agents can select and invoke at runtime.",
        createLabel: "New Workflow",
        editLabel: "Edit Workflow",
        stepCount: (n: number) => `${n} step${n === 1 ? "" : "s"}`,
        statusDraft: "Draft",
        statusPublished: "Published",
        noSteps: "No steps yet. Add a step to start building.",
        publish: "Publish",
        unpublish: "Unpublish",
        duplicate: "Duplicate",
        runDebug: "Run Debug",
        addStep: "Add Step",
        removeStep: "Remove",
        moveUp: "Move up",
        moveDown: "Move down",
        stepNumber: (n: number) => `Step ${n}`,
        debugTitle: "Debug Console",
        debugPlaceholder: "Run a debug session to see step outputs and variable state.",
        releaseTitle: "Release",
        releaseDescription:
          "Published workflows are available for Agents to select and invoke. Draft workflows are only visible in the builder."
      },
      workflowList: [
        {
          name: "Content Generation Pipeline",
          description: "Generate blog content from topic briefs using LLM with style adaptation and SEO optimization.",
          status: "published",
          steps: [
            { id: "s1", type: "start", title: "Receive topic brief", config: { inputs: "topic, audience, tone" } },
            { id: "s2", type: "llm", title: "Generate draft with GPT-4", config: { model: "gpt-4", temperature: "0.7", maxTokens: "4096" } },
            { id: "s3", type: "code", title: "Apply SEO formatting", config: { language: "python", snippet: "def optimize_seo(text): ..." } },
            { id: "s4", type: "end", title: "Return final content", config: { outputs: "content, wordCount, seoScore" } }
          ]
        },
        {
          name: "Customer Support Triage",
          description: "Classify inbound support tickets, route urgent issues to human agents, and auto-respond to FAQs.",
          status: "draft",
          steps: [
            { id: "s1", type: "start", title: "Receive support ticket", config: { inputs: "ticketText, customerTier" } },
            { id: "s2", type: "condition", title: "Check urgency level", config: { variable: "customerTier", operator: "equals", value: "premium" } },
            { id: "s3", type: "llm", title: "Generate FAQ response", config: { model: "gpt-4o", temperature: "0.3", maxTokens: "2048" } },
            { id: "s4", type: "http-request", title: "Escalate to Zendesk", config: { method: "POST", url: "https://api.zendesk.com/tickets" } },
            { id: "s5", type: "end", title: "Return resolution", config: { outputs: "response, escalated, ticketId" } }
          ]
        },
        {
          name: "Data Enrichment Flow",
          description: "Enrich lead records by querying external APIs and a knowledge base, then normalize the result.",
          status: "published",
          steps: [
            { id: "s1", type: "start", title: "Receive lead record", config: { inputs: "companyName, domain" } },
            { id: "s2", type: "http-request", title: "Fetch company profile", config: { method: "GET", url: "https://api.example.com/companies" } },
            { id: "s3", type: "knowledge", title: "Query industry knowledge base", config: { knowledgeBase: "industry-reports", topK: "5" } },
            { id: "s4", type: "llm", title: "Normalize enrichment data", config: { model: "gpt-4o-mini", temperature: "0.1", maxTokens: "2048" } },
            { id: "s5", type: "end", title: "Return enriched record", config: { outputs: "enrichedData, confidenceScore" } }
          ]
        }
      ],
      workflowStepTypes: {
        start: { label: "Start", category: "flow", fields: ["inputs"] },
        llm: { label: "LLM", category: "ai", fields: ["model", "systemPrompt", "temperature", "maxTokens"] },
        "http-request": { label: "HTTP Request", category: "integration", fields: ["method", "url", "headers", "body"] },
        code: { label: "Code", category: "logic", fields: ["language", "code"] },
        condition: { label: "Condition", category: "logic", fields: ["variable", "operator", "value", "trueBranch", "falseBranch"] },
        knowledge: { label: "Knowledge", category: "ai", fields: ["knowledgeBase", "query", "topK"] },
        end: { label: "End", category: "flow", fields: ["outputs"] }
      },
      store: {
        title: "Role Agent Store",
        description:
          "Discover and equip your swarm with professional role agents. Free agents are available to everyone — purchase premium agents to unlock specialized capabilities.",
        filterAll: "All",
        filterFree: "Free",
        filterPaid: "Paid",
        filterPurchased: "Purchased",
        useAgent: "Use Agent",
        buyAgent: "Buy",
        purchased: "Purchased",
        free: "FREE",
        rating: (n: number) => `${n.toFixed(1)} ★`,
        downloads: (n: number) => `${n.toLocaleString()} downloads`,
        noResults: "No agents match the current filter.",
        lockedHint: "Purchase this agent to use it."
      },
      storeAgents: [
        {
          name: "Sales Agent",
          role: "Acquisition operator",
          description: "Digitizes outbound sales motions into repeatable workflows with lead mapping and pipeline design capabilities.",
          status: "active",
          skills: ["Lead mapping", "Pipeline design", "CRM sync"],
          pricing: "free",
          price: 0,
          purchased: true,
          category: "Sales",
          rating: 4.7,
          downloads: 2840
        },
        {
          name: "Content Strategist",
          role: "Narrative strategist",
          description: "Plans editorial calendars, adapts messaging across channels, and generates launch content systems.",
          status: "active",
          skills: ["Editorial planning", "Channel adaptation", "SEO writing"],
          pricing: "paid",
          price: 19.99,
          purchased: false,
          category: "Marketing",
          rating: 4.9,
          downloads: 1520
        },
        {
          name: "Research Analyst",
          role: "Market analyst",
          description: "Scans market signals, maps competitors, and extracts actionable insights from unstructured sources.",
          status: "active",
          skills: ["Signal scanning", "Competitor mapping", "Trend analysis"],
          pricing: "free",
          price: 0,
          purchased: true,
          category: "Research",
          rating: 4.5,
          downloads: 3210
        },
        {
          name: "Finance Controller",
          role: "Operating controller",
          description: "Builds budget models, tracks unit economics, and reconciles revenue data across business lines.",
          status: "queued",
          skills: ["Budget model", "Unit economics", "Forecasting"],
          pricing: "paid",
          price: 29.99,
          purchased: true,
          category: "Finance",
          rating: 4.6,
          downloads: 980
        },
        {
          name: "Customer Support Agent",
          role: "Support operator",
          description: "Triages inbound tickets, auto-responds to FAQs, and escalates complex issues to human agents.",
          status: "active",
          skills: ["Ticket triage", "FAQ matching", "Escalation routing"],
          pricing: "free",
          price: 0,
          purchased: true,
          category: "Support",
          rating: 4.3,
          downloads: 4100
        },
        {
          name: "Legal Compliance Reviewer",
          role: "Compliance specialist",
          description: "Reviews documents for regulatory compliance, flags risks, and generates audit-ready summaries.",
          status: "review",
          skills: ["Policy scanning", "Risk flagging", "Audit summaries"],
          pricing: "paid",
          price: 49.99,
          purchased: false,
          category: "Legal",
          rating: 4.8,
          downloads: 620
        },
        {
          name: "Data Pipeline Engineer",
          role: "Data operator",
          description: "Designs ETL pipelines, normalizes data from multiple sources, and schedules recurring ingestion jobs.",
          status: "active",
          skills: ["ETL design", "Schema mapping", "Scheduling"],
          pricing: "paid",
          price: 24.99,
          purchased: false,
          category: "Engineering",
          rating: 4.4,
          downloads: 1350
        },
        {
          name: "Social Media Manager",
          role: "Social strategist",
          description: "Schedules posts, analyzes engagement metrics, and optimizes content timing across social platforms.",
          status: "active",
          skills: ["Content scheduling", "Engagement analytics", "A/B testing"],
          pricing: "free",
          price: 0,
          purchased: true,
          category: "Marketing",
          rating: 4.2,
          downloads: 5600
        }
      ]
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
      nav: ["总览", "Agent 控制台", "工作流", "角色 Agent", "Swarms", "技能", "记忆", "算力", "设置"],
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
      artifacts: ["角色地图", "工作流计划", "发布叙事", "财务假设"],
      workflows: {
        navLabel: "工作流",
        title: "工作流构建器",
        description:
          "设计和配置自动化工作流，作为可复用的构建块。每个工作流是一系列步骤——大模型调用、HTTP 请求、代码执行、条件判断和知识检索——Agent 可以在运行时选择并调用。",
        createLabel: "新建工作流",
        editLabel: "编辑工作流",
        stepCount: (n: number) => `${n} 个步骤`,
        statusDraft: "草稿",
        statusPublished: "已发布",
        noSteps: "暂无步骤，添加一个步骤开始构建。",
        publish: "发布",
        unpublish: "取消发布",
        duplicate: "复制",
        runDebug: "运行调试",
        addStep: "添加步骤",
        removeStep: "移除",
        moveUp: "上移",
        moveDown: "下移",
        stepNumber: (n: number) => `步骤 ${n}`,
        debugTitle: "调试控制台",
        debugPlaceholder: "运行调试会话以查看步骤输出和变量状态。",
        releaseTitle: "发布",
        releaseDescription:
          "已发布的工作流可供 Agent 选择和调用。草稿工作流仅在构建器中可见。"
      },
      workflowList: [
        {
          name: "内容生成流水线",
          description: "使用大模型从主题简报生成博客内容，包含风格适配和 SEO 优化。",
          status: "published",
          steps: [
            { id: "s1", type: "start", title: "接收主题简报", config: { inputs: "topic, audience, tone" } },
            { id: "s2", type: "llm", title: "使用 GPT-4 生成草稿", config: { model: "gpt-4", temperature: "0.7", maxTokens: "4096" } },
            { id: "s3", type: "code", title: "应用 SEO 格式化", config: { language: "python", snippet: "def optimize_seo(text): ..." } },
            { id: "s4", type: "end", title: "返回最终内容", config: { outputs: "content, wordCount, seoScore" } }
          ]
        },
        {
          name: "客服工单分流",
          description: "对入站支持工单进行分类，将紧急问题路由给人工客服，自动回复常见问题。",
          status: "draft",
          steps: [
            { id: "s1", type: "start", title: "接收支持工单", config: { inputs: "ticketText, customerTier" } },
            { id: "s2", type: "condition", title: "检查紧急级别", config: { variable: "customerTier", operator: "equals", value: "premium" } },
            { id: "s3", type: "llm", title: "生成 FAQ 回复", config: { model: "gpt-4o", temperature: "0.3", maxTokens: "2048" } },
            { id: "s4", type: "http-request", title: "升级至 Zendesk", config: { method: "POST", url: "https://api.zendesk.com/tickets" } },
            { id: "s5", type: "end", title: "返回处理结果", config: { outputs: "response, escalated, ticketId" } }
          ]
        },
        {
          name: "数据增强流程",
          description: "通过查询外部 API 和知识库来增强潜在客户记录，并规范化结果。",
          status: "published",
          steps: [
            { id: "s1", type: "start", title: "接收潜在客户记录", config: { inputs: "companyName, domain" } },
            { id: "s2", type: "http-request", title: "获取公司画像", config: { method: "GET", url: "https://api.example.com/companies" } },
            { id: "s3", type: "knowledge", title: "查询行业知识库", config: { knowledgeBase: "industry-reports", topK: "5" } },
            { id: "s4", type: "llm", title: "规范化增强数据", config: { model: "gpt-4o-mini", temperature: "0.1", maxTokens: "2048" } },
            { id: "s5", type: "end", title: "返回增强记录", config: { outputs: "enrichedData, confidenceScore" } }
          ]
        }
      ],
      workflowStepTypes: {
        start: { label: "开始", category: "flow", fields: ["inputs"] },
        llm: { label: "大模型", category: "ai", fields: ["model", "systemPrompt", "temperature", "maxTokens"] },
        "http-request": { label: "HTTP 请求", category: "integration", fields: ["method", "url", "headers", "body"] },
        code: { label: "代码", category: "logic", fields: ["language", "code"] },
        condition: { label: "条件判断", category: "logic", fields: ["variable", "operator", "value", "trueBranch", "falseBranch"] },
        knowledge: { label: "知识库", category: "ai", fields: ["knowledgeBase", "query", "topK"] },
        end: { label: "结束", category: "flow", fields: ["outputs"] }
      },
      store: {
        title: "角色 Agent 商店",
        description:
          "发现并为你的 Swarm 配备专业角色 Agent。免费 Agent 对所有用户开放——购买高级 Agent 解锁专业能力。",
        filterAll: "全部",
        filterFree: "免费",
        filterPaid: "付费",
        filterPurchased: "已购买",
        useAgent: "使用 Agent",
        buyAgent: "购买",
        purchased: "已购买",
        free: "免费",
        rating: (n: number) => `${n.toFixed(1)} ★`,
        downloads: (n: number) => `${n.toLocaleString()} 次下载`,
        noResults: "没有匹配当前筛选条件的 Agent。",
        lockedHint: "购买此 Agent 后可用。"
      },
      storeAgents: [
        {
          name: "销售 Agent",
          role: "获客运营者",
          description: "将外呼销售动作数字化为可复用的工作流，具备线索映射和管线设计能力。",
          status: "active",
          skills: ["线索映射", "管线设计", "CRM 同步"],
          pricing: "free",
          price: 0,
          purchased: true,
          category: "销售",
          rating: 4.7,
          downloads: 2840
        },
        {
          name: "内容策略师",
          role: "叙事策略师",
          description: "规划选题日历，跨渠道适配信息，生成发布内容系统。",
          status: "active",
          skills: ["选题规划", "渠道适配", "SEO 写作"],
          pricing: "paid",
          price: 19.99,
          purchased: false,
          category: "营销",
          rating: 4.9,
          downloads: 1520
        },
        {
          name: "研究分析师",
          role: "市场分析师",
          description: "扫描市场信号，映射竞品，从非结构化来源中提取可执行的洞察。",
          status: "active",
          skills: ["信号扫描", "竞品映射", "趋势分析"],
          pricing: "free",
          price: 0,
          purchased: true,
          category: "研究",
          rating: 4.5,
          downloads: 3210
        },
        {
          name: "财务控制员",
          role: "经营控制员",
          description: "构建预算模型，跟踪单位经济指标，跨业务线核对收入数据。",
          status: "queued",
          skills: ["预算模型", "单位经济", "预测"],
          pricing: "paid",
          price: 29.99,
          purchased: true,
          category: "财务",
          rating: 4.6,
          downloads: 980
        },
        {
          name: "客服 Agent",
          role: "支持运营者",
          description: "分流入站工单，自动回复常见问题，将复杂问题升级给人工客服。",
          status: "active",
          skills: ["工单分流", "FAQ 匹配", "升级路由"],
          pricing: "free",
          price: 0,
          purchased: true,
          category: "支持",
          rating: 4.3,
          downloads: 4100
        },
        {
          name: "法务合规审查员",
          role: "合规专员",
          description: "审查文件的合规性，标记风险，生成可审计的摘要。",
          status: "review",
          skills: ["政策扫描", "风险标记", "审计摘要"],
          pricing: "paid",
          price: 49.99,
          purchased: false,
          category: "法务",
          rating: 4.8,
          downloads: 620
        },
        {
          name: "数据管线工程师",
          role: "数据运营者",
          description: "设计 ETL 管线，规范化多源数据，调度定期数据采集任务。",
          status: "active",
          skills: ["ETL 设计", "模式映射", "任务调度"],
          pricing: "paid",
          price: 24.99,
          purchased: false,
          category: "工程",
          rating: 4.4,
          downloads: 1350
        },
        {
          name: "社交媒体经理",
          role: "社交策略师",
          description: "排期发布内容，分析互动指标，优化跨平台内容发布时机。",
          status: "active",
          skills: ["内容排期", "互动分析", "A/B 测试"],
          pricing: "free",
          price: 0,
          purchased: true,
          category: "营销",
          rating: 4.2,
          downloads: 5600
        }
      ]
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
export type WorkflowData = AppContent["console"]["workflowList"][number];
export type WorkflowStep = WorkflowData["steps"][number];
export type WorkflowStepType = keyof AppContent["console"]["workflowStepTypes"];
export type StoreAgent = AppContent["console"]["storeAgents"][number];

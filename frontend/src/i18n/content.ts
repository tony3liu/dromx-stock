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
    nav: { agents: "Role Agents", skills: "Skills", swarms: "Swarms", console: "Console" },
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
      nav: ["Agent Console", "Swarm", "Skills Workbench", "Workflows", "Compute"],
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
      ],
      swarm: {
        headerLabel: "Swarm Console",
        title: "Agent Swarm Orchestration",
        subtitle: "Group your owned agents into collaborative swarms. Each swarm works together as a coordinated team.",
        swarmCount: (n: number) => `${n} Swarm${n !== 1 ? "s" : ""}`,
        availableAgentCount: (n: number) => `${n} Agent${n !== 1 ? "s" : ""} Available`,
        createButton: "Create Swarm",
        editButton: "Edit",
        deleteButton: "Delete",
        confirmDelete: "Remove this swarm?",
        form: {
          name: "Swarm Name",
          namePlaceholder: "e.g. Engineering Team",
          description: "Description",
          descriptionPlaceholder: "What does this swarm do?",
          agentsInSwarm: "Agents in Swarm",
          availableAgents: "Available Agents",
          noAgentsSelected: "No agents selected. Add agents from the available pool below.",
          leaderLabel: "Leader Agent",
          leaderHint: "Select one agent as the swarm leader. Required.",
          save: "Save Swarm",
          cancel: "Cancel"
        },
        emptyState: "No swarms yet. Create your first agent swarm to get started."
      },
      computeCenter: {
        headerLabel: "Compute Center",
        title: "Model Compute Infrastructure",
        subtitle: "Configure your own model providers or browse DromX's built-in model catalog.",
        providerCount: (n: number) => `${n} Provider${n !== 1 ? "s" : ""}`,
        modelCount: (n: number) => `${n} Model${n !== 1 ? "s" : ""}`,
        freeModelCount: (n: number) => `${n} Free`,
        tabs: {
          myProviders: "My Providers",
          modelCatalog: "Model Catalog"
        },
        providers: {
          title: "Custom Model Providers",
          description: "Connect your own API-compatible model services by configuring provider endpoints and credentials.",
          emptyState: "No providers configured yet. Add your first model provider below.",
          addButton: "Add Provider",
          form: {
            name: "Provider Name",
            namePlaceholder: "e.g. My OpenAI Endpoint",
            baseUrl: "Base URL",
            baseUrlPlaceholder: "https://api.openai.com/v1",
            apiKey: "API Key",
            apiKeyPlaceholder: "sk-...",
            modelNames: "Model Names",
            modelNamesPlaceholder: "e.g. gpt-4o, gpt-4o-mini",
            modelNamesHint: "Comma-separated list of model identifiers",
            save: "Save Provider",
            update: "Update Provider",
            cancel: "Cancel",
            testConnection: "Test Connection",
            delete: "Remove",
            confirmDelete: "Remove this provider?"
          },
          status: {
            connected: "Connected",
            testing: "Testing...",
            error: "Connection Error",
            untested: "Untested"
          }
        },
        catalog: {
          title: "Built-in Model Catalog",
          description: "Browse and deploy DromX's curated selection of models. Free models are available to everyone.",
          filterAll: "All",
          filterFree: "Free",
          filterPaid: "Paid",
          filterPurchased: "Purchased",
          searchPlaceholder: "Search models...",
          contextWindow: "Context Window",
          speed: "Inference Speed",
          useModel: "Use Model",
          buyModel: "Buy",
          free: "FREE",
          purchased: "Purchased",
          noResults: "No models match the current filter.",
          lockedHint: "Purchase this model to deploy it."
        }
      }
    },
    skills: {
      title: "Skills Center",
      eyebrow: "Skills Center",
      description: "Browse public Skills, manage drafts, and publish your own capabilities.",
      counts: {
        skills: (n: number) => `${n} ${n === 1 ? "Skill" : "Skills"}`,
        free: (n: number) => `${n} Free`,
        paid: (n: number) => `${n} Paid`,
        installed: (n: number) => `${n} Installed`,
        myDrafts: (n: number) => `${n} My ${n === 1 ? "Draft" : "Drafts"}`
      },
      viewsLabel: "Skills views",
      store: "Store",
      mySkills: "My Skills",
      filters: {
        all: "All",
        free: "Free",
        paid: "Paid",
        installed: "Installed",
        draft: "Draft"
      },
      searchLabel: "Search skills",
      searchPlaceholder: "Search skills...",
      catalogLabel: "Skill catalog",
      detailLabel: "Skill Detail",
      detailsRegion: "Skill details",
      publicSkill: "Public Skill",
      privateSkill: "Private Skill",
      tools: "Tools",
      inputsOutputs: "Inputs & Outputs",
      agents: "Agents",
      installs: (n: number) => `${n.toLocaleString()} installs`,
      priceFree: "Free",
      pricePaid: (n: number) => `$${n.toFixed(2)}`,
      statuses: {
        draft: "Draft",
        review: "Review",
        published: "Published"
      },
      actions: {
        install: "Install",
        disable: "Disable",
        enable: "Enable",
        create: "Create Skill",
        openBuilder: "Open Builder",
        saveDraft: "Save Draft",
        submitReview: "Submit Review",
        submitForReview: "Submit for Review",
        publish: "Publish",
        backToSkills: "Back to Skills"
      },
      workspaceTitle: "Private Workspace",
      workspaceDescription: "Draft Skills stay private until published.",
      capabilityLoop: "Capability Loop",
      publishPath: "Publish Path",
      builder: {
        title: "New Skill",
        eyebrow: "Skill Builder",
        breadcrumbConsole: "Console",
        breadcrumbSkills: "Skills",
        breadcrumbBuilder: "Builder",
        description: "Create a private draft before publishing it to the store.",
        mySkill: "My Skill",
        details: "Skill Details",
        name: "Name",
        summary: "Summary",
        toolsMcp: "Tools / MCP",
        inputsOutputs: "Inputs and Outputs",
        inputs: "Inputs",
        outputs: "Outputs",
        publishFlow: "Publish Flow"
      },
      catalog: {
        "lead-mapper": {
          name: "Lead Mapper",
          category: "Sales",
          summary: "Turns raw prospect signals into structured lead routes.",
          description: "Maps outbound discovery, qualification, and routing into a repeatable sales workflow.",
          agentTypes: ["Sales Agent", "Growth Agent"],
          tools: ["CRM Sync", "Spreadsheet Parser"],
          inputs: ["Lead list", "ICP rules", "Signal feed"],
          outputs: ["Qualified leads", "Routing notes"],
          publisher: "DromX Labs"
        },
        "content-packager": {
          name: "Content Packager",
          category: "Marketing",
          summary: "Shapes positioning notes into channel-ready content.",
          description: "Packages briefs into launches, newsletters, and multi-channel publication plans.",
          agentTypes: ["Content Agent", "Brand Agent"],
          tools: ["Outline Generator", "Tone Adapter"],
          inputs: ["Positioning brief", "Voice rules"],
          outputs: ["Draft outline", "Channel variants"],
          publisher: "DromX Labs"
        },
        "research-signal": {
          name: "Research Signal Scanner",
          category: "Research",
          summary: "Extracts market assumptions from notes and documents.",
          description: "Scans source material, detects patterns, and produces structured market signals.",
          agentTypes: ["Research Agent"],
          tools: ["Web Notes", "Source Extractor"],
          inputs: ["Source notes", "Search scope"],
          outputs: ["Signals", "Evidence list"],
          publisher: "DromX Labs"
        },
        "finance-guard": {
          name: "Finance Guardrails",
          category: "Finance",
          summary: "Keeps budget assumptions and operating metrics aligned.",
          description: "Builds basic financial operating checks and flags mismatches in the model.",
          agentTypes: ["Finance Agent"],
          tools: ["Model Checker", "Assumption Diff"],
          inputs: ["Revenue plan", "Cost model"],
          outputs: ["Budget warnings", "Model notes"],
          publisher: "DromX Labs"
        },
        "my-launch-draft": {
          name: "Launch Brief Builder",
          category: "Marketing",
          summary: "My private draft Skill for launch planning.",
          description: "Draft-only helper for turning launch inputs into a structured campaign brief.",
          agentTypes: ["Content Agent"],
          tools: ["Draft Editor"],
          inputs: ["Launch notes"],
          outputs: ["Campaign brief"],
          publisher: "Me"
        },
        "my-research-skill": {
          name: "Signal Extractor",
          category: "Research",
          summary: "My own research draft for source extraction.",
          description: "Private workflow for pulling structured signals from raw notes.",
          agentTypes: ["Research Agent"],
          tools: ["Notes Parser"],
          inputs: ["Notes", "Prompt template"],
          outputs: ["Structured findings"],
          publisher: "Me"
        },
        "my-new-skill": {
          name: "Untitled Skill",
          category: "General",
          summary: "Describe the capability in one clear sentence.",
          description: "Draft-only helper for turning launch inputs into a structured skill.",
          agentTypes: ["Agent"],
          tools: ["Draft Editor"],
          inputs: ["Notes"],
          outputs: ["Draft output"],
          publisher: "Me"
        }
      }
    },
    swarmsCenter: {
      title: "Swarms Center",
      eyebrow: "Swarms Center",
      description: "Browse and manage your assembled agent swarms. Each swarm is a hand-picked team ready to collaborate.",
      searchPlaceholder: "Search swarms...",
      swarmCount: (n: number) => `${n} Swarm${n !== 1 ? "s" : ""}`,
      agentCount: (n: number) => `${n} Agent${n !== 1 ? "s" : ""}`,
      useSwarm: "Use Swarm",
      emptyState: "No swarms yet. Create your first swarm in the Console.",
      agents: "Agents"
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
    nav: { agents: "角色 Agent", skills: "技能中心", swarms: "Swarm 中心", console: "控制台" },
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
      nav: ["Agent 控制台", "Swarm 控制台", "技能工作台", "工作流", "算力中心"],
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
      ],
      swarm: {
        headerLabel: "Swarm 控制台",
        title: "Agent 团体编排",
        subtitle: "将你拥有的 Agent 组合成协作团体，协同完成复杂任务。",
        swarmCount: (n: number) => `${n} 个团体`,
        availableAgentCount: (n: number) => `${n} 个 Agent 可用`,
        createButton: "创建团体",
        editButton: "编辑",
        deleteButton: "删除",
        confirmDelete: "确认删除此团体？",
        form: {
          name: "团体名称",
          namePlaceholder: "例如：研发部",
          description: "描述",
          descriptionPlaceholder: "这个团体负责什么工作？",
          agentsInSwarm: "团体成员",
          availableAgents: "可用 Agent",
          noAgentsSelected: "尚未选择 Agent。从下方可用池中添加。",
          leaderLabel: "Leader Agent",
          leaderHint: "选择一个 Agent 作为团体 Leader。必填。",
          save: "保存团体",
          cancel: "取消"
        },
        emptyState: "尚无团体，点击创建第一个 Agent 团体。"
      },
      computeCenter: {
        headerLabel: "算力中心",
        title: "模型算力基础设施",
        subtitle: "配置你自己的模型供应商，或浏览 DromX 内置模型目录。",
        providerCount: (n: number) => `${n} 个供应商`,
        modelCount: (n: number) => `${n} 个模型`,
        freeModelCount: (n: number) => `${n} 个免费`,
        tabs: {
          myProviders: "我的供应商",
          modelCatalog: "模型商店"
        },
        providers: {
          title: "自定义模型供应商",
          description: "配置 API 兼容的模型服务端点与凭证，接入你自己的模型算力。",
          emptyState: "尚未配置供应商，请在下方添加你的第一个模型供应商。",
          addButton: "添加供应商",
          form: {
            name: "供应商名称",
            namePlaceholder: "例如：我的 OpenAI 端点",
            baseUrl: "Base URL",
            baseUrlPlaceholder: "https://api.openai.com/v1",
            apiKey: "API Key",
            apiKeyPlaceholder: "sk-...",
            modelNames: "模型列表",
            modelNamesPlaceholder: "例如：gpt-4o, gpt-4o-mini",
            modelNamesHint: "多个模型名以英文逗号分隔",
            save: "保存供应商",
            update: "更新供应商",
            cancel: "取消",
            testConnection: "测试连接",
            delete: "删除",
            confirmDelete: "确认删除此供应商？"
          },
          status: {
            connected: "已连接",
            testing: "测试中...",
            error: "连接失败",
            untested: "未测试"
          }
        },
        catalog: {
          title: "内置模型目录",
          description: "浏览并使用 DromX 精选模型，免费模型人人可用。",
          filterAll: "全部",
          filterFree: "免费",
          filterPaid: "付费",
          filterPurchased: "已购买",
          searchPlaceholder: "搜索模型...",
          contextWindow: "上下文窗口",
          speed: "推理速度",
          useModel: "使用模型",
          buyModel: "购买",
          free: "免费",
          purchased: "已购买",
          noResults: "当前筛选条件下无匹配模型。",
          lockedHint: "购买此模型即可部署使用。"
        }
      }
    },
    skills: {
      title: "技能中心",
      eyebrow: "技能中心",
      description: "浏览公共技能，管理草稿，并发布你自己的能力模块。",
      counts: {
        skills: (n: number) => `${n} 个技能`,
        free: (n: number) => `${n} 个免费`,
        paid: (n: number) => `${n} 个付费`,
        installed: (n: number) => `${n} 个已安装`,
        myDrafts: (n: number) => `${n} 个我的草稿`
      },
      viewsLabel: "技能视图",
      store: "商店",
      mySkills: "我的技能",
      filters: {
        all: "全部",
        free: "免费",
        paid: "付费",
        installed: "已安装",
        draft: "草稿"
      },
      searchLabel: "搜索技能",
      searchPlaceholder: "搜索技能...",
      catalogLabel: "技能目录",
      detailLabel: "技能详情",
      detailsRegion: "技能详情",
      publicSkill: "公共技能",
      privateSkill: "私有技能",
      tools: "工具",
      inputsOutputs: "输入与输出",
      agents: "角色 Agent",
      installs: (n: number) => `${n.toLocaleString()} 次安装`,
      priceFree: "免费",
      pricePaid: (n: number) => `¥${Math.round(n * 7)}`,
      statuses: {
        draft: "草稿",
        review: "审核中",
        published: "已发布"
      },
      actions: {
        install: "安装",
        disable: "停用",
        enable: "启用",
        create: "创建技能",
        openBuilder: "打开编辑器",
        saveDraft: "保存草稿",
        submitReview: "提交审核",
        submitForReview: "提交审核",
        publish: "发布",
        backToSkills: "返回技能中心"
      },
      workspaceTitle: "私有工作区",
      workspaceDescription: "草稿技能在发布前仅自己可见。",
      capabilityLoop: "能力循环",
      publishPath: "发布路径",
      builder: {
        title: "新建技能",
        eyebrow: "技能编辑器",
        breadcrumbConsole: "控制台",
        breadcrumbSkills: "技能",
        breadcrumbBuilder: "编辑器",
        description: "先创建私有草稿，再发布到商店。",
        mySkill: "我的技能",
        details: "技能详情",
        name: "名称",
        summary: "摘要",
        toolsMcp: "工具 / MCP",
        inputsOutputs: "输入与输出",
        inputs: "输入",
        outputs: "输出",
        publishFlow: "发布流程"
      },
      catalog: {
        "lead-mapper": {
          name: "线索映射器",
          category: "销售",
          summary: "将原始潜客信号转化为结构化线索路径。",
          description: "把外呼发现、资格判断和线索分配映射成可复用的销售工作流。",
          agentTypes: ["销售 Agent", "增长 Agent"],
          tools: ["CRM 同步", "表格解析器"],
          inputs: ["线索列表", "ICP 规则", "信号流"],
          outputs: ["合格线索", "分配记录"],
          publisher: "DromX Labs"
        },
        "content-packager": {
          name: "内容打包器",
          category: "营销",
          summary: "将定位笔记整理成可发布的多渠道内容。",
          description: "把简报封装成发布计划、邮件通讯和多渠道内容方案。",
          agentTypes: ["内容 Agent", "品牌 Agent"],
          tools: ["大纲生成器", "语气适配器"],
          inputs: ["定位简报", "语气规则"],
          outputs: ["内容大纲", "渠道版本"],
          publisher: "DromX Labs"
        },
        "research-signal": {
          name: "研究信号扫描器",
          category: "研究",
          summary: "从笔记和文档中提取市场假设。",
          description: "扫描来源材料，识别模式，并产出结构化市场信号。",
          agentTypes: ["研究 Agent"],
          tools: ["网页笔记", "来源提取器"],
          inputs: ["来源笔记", "搜索范围"],
          outputs: ["信号", "证据列表"],
          publisher: "DromX Labs"
        },
        "finance-guard": {
          name: "财务护栏",
          category: "财务",
          summary: "保持预算假设与经营指标一致。",
          description: "构建基础财务经营检查，并标记模型中的不一致。",
          agentTypes: ["财务 Agent"],
          tools: ["模型检查器", "假设差异"],
          inputs: ["收入计划", "成本模型"],
          outputs: ["预算预警", "模型备注"],
          publisher: "DromX Labs"
        },
        "my-launch-draft": {
          name: "发布简报构建器",
          category: "营销",
          summary: "用于发布规划的私有草稿技能。",
          description: "把发布输入整理成结构化活动简报的草稿能力。",
          agentTypes: ["内容 Agent"],
          tools: ["草稿编辑器"],
          inputs: ["发布笔记"],
          outputs: ["活动简报"],
          publisher: "我"
        },
        "my-research-skill": {
          name: "信号提取器",
          category: "研究",
          summary: "用于来源提取的私有研究草稿。",
          description: "从原始笔记中提取结构化信号的私有工作流。",
          agentTypes: ["研究 Agent"],
          tools: ["笔记解析器"],
          inputs: ["笔记", "提示词模板"],
          outputs: ["结构化发现"],
          publisher: "我"
        },
        "my-new-skill": {
          name: "未命名技能",
          category: "通用",
          summary: "用一句清晰的话描述这个能力。",
          description: "把输入整理成结构化技能的私有草稿能力。",
          agentTypes: ["Agent"],
          tools: ["草稿编辑器"],
          inputs: ["笔记"],
          outputs: ["草稿输出"],
          publisher: "我"
        }
      }
    },
    swarmsCenter: {
      title: "Swarm 中心",
      eyebrow: "Swarm 中心",
      description: "浏览和管理你组装的 Agent 团体。每个团体都是精心搭配、可协同工作的团队。",
      searchPlaceholder: "搜索团体...",
      swarmCount: (n: number) => `${n} 个团体`,
      agentCount: (n: number) => `${n} 个 Agent`,
      useSwarm: "使用团体",
      emptyState: "尚无团体，前往控制台创建你的第一个 Agent 团体。",
      agents: "成员 Agent"
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

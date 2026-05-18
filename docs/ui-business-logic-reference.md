# Agent Swarm OPC Platform UI Business Logic Reference

This document captures the initial business logic and information architecture for the first UI design phase. It is based on the PRD direction: an AI-native operating system for one-person companies, combining Agent Swarm orchestration, a Skills marketplace, and GPU-native compute.

## Product Surface Overview

The first UI scope is organized around four major surfaces:

1. Landing Page
2. Agent Console
3. Skills Marketplace
4. GPU Resources

These pages should not be designed as isolated screens. Together, they form the core product loop:

```text
Landing Page
-> user signs up or enters workspace
-> Agent Console starts business workflows
-> Skills Marketplace provides executable capabilities
-> GPU Resources supplies compute and cost control
-> workflow outputs return to the Agent Console
-> repeated usage creates memory, workflow reuse, and monetization
```

## 1. Landing Page

### Business Role

The landing page is responsible for acquisition, positioning, and trust building. It should answer:

- What is this product?
- Who is it for?
- Why should the user trust it?
- What can the user do next?

The page should sell the idea of an AI operating system for one-person companies, not a generic chatbot or ordinary SaaS dashboard.

### Target User

- One-person company founders
- Independent operators
- Solo entrepreneurs
- Small teams that operate like one-person companies

### Core Message

A one-person company can use Agent Swarm to operate like a larger AI-native team. The platform provides autonomous agents, installable skills, and GPU-backed compute in one system.

### Business Logic

```text
User has too many business tasks
-> current tools are fragmented
-> Agent Swarm creates an AI execution team
-> Skills let agents perform concrete business actions
-> GPU resources provide scalable, cost-controlled execution
-> user signs up and enters the Agent Console
```

### Key Content Blocks

- Product positioning: AI operating system for one-person companies
- Core value: run business workflows with autonomous agents
- Three-layer platform explanation:
  - Agent Swarm
  - Skills Marketplace
  - GPU Compute
- Use cases:
  - lead generation
  - content creation
  - customer management
  - finance and bookkeeping
  - data analysis
  - operations automation
- Trust builders:
  - execution trace
  - permission control
  - audit logs
  - compute cost visibility
  - security and sandboxing

### Primary Conversion Actions

- Sign up
- Book demo
- Enter console

## 2. Agent Console

### Business Role

The Agent Console is the product core. It is where users command their AI team, monitor active work, review outputs, and reuse workflows.

It should not feel like a simple chat screen. It should feel like an operational command center for autonomous business execution.

### Core Business Objects

- Main Agent: understands user intent, decomposes tasks, and schedules execution.
- Worker Agent: performs assigned subtasks.
- Workflow: a complete business process triggered by the user.
- Task: a subtask inside a workflow.
- Tool Call: a concrete action through a skill, API, model, or external integration.
- Memory: historical context, company profile, customer data, brand voice, and workflow learnings.
- Output: the final result of a workflow, such as copy, analysis, reports, customer lists, drafts, or structured data.

### Business Logic

```text
User submits a business goal
-> Main Agent interprets the goal
-> system creates a workflow
-> workflow is decomposed into tasks
-> required Skills are selected
-> Worker Agents execute tasks
-> system tracks status, retries, and errors
-> outputs are collected and summarized
-> useful context is written back into memory
-> workflow can be reused or scheduled
```

### Required UI Capabilities

- Submit a natural language business objective
- View active workflows
- Inspect task decomposition
- See agent assignments
- Monitor execution timeline
- Review tool calls and intermediate results
- Handle confirmation requests
- Retry failed steps
- Approve, edit, export, or reuse final outputs

### Important States

- Idle
- Planning
- Running
- Waiting for user confirmation
- Blocked
- Retrying
- Failed
- Completed

### Key Panels

- Active workflow list
- Task decomposition tree
- Agent activity panel
- Execution timeline
- Output preview
- Audit and event log
- Memory references

## 3. Skills Marketplace

### Business Role

The Skills Marketplace turns the platform from a general agent system into a business-capable operating system.

Skills are installable capability modules that agents can call during workflows. A skill may be an API wrapper, prompt package, workflow template, MCP server, data connector, or domain-specific automation tool.

### Core Business Objects

- Skill: a capability module that can be installed and called by agents.
- Category: business grouping such as marketing, sales, content, finance, customer management, data, or supply chain.
- Permission: data and tool access required by the skill.
- Version: release and compatibility metadata.
- Developer: creator or vendor of a skill.
- Installation: user-specific skill install and configuration record.
- Usage: invocation count, success rate, cost, and performance.
- Revenue Share: marketplace monetization and platform commission.

### Business Logic

```text
User has a business need
-> system recommends relevant Skills
-> user reviews capability, permissions, price, and trust signals
-> user installs and configures the Skill
-> Agent can call the Skill inside workflows
-> usage is tracked
-> cost and quality signals feed marketplace ranking
```

### Required UI Capabilities

- Browse skills by category
- Search by business need
- Filter by price, rating, usage, permission level, and compatibility
- View skill details
- Preview required permissions
- Install, configure, update, disable, or uninstall a skill
- Test run a skill
- View usage and billing impact

### Key Skill Detail Content

- What business problem it solves
- Supported workflows
- Required permissions
- Data access scope
- Price or billing model
- Version history
- Developer information
- Compatibility with Agent runtime
- Usage stats
- Security status

### Security Requirements

Skills must expose permissions clearly before installation. At minimum, the UI should support:

- Data access disclosure
- External network access disclosure
- Tool execution disclosure
- Cost impact disclosure
- Version and update visibility
- Disable or revoke access

## 4. GPU Resources

### Business Role

The GPU Resources page makes compute usage visible, controllable, and billable.

For normal OPC users, this page should focus on speed, balance, quota, running workload, and estimated cost. For advanced or enterprise users, it can expose model services, node health, queues, autoscaling, and detailed billing.

### Core Business Objects

- Compute Plan: subscription or usage package.
- GPU Node: available compute node.
- Model Service: hosted inference endpoint or model route.
- Job Queue: pending and running compute jobs.
- Usage: consumed compute, tokens, requests, or runtime.
- Cost: billable amount.
- Quota: plan limit or remaining allowance.
- Voucher: compute coupon or government subsidy.
- Autoscaling Policy: scaling behavior for workloads.

### Business Logic

```text
Agent workflow needs model or compute resources
-> system requests GPU Compute
-> compute scheduler selects node or model service
-> job enters queue or executes immediately
-> usage is measured
-> cost is calculated
-> quota and billing are updated
-> status returns to Agent Console
```

### Required UI Capabilities

- View current compute balance
- View monthly usage and projected cost
- Inspect active jobs consuming compute
- Monitor model service status
- See queue depth and estimated wait time
- Understand cost by workflow, skill, or model
- Apply or view compute vouchers
- Upgrade plan or adjust limits

### Key Panels

- Current plan and quota
- Monthly usage summary
- Active compute jobs
- Model service status
- GPU utilization
- Cost forecast
- Voucher and subsidy status
- Autoscaling controls for advanced users

## Cross-Page Business Loop

The pages should reinforce one product loop:

```text
Acquire user through Landing Page
-> activate user in Agent Console
-> expand capability through Skills Marketplace
-> consume and manage compute through GPU Resources
-> return execution results to Agent Console
-> retain user through memory, reusable workflows, and improved recommendations
```

## Page Positioning Summary

| Page | Purpose | Primary User Question |
| --- | --- | --- |
| Landing Page | Acquisition and trust | Why should I try this? |
| Agent Console | Business execution | What is my AI team doing now? |
| Skills Marketplace | Capability expansion | What can my agents learn to do? |
| GPU Resources | Compute control and billing | How much compute am I using and paying for? |

## MVP Priority

Recommended first implementation priority:

1. Agent Console
2. Skills Marketplace
3. Landing Page
4. GPU Resources

Rationale:

- Agent Console proves the core product value.
- Skills Marketplace proves extensibility and ecosystem potential.
- Landing Page supports acquisition and conversion.
- GPU Resources can start as a simplified usage and billing view before evolving into a full infrastructure console.

## UX Design Principles

- The product should feel operational, not promotional.
- The UI should show what the system is doing, not only describe what it can do.
- Agent activity should be inspectable and auditable.
- Skills should be understandable before installation.
- Compute costs should be visible before they surprise the user.
- Workflows should be reusable, schedulable, and explainable.
- The system should feel premium, calm, precise, and trustworthy.


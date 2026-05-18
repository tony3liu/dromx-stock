# Agent Console Design Spec

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this spec task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first Agent Console page for DromX, showing how real-world capabilities become role Agents and how those Agents collaborate as a Swarm to execute complex work.

**Architecture:** The Agent Console is a React route/screen inside `frontend/`. It should feel like an operational control surface for a digital labor network, not a chat page and not a generic admin dashboard. The first version is static/mock-data driven, but the component boundaries should map cleanly to future backend APIs for role agents, workflows, tasks, tool calls, memory, and outputs.

**Tech Stack:** React, Vite, TypeScript, plain CSS, Vitest, Testing Library, lucide-react

---

## Product Intent

The console should demonstrate DromX's core idea:

```text
Reality ability
-> digitized professional role
-> Agent with identity, skills, tools, and memory
-> Swarm collaboration
-> persistent digital labor output
```

The user should immediately understand:

- Which role Agents exist in the current Swarm
- What workflow the Swarm is executing
- How the workflow is decomposed into tasks
- Which Agent owns each task
- What tool/skill/memory is being used
- What output is emerging
- Where the user can review or intervene

## Page Structure

### 1. Console Shell

The console should have a product-app layout, separate from the landing page:

- Left navigation: Overview, Agent Console, Role Agents, Swarms, Skills, Memory, Compute, Settings
- Top bar: workspace name, language switch, run status, notifications placeholder
- Main content: active Swarm execution
- Right panel: memory, events, and emerging outputs

### 2. Swarm Overview

Show high-level state:

- Active Swarm name
- Current objective
- Workflow status
- Number of active Agents
- Tasks completed / running / blocked
- Memory updates

### 3. Role Agent Roster

Show role Agents as real-world professional roles:

- Sales Agent
- Content Agent
- Finance Agent
- Research Agent
- Operations Agent

Each card should show:

- Role identity
- Skill coverage
- Current assignment
- Status
- Memory depth or learning signal

### 4. Workflow Decomposition

Show the current workflow as a structured task tree/timeline:

- Intent analysis
- Role mapping
- Skill selection
- Task execution
- Output synthesis
- Human review

Each step should have:

- owner Agent
- status
- short description
- dependency cue

### 5. Execution Feed

Show live-style operational events:

- Agent assigned
- Skill invoked
- Memory retrieved
- Tool call completed
- Output draft generated
- Review requested

### 6. Output Preview

Show the work product emerging from the Swarm:

- Summary
- Generated artifacts
- Review actions
- Export/reuse buttons

## Data Model For Mock UI

Use static arrays in the frontend for the first version:

```ts
type RoleAgent = {
  name: string;
  role: string;
  status: "active" | "review" | "queued" | "idle";
  skills: string[];
  currentTask: string;
  memorySignal: string;
};

type WorkflowStep = {
  title: string;
  owner: string;
  status: "completed" | "running" | "waiting" | "queued";
  description: string;
};

type ExecutionEvent = {
  time: string;
  title: string;
  detail: string;
};
```

## Interaction Requirements

First version:

- Route or state should allow the user to reach Agent Console from the landing page CTA.
- Language switching should continue to work.
- Tabs or segmented controls may be static for now, but should look like real controls.
- Primary actions: Review Output, Re-run Step, Save Workflow.

Later versions:

- Create workflow
- Assign/reassign Agents
- Approve tool calls
- Inspect memory references
- Export output

## Visual Direction

- Same premium dark editorial system as the landing page
- Denser and more operational than the landing page
- No oversized marketing hero
- Use precise grid, thin dividers, compact panels
- Do not nest UI cards inside decorative cards
- Avoid playful illustrations and decorative gradients

## Acceptance Criteria

- User can navigate from landing CTA to Agent Console.
- Console displays Swarm objective, role Agent roster, workflow decomposition, execution feed, and output preview.
- Console supports English/Chinese text through the existing i18n approach.
- Layout is responsive and does not overlap on mobile.
- Frontend tests cover the presence of the console route/screen and key sections.
- `npm test` and `npm run build` pass in `frontend/`.


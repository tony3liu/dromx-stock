# Skills Store Design Spec

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this spec task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a premium Skills app store for DromX where users can browse, search, install, create, and publish Skills, while user-created Skills remain private drafts until published.

**Architecture:** The Skills experience is a dedicated React route group inside `frontend/`. It should behave like a product store plus creator workspace, not a generic settings page. The first version is mock-data driven, but the page boundaries should map cleanly to future backend concepts: public Skill catalog, private drafts, versioned publishing, and installation state. The UI should feel consistent with the existing premium dark DromX design language, but denser and more app-like than the landing page.

**Tech Stack:** React, Vite, TypeScript, plain CSS, Vitest, Testing Library, lucide-react

---

## Product Intent

Skills in DromX are reusable capability modules. They are not just labels or tags; they are the packaged expression of how an Agent can do work.

The user should understand:

- Public Skills can be discovered, inspected, and installed from the store
- Personal Skills can be created privately as drafts
- Draft Skills are visible only to their owner until published
- Publishing moves a Skill from private creation into the shared store flow
- The store and the creator workspace are part of one coherent loop

## Page Model

### 1. Skills Store Home

Route: `/skills`

This page is the main entry point for the module.

It should include:

- A strong page header explaining that Skills are reusable capability packages
- Search and filters for category, pricing, status, and install state
- A market summary strip with counts for total Skills, free Skills, paid Skills, installed Skills, and drafts
- A dense card wall of public Skills
- A detail panel for the selected Skill
- A visible path into personal drafts and Skill creation

### 2. Skill Detail Surface

The selected Skill should expose:

- Name, category, and status
- Short capability summary
- Intended Agent types
- Required tools / MCP dependencies
- Input / output description
- Version and publisher information
- Install / enable / disable actions

### 3. My Skills Workspace

The module should clearly separate public store content from personal work.

This area should show:

- Draft Skills
- Skills awaiting review
- Published Skills owned by the current user
- Draft-only visibility before publication

Draft Skills should not appear in the public store grid until they are published.

### 4. Skill Builder

Route: `/skills/new`

This is the page for creating a new Skill.

It should support:

- Basic metadata
- Skill description
- Capability scope
- Input / output schema
- Tool / MCP dependencies
- Example tests or usage snippets
- Save draft
- Submit for publish / review

This page should feel like an editor, not a modal and not a side panel.

### 5. Skill Lifecycle

Supported mock states:

- `draft`
- `review`
- `published`

Recommended flow:

`draft -> review -> published -> installed`

The UI should make publication flow visible through labels, chips, and actions. Installation is a separate user state that can apply after publication.

## Data Model For Mock UI

Use static arrays in the frontend for the first version:

```ts
type SkillStatus = "draft" | "review" | "published";

type SkillItem = {
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
```

## Interaction Requirements

First version:

- Users can search and filter the public store
- Users can select a Skill to inspect details
- Users can install / enable a Skill from the detail surface
- Users can create a private draft Skill
- Users can save draft changes locally
- Users can submit a draft into the review flow, then publish it from the same UI in mock form
- Users can switch between public store and My Skills views
- Language switching continues to work

Later versions:

- Review queue
- Version history
- Skill cloning
- Publish approval workflow
- Agent compatibility suggestions
- Dependency validation

## Visual Direction

- Same premium dark editorial system as the rest of DromX
- More product-store-like than the console
- Dense grids, clean alignment, thin dividers
- Avoid generic admin dashboard patterns
- Avoid oversized hero marketing composition
- Avoid decorative blobs, heavy gradients, and cartoon-like UI

## Route / Navigation Plan

- Add `Skills` to the primary navigation
- Keep the existing landing page as the homepage
- Use `/skills` as the store home
- Use `/skills/new` for Skill creation
- Optionally reserve `/skills/:id` for later detail deep-linking

## Component Boundaries

The first implementation should split into focused pieces:

- Store summary header
- Filter/search controls
- Skill card wall
- Skill detail panel
- My Skills panel
- Skill builder form

Each piece should be independently understandable and easy to swap to API data later.

## Acceptance Criteria

- User can enter a Skills Store page from the global navigation
- User can browse and filter public Skills
- User can inspect a selected Skill in detail
- User can create a private draft Skill
- Draft Skills stay private until published
- User can move a Skill through draft / review / published states
- Layout is responsive and visually aligned with the current DromX design system
- Frontend tests cover the main Skills route and core interactions
- `npm test` and `npm run build` pass in `frontend/`

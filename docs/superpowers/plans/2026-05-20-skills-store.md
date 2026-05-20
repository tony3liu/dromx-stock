# Skills Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a premium `/skills` app store and `/skills/new` builder where users can browse public Skills, manage private drafts, and publish Skills from a dedicated workspace.

**Architecture:** Add a new Skills route group to the existing React app without folding it into Console. The first version is mock-data driven and should split into a store home, a Skill detail surface, a private drafts workspace, and a full-page builder. The data model must separate publication state from installation/enabled state so public catalog behavior and personal ownership stay unambiguous.

**Tech Stack:** React, Vite, TypeScript, plain CSS, Vitest, Testing Library, lucide-react

---

### Task 1: Add Skills routes and navigation entry points

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/i18n/content.ts`
- Modify: `frontend/src/components/AppHeader.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing test**

Add route/navigation assertions for:
- clicking `Skills` in the top nav opens `/skills`
- clicking `Create Skill` opens `/skills/new`
- browser back/forward preserves the Skills route

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run`

Expected: FAIL because the `/skills` routes and nav entry do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Update the app router to support:
- `/skills`
- `/skills/new`

Add `Skills` to the shared top navigation and keep the existing landing-page logo behavior. Extend i18n content with Skills labels for English and Chinese.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/i18n/content.ts frontend/src/components/AppHeader.tsx frontend/src/App.test.tsx
git commit -m "feat: add skills routes"
```

### Task 2: Build the Skills store page shell

**Files:**
- Create: `frontend/src/pages/SkillsStorePage.tsx`
- Create: `frontend/src/components/skills/SkillCatalog.tsx`
- Create: `frontend/src/components/skills/SkillSidebar.tsx`
- Create: `frontend/src/components/skills/SkillStoreTabs.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing test**

Add assertions that `/skills` renders:
- a store header
- a market summary strip
- search/filter controls for category, pricing, status, and install state
- a Store/My Skills view switch
- a skill grid
- a detail panel for the selected Skill
- a `My Skills` area

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run`

Expected: FAIL because the store page does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create the store page with mock data and focused components:
- header summary
- market summary strip with counts for total, free, paid, installed, and drafts
- explicit segmented switch between public store and My Skills
- filter/search controls
- public skill card wall
- selected skill detail panel
- personal skills summary panel

Keep the layout dense and aligned with the current DromX dark editorial system.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SkillsStorePage.tsx frontend/src/components/skills/SkillCatalog.tsx frontend/src/components/skills/SkillSidebar.tsx frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: build skills store shell"
```

### Task 3: Model skill lifecycle and personal draft behavior

**Files:**
- Create: `frontend/src/data/skills.ts`
- Modify: `frontend/src/pages/SkillsStorePage.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing test**

Add tests that confirm:
- public catalog skills exclude private drafts
- `Draft`, `Review`, and `Published` states are distinct from `installed` and `enabled`
- a personal draft appears only in `My Skills`

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run`

Expected: FAIL because the mock data source and filters do not yet separate lifecycle from user installation state.

- [ ] **Step 3: Write minimal implementation**

Create a shared mock data module for Skills with:
- `status: "draft" | "review" | "published"`
- `installed: boolean`
- `enabled?: boolean`
- `owner: "system" | "me"`
- `summary`, `description`, `category`, `pricing`, `rating`, `installs`, `agentTypes`, `tools`, `inputs`, `outputs`, `version`, `publisher`

Filter the public store so only published system Skills appear there, while `My Skills` shows the user-owned drafts and published items.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/data/skills.ts frontend/src/pages/SkillsStorePage.tsx frontend/src/App.test.tsx
git commit -m "feat: model skills lifecycle"
```

### Task 4: Build the Skill builder page

**Files:**
- Create: `frontend/src/pages/SkillBuilderPage.tsx`
- Create: `frontend/src/components/skills/SkillBuilderForm.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing test**

Add assertions for `/skills/new`:
- shows a full-page editor
- exposes draft save and review/publish actions
- shows fields for metadata, inputs/outputs, tools/MCP, and usage examples
- exposes a publish action that moves a reviewed draft into the published mock state

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run`

Expected: FAIL because the builder route and form do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create a dedicated builder page with mock form state. It should feel like a true editor, not a modal, and should support save draft plus submit to review.
Include a publish control in the same workspace so the draft -> review -> published loop is complete in mock form.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SkillBuilderPage.tsx frontend/src/components/skills/SkillBuilderForm.tsx frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: add skill builder page"
```

### Task 5: Polish styles and responsive behavior

**Files:**
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing test**

Add one layout-focused test that confirms the Skills store and builder expose the expected container roles/labels for responsive sections.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run`

Expected: FAIL until the new layout hooks exist.

- [ ] **Step 3: Write minimal implementation**

Refine the Skills UI with:
- denser card grids
- clean tab/filter bars
- clearer selected-state treatment
- consistent editor spacing
- mobile-safe stacking for the store and builder

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run && npm run build`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/styles.css frontend/src/App.test.tsx
git commit -m "feat: polish skills store layout"
```

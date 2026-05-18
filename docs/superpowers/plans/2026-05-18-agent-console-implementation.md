# Agent Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first frontend Agent Console screen for DromX.

**Architecture:** Keep the first implementation static and frontend-only. Add a lightweight screen state inside `App.tsx` so the landing page CTA can navigate to the console without introducing a router dependency yet. Add reusable data structures for role Agents, workflow steps, execution events, and output preview.

**Tech Stack:** React, Vite, TypeScript, plain CSS, Vitest, Testing Library, lucide-react

---

## File Structure

- Modify: `frontend/src/App.tsx`
  - Add `screen` state: `landing | console`
  - Keep existing i18n data and add console content to the same content object
  - Render Landing or Agent Console based on state
- Modify: `frontend/src/App.test.tsx`
  - Add tests for navigating from landing to console
  - Assert key console sections exist
- Modify: `frontend/src/styles.css`
  - Add dense app-console layout styles
  - Preserve landing styles

## Task 1: Add Console Navigation State

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing test**

Test that clicking the landing primary CTA reveals the Agent Console.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test`

Expected: FAIL because the CTA is currently just an anchor and no console screen exists.

- [ ] **Step 3: Write minimal implementation**

Add local screen state and convert the primary CTA to set the console screen.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test`

Expected: PASS

## Task 2: Build Static Agent Console Content

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing test**

Assert these console sections:
- Active Swarm
- Role Agents
- Workflow Decomposition
- Execution Feed
- Output Preview

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test`

Expected: FAIL until console content exists.

- [ ] **Step 3: Write minimal implementation**

Add mock role Agents, workflow steps, events, and output preview for both English and Chinese.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test`

Expected: PASS

## Task 3: Style Console Layout

**Files:**
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Add layout hooks through existing console markup**

Use class names for shell, sidebar, topbar, content grid, panels, roster, timeline, feed, and output preview.

- [ ] **Step 2: Implement responsive CSS**

Make desktop dense and mobile stacked. Avoid nested decorative cards.

- [ ] **Step 3: Verify**

Run: `cd frontend && npm test && npm run build`

Expected: PASS


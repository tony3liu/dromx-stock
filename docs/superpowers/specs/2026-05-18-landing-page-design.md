# Landing Page Design Spec

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this spec task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a premium landing page that explains DromX as a digital labor network for the real world, showing how real-world human capability becomes digitized, structured, agentized, and able to collaborate as a swarm toward infinite productivity.

**Architecture:** The landing page is a single React surface inside `frontend/` that behaves like a product introduction page, not a marketing brochure. It should lead with a strong business promise, show proof through real operational outcomes, explain how the system works in three layers, and end with trust signals plus a clear path into the console. The page should stay visually restrained and editorial, using one coherent layout system and reusable sections rather than decorative one-off elements.

**Tech Stack:** React, Vite, TypeScript, plain CSS, Vitest, Testing Library, lucide-react

---

### Task 1: Rebuild the landing page information architecture

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing test**

Add assertions for the page-level structure: vision headline, capability transformation section, outcome section, evolution-path section, trust section, and the primary CTA.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test`

Expected: FAIL because the current page does not yet expose the final section structure and headings.

- [ ] **Step 3: Write minimal implementation**

Update the React component to render the new landing page sections:
- hero with strong vision headline and supporting copy
- business outcome strip for the digital labor network
- role digitization and evolution explanation
- three-layer platform explanation
- trust and safety signals
- final conversion CTA

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: refine landing page structure"
```

### Task 2: Rework the visual style into a premium editorial system

**Files:**
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write the failing test**

Add a lightweight DOM-based test or screenshot-checkable expectation for the presence of the key layout containers and spacing-friendly structure, so the style changes are driven by the section layout above.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test`

Expected: FAIL if the layout hooks or container structure are still not aligned with the new spec.

- [ ] **Step 3: Write minimal implementation**

Restyle the landing page with:
- dark neutral base
- restrained accent color
- editorial typography hierarchy
- precise spacing and compact but breathable cards
- no heavy gradients, blobs, or generic dashboard chrome

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test && npm run build`

Expected: PASS for tests and build

- [ ] **Step 5: Commit**

```bash
git add frontend/src/styles.css
git commit -m "feat: polish landing page visual system"
```

### Task 3: Keep the onboarding path aligned with the product loop

**Files:**
- Modify: `README.md`
- Modify: `docs/ui-business-logic-reference.md` if needed

- [ ] **Step 1: Write the failing test**

No code test is required here. Validate the plan by checking that the repo-level docs and onboarding instructions point to `frontend/` and `backend/` clearly.

- [ ] **Step 2: Run test to verify it fails**

Not applicable.

- [ ] **Step 3: Write minimal implementation**

Update the README so the landing page work is discoverable and the module boundaries stay clear.

- [ ] **Step 4: Run test to verify it passes**

Run: `cat README.md`

Expected: The frontend and backend paths are clear and the landing page scope is readable from the repo root.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/ui-business-logic-reference.md
git commit -m "docs: clarify landing page workspace flow"
```

# Documentation & Skills Review Plan

Status: **in progress** - this file is the live checklist. Check items off and
record findings inline as each step is executed. Do not delete prior findings;
superseded items should be struck through with a note.

Related files:
- [PROMPTS.md](PROMPTS.md) - prompts/instructions that drove this review, kept for reuse
- [CHANGELOG.md](CHANGELOG.md) - record of every change made as a result of this review

---

## 0. Inventory (Step 1 - completed 2026-07-16; updated 2026-07-17, see note below table)

### Skills - `.agents/skills/*/SKILL.md`

| Skill | Category | Purpose |
|---|---|---|
| brainstorming | Planning & Process | Explore intent/requirements before creative work |
| writing-plans | Planning & Process | Turn a spec into a written implementation plan |
| executing-plans | Planning & Process | Execute a written plan in a separate session w/ checkpoints |
| subagent-driven-development | Planning & Process | Execute plan tasks via parallel subagents in-session |
| using-git-worktrees | Planning & Process | Isolate feature work via git worktrees |
| verification-loop | Planning & Process | Comprehensive verification system for sessions |
| systematic-debugging | Planning & Process | Structured approach before proposing bug fixes |
| improve | Planning & Process | Read-only codebase audit → handoff plans for other agents |
| ~~api-design~~ | ~~Backend/API Engineering~~ | ~~REST API design: naming, status codes, pagination, errors, versioning, rate limiting~~ - **removed 2026-07-17**, see FIND-3 |
| ~~backend-patterns~~ | ~~Backend/API Engineering~~ | ~~Backend architecture for **Node.js/Express/Next.js API routes**~~ - **removed 2026-07-17**, see FIND-4 |
| fastapi-patterns | Backend/API Engineering | FastAPI + Pydantic v2 + DI + async patterns (Python) |
| ~~frontend-patterns~~ | ~~Frontend Engineering~~ | ~~React/**Next.js** patterns, state mgmt, performance~~ - **removed 2026-07-17**, see FIND-4 |
| frontend-design-direction | Frontend Engineering | ECC-specific product design judgment for UI work |
| coding-standards | Cross-cutting Quality | Baseline naming/readability/immutability conventions |
| security-review | Cross-cutting Quality | Security checklist for auth, input, secrets, payments |
| tdd-workflow | Cross-cutting Quality | TDD workflow, 80%+ coverage (unit/integration/E2E) |
| seo | Domain-specific | Technical/on-page SEO, structured data, Core Web Vitals |
| browser-testing-with-devtools | Tooling | Real-browser testing via Chrome DevTools MCP |
| caveman | Meta/Communication | Ultra-compressed output style |

**16 skills remain** (down from the original 18) - `api-design`,
`backend-patterns`, and `frontend-patterns` were deleted from
`.agents/skills/` on 2026-07-17. See FIND-3/FIND-4 below (originally fixed
by annotation in `Agents.md`; now superseded by physical removal) and
`review/CHANGELOG.md` for the full record.

### Documentation - `docs/*.md`

| Doc | Category | Purpose |
|---|---|---|
| specs.md | Product/Requirements | UI functional spec for "AISeo Expert" |
| architecture.md | Architecture | System architecture (hexagonal, workflow, storage) |
| agent-architecture.md | Architecture | Agent categories, responsibilities, orchestration |
| frontend-architecture.md | Architecture | React/FastAPI integration, pages, state, live updates |
| system-design.md | Architecture | Bootstrap design rules, layout, accessibility, LLM prompt template |
| api-contracts.md | Engineering Reference | HTTP endpoints (workflows, SSE streaming) |
| project-structure.md | Engineering Reference | Recommended repo layout |
| implementation.md | Engineering Reference | Phased delivery roadmap |
| deployment.md | Engineering Reference | Docker config + Alibaba Cloud deployment target (added 2026-07-16) |

### Top-level entrypoints

| File | Role |
|---|---|
| `Agents.md` | Agent operating instructions; docs table and skills table, both now reconciled with the filesystem (FIND-1/FIND-6 fixed) |
| `README.md` | Human-facing overview; docs table now matches `Agents.md`/`docs/` (FIND-2 resolved) |

---

## 1. Review Checklist

Each pass below is a distinct step. Record ✅ (clean), ⚠️ (finding logged), or
➖ (not applicable) per item, with a one-line pointer into §2 Findings.

### Step 2 - Cross-reference entrypoints against real files
- [x] `Agents.md` skills table → each linked path exists in `.agents/skills/` - ⚠️ FIND-1
- [x] `Agents.md` docs table → each linked path exists in `docs/` - ✅
- [x] `README.md` docs list → each linked path exists in `docs/` - ⚠️ FIND-2
- [x] `Agents.md` and `README.md` describe the same doc set consistently - ⚠️ FIND-2

### Step 3 - Duplication scan (skills vs skills, skills vs docs)
- [x] Overlapping skill pairs covering the same concern - ⚠️ FIND-3
- [x] Skill content duplicated inside a doc (or vice versa) - ✅ none found
- [x] Near-duplicate planning skills (brainstorming/writing-plans/executing-plans/subagent-driven-development/improve) checked for redundant vs complementary scope - ✅ complementary, sequential stages (see FIND-3 note)
- [x] Within-file duplication in a single entrypoint (added 2026-07-16, user-requested spot check of `Agents.md`) - ⚠️ FIND-6

### Step 4 - Conflict scan (contradicting guidance)
- [x] Skill tech stack vs project tech stack (`Agents.md` "Technology Stack", `README.md` "Recommended Stack") - ⚠️ FIND-4
- [x] Doc-to-doc contradictions (architecture.md vs system-design.md vs frontend-architecture.md) - ✅ none found, layers are complementary
- [x] Skill-to-doc contradictions (e.g. security, accessibility guidance) - ✅ none found beyond stack mismatch (FIND-4)

### Step 5 - Gap scan (referenced but missing, or needed but absent)
- [x] Skills referenced in `Agents.md` with no corresponding file - ⚠️ FIND-1 (same as Step 2)
- [x] Docs referenced in `README.md` with no corresponding file - ⚠️ FIND-2 (same as Step 2)
- [x] Agent roles in `docs/agent-architecture.md` with no supporting skill - ⚠️ FIND-5
- [x] Testing coverage: `tdd-workflow` exists but no project-level test doc - ➖ acceptable, skill is self-contained

### Step 6 - Report
- [x] Findings categorized and written to §2 below
- [x] Findings triaged with user (fix now vs. defer) - FIND-1, FIND-3, FIND-4 fixed, FIND-2 found already resolved (all 2026-07-16); FIND-5 still pending
- [x] Any agreed fixes applied and logged in `CHANGELOG.md` - FIND-1, FIND-2, FIND-3, FIND-4 logged

---

## 2. Findings

### FIND-1 - Gap + Inconsistency: `Agents.md` skills table references non-existent skills - ✅ FIXED 2026-07-16
`Agents.md` §"Agent Skills" links five skills that do not exist under `.agents/skills/`:
`security`, `accessibility`, `testing`, `github-workflow`, `design-and-planning`.
Conversely, 14 of the 18 skills that *do* exist (`api-design`, `brainstorming`,
`browser-testing-with-devtools`, `caveman`, `executing-plans`, `fastapi-patterns`,
`frontend-design-direction`, `improve`, `security-review`, `seo`,
`subagent-driven-development`, `systematic-debugging`, `tdd-workflow`,
`using-git-worktrees`, `verification-loop`, `writing-plans`) are absent from the table,
so an agent following `Agents.md` literally would never discover them.
The closest existing match for "Security" is `security-review`, not `security`.
- **Category:** gap, inconsistency
- **Files:** `Agents.md` (skills table), `.agents/skills/*`
- **Fix applied:** replaced the skills table in `Agents.md` with all 18 real
  skills, grouped by category, each linking to its actual path. Dropped the
  5 phantom entries (`security`, `accessibility`, `testing`, `github-workflow`,
  `design-and-planning`); `security` → `security-review` (real skill, kept).
  `accessibility` and `github-workflow` have no real equivalent - flagged as an
  explicit open gap in the new table (still tracked as FIND-5). Also annotated
  the `backend-patterns` and `frontend-patterns` rows with the stack mismatch
  from FIND-4, since restoring these rows without a note would silently
  re-endorse conflicting guidance.

### FIND-2 - Inconsistency + Gap: `README.md` doc links don't match `docs/` - ✅ RESOLVED (found already fixed 2026-07-16)
`README.md` lists docs as `ARCHITECTURE.md`, `AGENT_ARCHITECTURE.md`,
`FRONTEND_ARCHITECTURE.md`, `DESIGN_SYSTEM.md`, `CODING_STANDARDS.md`,
`IMPLEMENTATION_PLAN.md`, `API_CONTRACTS.md`, `PROJECT_STRUCTURE.md`
(UPPER_SNAKE_CASE). Actual files in `docs/` are lowercase-hyphenated:
`architecture.md`, `agent-architecture.md`, `frontend-architecture.md`,
`api-contracts.md`, `project-structure.md`, `implementation.md`, `system-design.md`.
Two README entries have no file at all under any casing:
`DESIGN_SYSTEM.md` (closest actual doc is `system-design.md`, different scope/name)
and `CODING_STANDARDS.md` (no `docs/` file exists; only `.agents/skills/coding-standards/SKILL.md`).
`Agents.md`'s own doc table (lowercase, 8 entries incl. `docs/specs.md` and
`docs/system-design.md`) does not match README's list either - the two
entrypoints disagree on both filenames and doc set.
- **Category:** inconsistency, gap
- **Files:** `README.md`, `Agents.md`, `docs/*`
- **Resolution note:** when work started on this fix, `README.md` was found
  to already match `Agents.md`'s doc table exactly (verified: all 8 rows
  identical, every path exists under `docs/`). This edit was **not** made by
  the review process - it happened outside this session (most likely a
  direct IDE edit) between the original inventory pass and this fix pass.
  No further change was needed.

### FIND-3 - Duplication risk: overlapping API-design guidance - ✅ FIXED 2026-07-16
`api-design/SKILL.md` and `fastapi-patterns/SKILL.md` both cover request/response
schema design, error responses, and endpoint conventions, but from different
angles (framework-agnostic REST rules vs FastAPI-specific implementation).
`api-design/SKILL.md`'s own "Implementation Patterns" section includes
TypeScript/Next.js and Django REST Framework examples - not FastAPI, the
project's actual backend framework - while `fastapi-patterns/SKILL.md` covers
that ground already. This isn't pure duplication but creates a "which one wins"
ambiguity that `Agents.md` doesn't resolve (its skill table doesn't list either
of these two under their real names).
The planning-skill family (`brainstorming` → `writing-plans` → `executing-plans`/
`subagent-driven-development` → `improve`) was checked and found complementary
(sequential lifecycle stages, not overlapping scope) - no action needed there.
- **Category:** duplication (partial), ambiguity
- **Files:** `.agents/skills/api-design/SKILL.md`, `.agents/skills/fastapi-patterns/SKILL.md`
- **Fix applied:** left both shared/vendored skill files (`origin: ECC`)
  untouched - mutating a general-purpose skill pack to fit one project's
  stack would reduce its reusability elsewhere. Instead resolved the
  ambiguity at the project-integration layer, in `Agents.md`: the API Design
  row now says to apply its *conventions*, not its TypeScript/Next.js/Django
  *examples*, and a new paragraph after the skills table states the
  precedence - API Design (protocol rules) + FastAPI Patterns (Python
  implementation) apply together for API work, and FastAPI Patterns wins
  where the two disagree. Same pattern used for FIND-1/FIND-4.
- **Superseded 2026-07-17:** user deleted `.agents/skills/api-design/`
  entirely rather than keep the annotate-in-place fix above. The
  precedence paragraph in `Agents.md` was rewritten accordingly - see
  `review/CHANGELOG.md`.

### FIND-4 - Conflict: `backend-patterns` / `frontend-patterns` target the wrong stack - ✅ FIXED 2026-07-16
Project stack per `Agents.md` and `README.md` is **FastAPI + Python** (backend)
and **React + TypeScript + Bootstrap 5** (frontend) - no Next.js or Express
anywhere in the project. But:
- `backend-patterns/SKILL.md` description: *"for Node.js, Express, and Next.js API routes"*
- `frontend-patterns/SKILL.md` description and body: React/**Next.js** patterns,
  with code samples assuming a Next.js app (not Bootstrap 5, which this project
  uses per `docs/system-design.md`)
An agent loading these two skills "as-is" would introduce Node/Next.js-flavored
guidance into a FastAPI/Bootstrap project, contradicting `docs/frontend-architecture.md`
(§1 Stack: React + Bootstrap 5, no Next.js) and `docs/system-design.md` (§2
Technology Rules: Bootstrap 5 + Bootstrap Icons).
- **Category:** conflict
- **Files:** `.agents/skills/backend-patterns/SKILL.md`, `.agents/skills/frontend-patterns/SKILL.md`, `docs/frontend-architecture.md`, `docs/system-design.md`
- **Fix applied:** user confirmed the frontend is plain React.js (no Next.js
  anywhere in the stack), which sharpened this from "possible mismatch" to
  confirmed. Chose "scope out" over "edit in place" (same reasoning as
  FIND-3: these are shared/vendored `origin: ECC` skills, not worth forking
  for one project). In `Agents.md`: both rows now explicitly say **do not
  load for this project**, with a pointer to the correct alternative
  (FastAPI Patterns for backend; Frontend Design Direction +
  `docs/system-design.md`/`docs/frontend-architecture.md` for frontend), and
  a new paragraph after the skills table states the exclusion and reasoning
  in full. Skill files themselves left unmodified.
- **Superseded 2026-07-17:** user deleted both
  `.agents/skills/backend-patterns/` and `.agents/skills/frontend-patterns/`
  entirely rather than keep the scope-out-in-place fix above. `Agents.md`'s
  exclusion paragraph was rewritten to describe the removal instead of an
  exclusion - see `review/CHANGELOG.md`. See also FIND-7: this removal left
  dangling cross-references inside two other, still-present vendored
  skills.

### FIND-5 - Gap: agent roles without a corresponding skill
`docs/agent-architecture.md` §1 lists worker agents including **Accessibility
Agent** and **Performance Agent**. `docs/specs.md` has a dedicated
"Accessibility" requirements section. There is no `accessibility` skill (only
referenced-but-missing in FIND-1) and no performance-specific skill - the
closest was generic `coding-standards` / ~~`frontend-patterns`~~ (the latter
removed 2026-07-17, see FIND-4's superseded note - no longer even a nominal
fallback). Not necessarily wrong (skills are optional guidance, not
mandatory per-agent files), but worth a decision: either add these skills
or accept the gap explicitly.
- **Category:** gap
- **Files:** `docs/agent-architecture.md`, `docs/specs.md`, `.agents/skills/`

### FIND-6 - Duplication: structural/semantic repetition within `Agents.md` itself - ✅ FIXED 2026-07-16
A same-file duplication pass (triggered by a direct user request, not part of
the original Step 3 skills/docs scan) found no byte-identical duplicate lines,
but several requirements were restated in different words across non-adjacent
sections:
- Two H1 titles back-to-back (`# AGENTS.md` then `# AISeo Expert`).
- `# Implementation Expectations` and `# Implementation Requirements` were
  two separate top-level sections ~30 lines apart, with unrelated `# Security
  & Quality` / `# Documentation` sections wedged between them, both governing
  the same concern (how implementation work should be carried out).
- `# Project Documentation` (docs table) and `# Documentation` (one-line
  "keep docs updated" reminder) were two separate top-level sections about
  the same topic.
- The "production-ready" bar was asserted independently in three places
  (General Principles, the old Implementation Requirements intro, Production
  Standards).
- Validation, error-handling, and testing requirements were each restated in
  2–3 different sections (Security & Quality vs Production Standards vs
  Feature Completion) with no cross-reference.
- **Category:** duplication
- **Files:** `Agents.md`
- **Fix applied:** consolidated in place (no content lost, only merged/moved/
  cross-referenced):
  - Dropped the redundant `# AGENTS.md` title, keeping `# AISeo Expert` as
    the sole top-level title.
  - Merged the one-line `# Documentation` reminder into the end of `#
    Project Documentation` (same topic, now one section).
  - Merged `# Implementation Expectations` into `# Implementation
    Requirements` as its new opening subsection, `## Before Implementation`;
    the standalone `# Implementation Expectations` heading is gone.
  - Moved `# Security & Quality` to sit immediately before the (now merged)
    `# Implementation Requirements`, and made it the single canonical home
    for validation/error-handling/testing requirements.
  - Trimmed `## Production Standards` from 8 bullets to 4 (`Type safety`,
    `Responsive UI`, `Loading and error states`, `Meaningful user feedback`),
    removing the ones that duplicated Security & Quality (`Proper
    validation`, `Robust error handling`, `Security considerations`, `Tests
    required by the project standards`), and added a one-line pointer back
    to Security & Quality instead.
  - `Feature Completion`'s "Required tests pass" kept as-is (distinct nuance
    - tests passing, not just existing).

### FIND-7 - Gap: dangling cross-references to the three deleted skills
This is the same issue flagged as an incidental item in §3 Next Steps
(2026-07-16, "the `security-review`/`coding-standards` Next.js mentions
found during the Django/Next.js sweep"), formalized now that the referenced
skills no longer exist at all - these are no longer just off-stack mentions,
they're broken links.
- `.agents/skills/coding-standards/SKILL.md` (lines 14–15): "Use
  `frontend-patterns` for React..." and "Use `backend-patterns` or
  `api-design` for repository/service layers..." - all three named skills
  are gone.
- `.agents/skills/seo/SKILL.md` (line 153): references `frontend-patterns`.
- **Category:** gap (broken reference)
- **Files:** `.agents/skills/coding-standards/SKILL.md`,
  `.agents/skills/seo/SKILL.md`
- **Status:** partially open. The two vendored (`origin: ECC`) files still
  point at deleted sibling skills - same reasoning as FIND-3/FIND-4 applies
  against forking them just for this project. Awaiting a decision on whether
  to patch their dangling mentions anyway (they're now factually wrong, not
  just off-stack) or accept the gap and note it inline in `Agents.md`
  instead.

---

## 3. Next Steps (not yet executed - awaiting direction)

1. Decide, per finding, whether to fix, defer, or accept as-is.
2. ~~If fixing FIND-1~~ - done 2026-07-16, see FIND-1 and `CHANGELOG.md`.
3. ~~If fixing FIND-2~~ - found already resolved 2026-07-16 (edited outside
   this session before this fix pass); see FIND-2 note and `CHANGELOG.md`.
4. ~~If fixing FIND-3~~ - done 2026-07-16 via an `Agents.md` precedence note;
   see FIND-3 and `CHANGELOG.md`.
5. ~~If fixing FIND-4~~ - done 2026-07-16: `backend-patterns`/`frontend-patterns`
   marked "do not load for this project" in `Agents.md`, with alternatives
   pointed to; see FIND-4 and `CHANGELOG.md`.
6. ~~If fixing FIND-6~~ - done 2026-07-16: consolidated the duplicate/redundant
   sections in `Agents.md` in place; see FIND-6 and `CHANGELOG.md`.
7. FIND-5 (accessibility/GitHub-workflow gap) remains open - decide whether to
   add dedicated skills or accept the gap explicitly.
8. ~~Consider logging the `security-review`/`coding-standards` Next.js
   mentions... as a new minor finding~~ - done 2026-07-17 as FIND-7, sharpened
   from "off-stack mention" to "broken reference" once `api-design`/
   `backend-patterns`/`frontend-patterns` were deleted. Still open - decide
   whether to patch the two vendored skills' dangling mentions or accept the
   gap.
9. Consider a same-file duplication pass on the other entrypoint (`README.md`)
   and on `docs/*` for the same kind of restated-in-multiple-places content
   found in FIND-6 - not yet done, only `Agents.md` was checked.
10. ~~2026-07-17: user deleted `api-design`, `backend-patterns`, and
    `frontend-patterns` from `.agents/skills/`~~ - done; see FIND-3/FIND-4
    superseded notes, FIND-7, and `CHANGELOG.md`.
11. Any further change must be logged in `CHANGELOG.md`.

# Review Prompts Log

Prompts that drove the documentation/skills review, kept verbatim so the
process can be re-run later (e.g. after edits, or periodically as skills/docs
are added).

---

## 2026-07-16 - Initial review kickoff

> List all skills and documentation, categorizing them by their names and
> purpose. Then create a multi-step review plan with a checklist to identify
> inconsistencies, duplication, conflicts, and gaps. Save this plan and use it
> as the review checklist for all subsequent steps. Save the prompts for
> future reference. Also keep records of the changes made in a separate file.

**Produced:**
- [REVIEW_PLAN.md](REVIEW_PLAN.md) - inventory, checklist, findings
- This file (`PROMPTS.md`)
- [CHANGELOG.md](CHANGELOG.md)

---

## 2026-07-16 - Fix FIND-1

> Fix find 1

**Result:** Rewrote the skills table in `Agents.md` - all 18 real skills,
grouped by category, correct paths; dropped 5 phantom entries; annotated the
stack mismatch later formalized as FIND-4. Logged in `CHANGELOG.md`.

---

## 2026-07-16 - Fix FIND-2

> Fix find 2

**Result:** Found `README.md` already matched `Agents.md`/`docs/` exactly -
edited outside this session, not by this process. Verified by diff and marked
resolved in `REVIEW_PLAN.md`/`CHANGELOG.md` without further changes.

---

## 2026-07-16 - Suggest a fix for FIND-3

> What fix do you suggest for find 3

**Result:** Recommended annotating `Agents.md` with a precedence note
(api-design = conventions, fastapi-patterns = implementation) rather than
editing the shared/vendored skill files directly. Presented as a choice via
`AskUserQuestion`; user picked "FIND-3 as proposed."

---

## 2026-07-16 - Stack clarification

> This project uses react.js in frontend

**Result:** Confirmed this matches existing docs (no Next.js anywhere);
reinforced the FIND-4 stack-mismatch finding for `frontend-patterns`. No file
changes - informational, used to sharpen FIND-4 for later.

---

## 2026-07-16 - Fix FIND-3 (confirmed)

> (selection: "FIND-3 as proposed (Recommended)" from AskUserQuestion)

**Result:** Added a precedence note to `Agents.md` after the skills table
(API Design + FastAPI Patterns apply together; FastAPI Patterns wins on
conflict) and reworded the API Design row's "Apply when" column. Left
`api-design/SKILL.md` and `fastapi-patterns/SKILL.md` unmodified. Logged in
`REVIEW_PLAN.md`/`CHANGELOG.md`.

---

## 2026-07-16 - Django/Next.js mention sweep

> which skills mention django nextjs

**Result:** `grep`-based lookup (not a file change) across
`.agents/skills/*/SKILL.md`. Found 5 matches: `backend-patterns`,
`frontend-patterns`, `api-design` (all already covered by FIND-3/FIND-4), plus
two not yet flagged - `security-review` (one reference link to Next.js
Security docs) and `coding-standards` (one Next.js App Router folder-tree
example). Flagged to user as candidates for a new minor finding or fold-in;
no decision made yet.

---

## 2026-07-16 - Docker/Alibaba Cloud deployment doc

> Update the specs to include docker configuration which is compatible with
> alibabacloud deployment

**Result:** `docs/specs.md` is UI-only in scope; asked via `AskUserQuestion`
where the content should live rather than bolting infra content onto a UI
spec. User chose a new dedicated doc. Produced `docs/deployment.md` (Docker
multi-stage build, docker-compose, Alibaba Cloud target: ACR/ACK/ApsaraDB
RDS/OSS/SLB/KMS, env vars, CI/CD outline) and added matching rows to the docs
tables in `Agents.md` and `README.md`. Logged in `CHANGELOG.md`.

---

## 2026-07-16 - Check Agents.md for duplicates

> Check Agents.md for any duplicate contents

**Result:** No exact duplicate lines, but found structural/semantic
duplication: a redundant title, two overlapping "Implementation" sections
split apart by unrelated content, two separate doc-reminder sections, and
validation/error-handling/testing requirements each restated 2–3 times.
Reported as candidate FIND-6; user confirmed with "yes" (next prompt).

---

## 2026-07-16 - Confirm FIND-6 fix

> yes

**Result:** Consolidated `Agents.md` in place (title, doc sections, and
Implementation sections merged; Production Standards de-duplicated against
Security & Quality). Logged as FIND-6 (fixed) in `REVIEW_PLAN.md` and
`CHANGELOG.md`.

---

## 2026-07-16 - Full application build (10 phases)

> Implement the code in accordance with the project documentation and skill
> guardrails.

Clarified scope via `AskUserQuestion` (Phase 1 Foundation vs skeleton vs a
named feature) → user picked Phase 1. Then:

> Prepare a multi-step implementation plan, then build a fully functional
> application in accordance with the documented architecture, specifications,
> and skill guardrails. Save the plan and implement it step by step

This expanded scope beyond the earlier Phase-1-only answer, so re-clarified
via `AskUserQuestion` (Phase 1 only vs Phases 1–3 vs all 10) → user picked
**all 10 phases**. Entered plan mode, wrote the full phase-by-phase plan to
`~/.claude/plans/kind-sauteeing-papert.md`, got approval via `ExitPlanMode`,
then executed all 10 phases from `docs/implementation.md` sequentially, each
with real verification (pytest, real Postgres, real `uvicorn`/`curl`, real
Docker build) rather than one unverified dump. Mid-build, the user sent
`/compact` (a harness-level context-management command, not something
requiring action from me) - acknowledged and continued.

**Result:** Full-stack application - FastAPI backend (11 agents across
manager/worker/reviewer/fix roles, 9 hexagonal ports each with a real
adapter, Alembic migrations 0001–0006, auth, rate limiting, request tracing,
artifact storage), React+TypeScript+Bootstrap frontend, real Docker build.
146 passing tests. Every phase logged in detail in `review/CHANGELOG.md`,
including 4 real bugs found via failing tests (and one via directly
verifying a library) and fixed, not patched around. See `CHANGELOG.md`'s
per-phase entries for what's real vs what still needs the user's own
credentials (Qwen Cloud, GitHub, Alibaba OSS) to exercise end-to-end.

---

## Reuse template

To re-run this review later (e.g. after new skills/docs are added, or after
fixing findings), reuse this prompt:

> Re-run the review checklist in `review/REVIEW_PLAN.md` against the current
> state of `.agents/skills/` and `docs/`. Update the inventory tables, re-check
> every checklist item, and append any new findings (or mark resolved ones as
> closed with the date). Log any file changes in `review/CHANGELOG.md`.

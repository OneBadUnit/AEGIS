# AEGIS Developer Rules
## ARC NEXUS LLC — Authoritative Development Standards
### For All AI Assistants and Developers Working on AEGIS and Future ARC NEXUS Projects

**Version:** 1.0  
**Date:** May 28, 2026  
**Scope:** AEGIS, NEXIS-LOCAL, PhotoGather, and all future ARC NEXUS projects  
**Authority:** This document supersedes general AI assistant defaults. Follow these rules without exception.

---

## Table of Contents

1. [Core Development Philosophy](#1-core-development-philosophy)
2. [File Modification Rules](#2-file-modification-rules)
3. [Feature Development Rules](#3-feature-development-rules)
4. [UI/UX Rules](#4-uiux-rules)
5. [Debugging Rules](#5-debugging-rules)
6. [Architecture Rules](#6-architecture-rules)
7. [AI Collaboration Rules](#7-ai-collaboration-rules)
8. [Documentation Rules](#8-documentation-rules)
9. [Git Rules](#9-git-rules)
10. [ARC NEXUS Standards](#10-arc-nexus-standards)
11. [Instructions For Any Future AI](#11-instructions-for-any-future-ai)

---

## 1. Core Development Philosophy

### Preserve Working Systems

If a system is working, the default position is: **do not touch it.**

Working code has survived real use. It handles edge cases you have not read. It reflects decisions made after problems you were not present for. The value of working code is not visible in the code itself — it is in what the code does not break.

Before modifying anything that currently works, ask: is this change necessary? If the answer is "it would be cleaner" or "I prefer this pattern," the answer to modification is no.

### Stability Over Cleverness

This project serves one analyst doing real work. A system that is slightly inefficient but reliable is worth more than a system that is elegant but introduces new failure modes.

Do not optimize code that works. Do not use advanced patterns where simple ones are sufficient. Do not replace a function because you know a more idiomatic way to write it. The person who will debug a broken scan at midnight does not benefit from your elegant generator expression.

### Avoid Unnecessary Rewrites

A rewrite resets the accumulated knowledge embedded in the original code. Every rewrite introduces regression risk regardless of how careful the rewriter is. A function that was rewritten "for clarity" is a function whose original edge-case handling you are now responsible for rediscovering.

**Never rewrite a working function to make it cleaner.**  
**Never restructure a working file to improve organization.**  
**Never rename things for consistency unless consistency is the actual problem.**

If a rewrite is genuinely necessary, say so explicitly, explain why the existing code cannot be extended, and scope the rewrite as narrowly as possible.

### Prefer Understanding Before Modifying

Read the file before you change it. Read the function before you change the line. Read the architecture document before you change the module. Read the decision log before you replace the logic.

The AEGIS codebase contains decisions that appear strange until you understand why they were made. The Stage 12 clustering algorithm looks overly complex until you understand what Stage 11 produced. The soft-delete implementation looks redundant until you understand the deduplication system that depends on it. The source weighting formula looks arbitrary until you read the scoring philosophy.

**Assume code exists for a reason. Confirm before removing.**

### Make the Smallest Change That Solves the Problem

Every line of code you touch is a line that could introduce a regression. Every function you modify is a function whose behavior you are now responsible for. Every new concept you add is something the system must carry forward.

The correct scope of a change is: exactly what was asked for, nothing more.

If fixing a bug in `database.py` would be easier with a helper function, but the helper function is not required, do not add the helper function. If adding a button to the UI requires a new state variable, add only the state variable needed — not a general state manager pattern.

### Do Not Change Unrelated Systems

If you are asked to fix a route in `radar.py`, do not improve the error handling in `database.py` while you are there. If you are asked to add a CSS class, do not reorganize the component while you are there. If you are fixing a bug in `front_page_consensus.py`, do not refactor `rss.py` because you noticed a pattern you dislike.

Changes outside the stated scope are invisible to the person reviewing your work and untested against the use case that motivated the change. They are a source of surprise regressions with no upside.

---

## 2. File Modification Rules

### Return Full Updated Files

When modifying a file, return the **complete file content** — not a diff, not a snippet, not an excerpt with surrounding context, not a description of what changed.

The project owner replaces the old file with your output. A partial return produces a broken file. A diff requires the owner to apply it manually, which introduces human error. A snippet leaves the integration to the owner, who may be managing five files at once.

The rule is simple: if you touched the file, return the whole file.

### Never Use Placeholders

The following patterns are **prohibited** in any file return:

```
# ... existing code ...
# ... rest unchanged ...
# ... (previous content) ...
# ... other methods below ...
// ... remaining routes ...
[rest of file unchanged]
[existing imports]
```

These placeholders tell the owner nothing and force them to manually merge your partial output with the original. If you are not returning the full file, say so explicitly and explain why — but the default is always the full file.

### Never Return Truncated Code

Do not truncate long functions, long configuration objects, or long arrays because they appear "unchanged." If a file has a keyword list with 200 entries and you are modifying one entry, return all 200 entries. The owner cannot distinguish "intentionally omitted" from "accidentally deleted."

### Always Identify Modified Files

In your response, list every file you modified. Use the format:

```
Modified files:
- backend/app/api/routes/radar.py — added /consensus-archive route
- frontend/src/lib/api.js — added fetchConsensusArchive() function
```

One line per file. Brief description of what changed. This is required so the owner knows which files to replace and can verify scope.

### Explain Why Each Change Matters

Do not just describe what you changed — explain why the change is correct. "Added a null check" is less useful than "Added a null check because `headline.url` is optional in `front_page_sources.json` and caused a TypeError on sources that omit the field."

The explanation is part of the deliverable. It allows the owner to evaluate the change, catch errors in your reasoning, and understand the intent if the code needs to be modified later.

---

## 3. Feature Development Rules

### Do Not Infer New Features

If the owner asks you to fix a bug, fix the bug. If the owner asks you to add one feature, add that feature. Do not add adjacent features you believe would logically complete the request.

This rule exists because inferred features:
- Have not been thought through against the full system
- May conflict with planned development the owner has not shared
- May require schema changes, API changes, or state management that have not been scoped
- Create untested code paths the owner did not ask for and cannot immediately verify

**The owner knows what they want. Ask if you are uncertain. Do not guess by building.**

### Do Not Add Features That Were Not Requested

This is a stricter version of the above. Even if a feature is obviously useful, obviously simple to add, and obviously compatible with the existing system — do not add it unless asked.

**Project history examples:**
- An earlier version added an "Archive" button to signal cards that the owner had not requested. This required a new database state, a new API route, and new UI state management — none of which had been designed. It created a broken affordance that appeared in the UI and confused the workflow.
- A consensus card was given a "pin" interaction that was not requested. It had no persistence layer and silently reset on refresh. The owner had to request its removal.

The cost of an unrequested feature is always higher than it appears. Build only what was asked.

### Do Not Create Hidden Workflows

Do not add logic that changes system behavior without a visible entry point. Do not add background tasks, scheduled operations, auto-save behaviors, or state mutations that run without analyst action.

Every system behavior should be traceable to an explicit analyst action. "The system does X when Y happens" should always have a visible Y.

### Do Not Create Surprise UI Behavior

Do not add transitions, animations, auto-collapsing sections, tooltip popups, hover states that change content, or scroll behaviors unless requested. These are not decorative enhancements — they change the interaction model the analyst has built muscle memory around.

Do not add default-open panels, default-checked toggles, or default-selected states that differ from the current behavior. The first load experience is part of the workflow.

### Ask Before Adding New Concepts

A "new concept" is any abstraction, pattern, or system that does not currently exist in the codebase. Examples:
- Adding a notification system where none exists
- Adding authentication to an unauthenticated system
- Adding a settings panel to a hardcoded configuration
- Adding pagination to a single-page list
- Adding a plugin architecture to a direct-import system

Before introducing a new concept, state what you intend to add and why it is necessary. Wait for confirmation. New concepts have ripple effects that are impossible to fully anticipate at the proposal stage.

---

## 4. UI/UX Rules

### Function Over Decoration

The AEGIS dashboard is an analyst tool, not a product showcase. Every UI element should earn its presence by improving the analyst's ability to triage, evaluate, or act on intelligence signals.

Decorative elements — purely visual dividers, icon-only buttons with no label, animated indicators that convey no information, color gradients that add no semantic meaning — are noise. Noise slows the analyst down.

When in doubt: remove the decoration, keep the function.

### Analyst Workflow First

The sequence of actions an analyst takes to do their job is: scan → review → save or dismiss → repeat. Every UI decision should be evaluated against this workflow. Does this addition make the workflow faster? Does it reduce cognitive load? Does it keep the analyst in the triage state rather than forcing a context switch?

If a UI change requires the analyst to learn a new interaction pattern, it must provide proportional value. Learning cost is real cost.

### Minimize Clicks

Every additional click between the analyst and their goal is friction. The analyst should be able to:
- See the most significant new signals immediately on load
- Save or dismiss a signal with two clicks (click action → confirm)
- Start a scan with one click
- Switch views with one click

Do not add confirmation dialogs for non-destructive actions. Do not add navigation steps to reach primary functionality. Do not hide primary actions behind menus or dropdowns unless the action list is genuinely long.

### Preserve Visual Consistency

The AEGIS visual system uses a specific design language:
- Dark background (`#10151c`) with panel surfaces (`#151d26`)
- Amber accent (`#d69a38`) for primary interactive elements
- Monitor green (`#5ccf91`) for success and live states
- Alert red (`#d64b3f`) for critical and warning states
- Barlow Condensed for headers and labels (command center aesthetic)
- JetBrains Mono for scores and metadata (technical readability)

Do not introduce new colors outside the design token set. Do not change font families. Do not change the heading hierarchy. Do not change card border-radius, padding scale, or spacing rhythm without a specific request.

When adding a new UI element, it must look like it belongs in the existing system — not like a different designer made it.

### Do Not Redesign Working UI

If the analyst can currently perform a task and the task works correctly, the UI for that task is not broken. Do not propose or implement layout restructuring, component reorganization, or visual redesigns unless the owner explicitly identifies the current UI as a problem.

"This could be laid out better" is not a bug. "This would look more modern if" is not a requirement. "I would organize this differently" is not a request.

### Avoid Unnecessary Animations

Animations have a cost: they delay perception of state changes, they consume CPU, and they can mask latency. The AEGIS dashboard uses minimal motion by design — scan status indicators show live state without animation loops; card rendering is immediate.

Do not add enter/exit animations to cards, panels, or modals. Do not add loading spinners beyond what currently exists. Do not add hover-triggered transitions beyond the existing 0.15s color transitions already defined in `styles.css`.

### Avoid Clutter

Every element added to the UI competes for the analyst's attention. Before adding an element, ask: what does the analyst need to not see while working? The answer is: everything that is not relevant to the current task.

Do not add persistent status displays for state that does not require action. Do not add metadata labels that the analyst does not use for triage decisions. Do not add "additional information" sections that expand the card footprint without adding signal value.

The best interface shows the analyst exactly what they need and hides everything else.

---

## 5. Debugging Rules

### Verify Root Cause Before Fixing

Do not fix a symptom. A symptom is what the analyst observes: "the consensus tab shows nothing." The root cause is why: "the `view === 'archive'` render block was nested inside the `view === 'consensus'` conditional."

Fixing the symptom without finding the root cause produces a fix that may work for the immediate case but leaves the actual problem in the code. It may also produce a fix that makes the symptom disappear while the underlying bug causes a different symptom elsewhere.

Before writing a fix: state the root cause. State how you verified it. State why the fix addresses the root cause and not just the symptom.

### Do Not Guess

If you do not know what is causing a problem, say so. Do not apply a fix that "might work." Do not ship speculative changes to a production system on the assumption that they are probably correct.

"I believe the issue is X, but I would need to see the output of Y to confirm" is a valid response. "Let's try this and see if it helps" is not acceptable for production code.

Guessing has a specific failure mode in this system: it tends to produce changes that fix the presented symptom but silently break something else. The analyst then finds a new problem, reports it, and the debugging cycle starts over with compounded complexity.

### Check Dependencies Before Changing Code

Most errors in this system are not code bugs. Before concluding that a function is broken, verify:

1. **Port agreement** — Backend on 8002? Frontend hitting 8002? CORS allows 5175?
2. **Python interpreter** — Is VS Code using the right virtualenv? Is the terminal running the right Python?
3. **Ollama running** — Is Ollama started? Is `qwen2.5:7b` pulled?
4. **CWD** — Is `python main.py` being run from the project root?
5. **DB state** — Does the SQLite database have the expected columns? Run `PRAGMA table_info(signals)` if unsure.
6. **JSON validity** — Is `rss_sources.json` valid JSON? Is there a trailing comma?
7. **Node modules** — Has `npm install` been run after any `package.json` change?

A misconfigured environment produces symptoms that look like code bugs. Eliminate environment causes before touching code.

### Check Data Flow Before Changing Logic

If data is missing from the UI, trace it backwards:

```
UI shows nothing
→ Is the API returning data? (check Network tab / curl the endpoint)
→ Is the DB query returning rows? (check the WHERE conditions)
→ Did the insert succeed? (check is_deleted, tracked, filtered flags)
→ Did the pipeline process the item? (check scan summary: stored count)
→ Did the collector fetch the item? (check collected count)
→ Is the feed reachable? (curl the RSS URL)
```

The most common cause of "no data" in AEGIS is not a code bug — it is that the item was deduped (already in the DB as tracked or deleted), filtered (LLM marked it filtered=True), or the feed was unreachable. Verify the data pipeline before modifying the data pipeline.

### Confirm Assumptions With Evidence

If your debugging hypothesis requires an assumption about system state, confirm it before acting on it. Examples:

- "The item should be in the database" → run `SELECT * FROM signals WHERE title LIKE '%keyword%' LIMIT 5`
- "The route exists" → curl `http://127.0.0.1:8002/api/radar/consensus-status`
- "The frontend is hitting the right URL" → check the Network tab in browser DevTools
- "The LLM returned valid JSON" → add a print statement to `ai/analyzer.py::extract_json()` and run a single item

Assumptions that turn out to be wrong send debugging in the wrong direction. Confirm first.

---

## 6. Architecture Rules

### Local-First Architecture Preferred

AEGIS is designed to run entirely on one machine with no external service dependencies during normal operation (internet access is required only for RSS feed fetching). This is intentional.

Do not add dependencies on:
- Cloud APIs (OpenAI, Anthropic, Google, AWS, Azure)
- Third-party databases (MongoDB Atlas, Supabase, PlanetScale)
- External authentication services
- Remote logging or monitoring services
- CDN-hosted fonts or libraries required for core functionality (the Google Fonts import in `styles.css` is acceptable because it degrades gracefully to system fonts)

When a capability can be implemented locally, implement it locally. When a local implementation is insufficient, discuss the tradeoff explicitly before adding an external dependency.

### Minimize External Dependencies

Every external dependency is a surface for:
- Version conflicts
- Breaking API changes
- Network-dependent failures
- Licensing complications
- Supply chain security risks

Before adding a new Python package or npm dependency, ask: can this be done with what already exists? The current stack (`fastapi`, `uvicorn`, `feedparser`, `requests`, `pydantic`, React, Vite) is deliberately minimal. The entire backend has no ORM, no task queue, no cache layer, no message broker — these were omitted deliberately.

If a new dependency is genuinely necessary, add it with a pinned version and document why it was added.

### Prefer Simple Solutions

When two implementations achieve the same goal, prefer the simpler one. The measure of simplicity is: how much does a new developer need to understand before they can safely modify this code?

AEGIS uses:
- Plain SQLite with raw SQL — not SQLAlchemy, not an ORM, not a migration framework
- Plain CSS — not Tailwind, not CSS-in-JS, not a component library
- Plain threading — not asyncio, not Celery, not a task queue
- Plain `fetch()` — not axios, not React Query, not SWR

These choices are not limitations — they are deliberate simplicity boundaries. Introducing a more complex solution requires justification proportional to its complexity cost.

### Avoid Unnecessary Frameworks

A framework is appropriate when: (1) the problem it solves is genuinely hard, (2) the framework is already present in the stack, or (3) the framework is the clear industry standard for the problem domain.

A framework is not appropriate when: (1) the problem it solves is small, (2) it would be the only thing of its kind in the stack, or (3) its primary benefit is "cleaner code" rather than solving a real capability gap.

Do not propose adding Redux for state management because the current `useState` approach is "getting complex." Do not propose adding SQLAlchemy because raw SQL is "harder to read." Do not propose adding a CSS framework because "Tailwind would be easier." These are framework preferences, not requirements.

### Preserve Modular Structure

The current module boundaries are:
- `sources/` — data collection only (no analysis, no storage)
- `ai/` — LLM interaction only (no collection, no storage)
- `backend/app/core/` — scoring logic only (no I/O)
- `backend/app/db/` — storage only (no business logic)
- `backend/app/api/` — HTTP routing only (no business logic)
- `tasks/` — orchestration only (coordinates the above)
- `frontend/` — display and interaction only (no business logic)

Do not add database calls to `sources/`. Do not add HTTP calls to `pipeline.py`. Do not add scoring logic to `radar.py`. Do not add UI state management to `api.js` beyond API calls.

When adding a new capability, identify which layer it belongs to. If it does not fit cleanly into an existing layer, discuss the architecture before creating a new one.

### Keep Responsibilities Separated

Each file should have one reason to change. If a change to the scoring formula requires modifying `database.py`, the responsibilities are not properly separated. If a change to the API route format requires modifying `RadarDashboard.jsx`, the responsibilities are not properly separated.

The current architecture achieves this well. Do not violate it in the name of "simplicity."

---

## 7. AI Collaboration Rules

### Read Documentation Before Touching Code

The `docs/` folder contains architecture documents that describe decisions made during development. Before modifying any significant system, read the relevant documentation:

- `AEGIS_STORAGE_AND_STRUCTURE.md` — physical layout, data flow, database schema, architectural decisions
- `AEGIS_AI_HANDOFF_SOP.md` — operating procedures, known bugs, sensitive areas
- `AEGIS_DEVELOPER_RULES.md` — this file

These documents exist because the codebase contains non-obvious decisions. Reading them takes five minutes and prevents hours of work on the wrong problem.

### Read Architecture Before Modifying Code

Before modifying any file that participates in a multi-system workflow — `radar.py`, `database.py`, `RadarDashboard.jsx`, `front_page_consensus.py`, `pipeline.py` — understand the complete flow it participates in. Do not read only the function you are changing. Read the callers. Read what it calls. Read what the outputs feed into.

A change that looks correct in isolation may break behavior three hops away in the data flow.

### Read Decision Logs Before Replacing Logic

The `AEGIS_STORAGE_AND_STRUCTURE.md` document contains a "Failed Approaches" section that documents what was tried and why it was replaced. Before "simplifying" any algorithm, check whether the current complexity is the solution to a previous simplification's failure.

**The most important example in this codebase:** The Stage 12 clustering algorithm in `front_page_consensus.py` looks more complex than necessary. It is. It is complex because Stage 11's simpler version produced mega-clusters of unrelated stories. The complexity is the fix. Do not simplify it.

When you see code that appears over-engineered, consider: was this complexity earned by a failure you have not read about?

### Preserve Intentional Design Decisions

The following patterns in this codebase are intentional and must not be "improved":

| Pattern | Why It Exists |
|---------|--------------|
| Soft delete (`is_deleted=1`) instead of hard delete | Preserves dedup fingerprints that block story re-import |
| `ensure_columns()` migration pattern | Safe schema evolution without destroying existing data |
| `check_same_thread=False` on SQLite connection | Required for background scan threads |
| `daemon=True` on scan threads | Prevents orphaned threads on process exit |
| Pre-AI score sort before LLM calls | Ensures 60 LLM slots go to highest-priority content |
| Per-category quota enforcement | Prevents high-volume tech feeds from crowding geopolitical coverage |
| `_HIGH_SALIENCE` blocklist in consensus clustering | Prevents high-frequency entities from over-merging unrelated stories |
| Consensus source list separate from main RSS list | Different scanning purpose — editorial consensus, not signal scoring |
| `title_norm` dedup blocks tracked AND deleted | Both saved and dismissed stories suppress future near-duplicate intake |

If you encounter one of these patterns and believe it is wrong, do not remove it. State your concern explicitly and wait for confirmation that removal is appropriate.

### Do Not "Clean Up" Code Without Understanding Why It Exists

Comments, redundant-looking checks, conservative defaults, and verbose-looking implementations often exist because a shorter version was tried and failed. Respect the code's history.

Specifically:
- Do not remove comments that explain why something is done a certain way
- Do not remove defensive checks (null checks, bounds clamping, fallback values) because "they shouldn't be needed"
- Do not consolidate try/except blocks into broader handlers that lose specificity
- Do not remove print statements from scan functions — they are the analyst's visibility into scan progress
- Do not replace explicit string comparisons with pattern matchers that accept broader input

"Cleaner" code that breaks edge cases is not cleaner — it is less tested.

### State Your Interpretation Before Proceeding on Ambiguous Requests

If a request could be interpreted multiple ways, or if fulfilling it would require assumptions about the intended behavior, state your interpretation explicitly before writing code.

Example: "I'm interpreting this as adding a visual indicator to the consensus card, not adding a new database field. If you mean the latter, let me know before I proceed."

This prevents wasted work. The cost of a clarifying question is one message. The cost of a misinterpreted implementation is a full file return, a review, a correction request, another full file return, and the introduction of whatever subtle errors entered during the hasty second implementation.

---

## 8. Documentation Rules

### Update Architecture When Architecture Changes

When a new table is added to the database, update `AEGIS_STORAGE_AND_STRUCTURE.md` — specifically the database schema section. When a new route is added, update the route table. When a new source file is added to the project, update the folder map.

Documentation that is out of date is worse than no documentation, because it actively misleads the next person who reads it.

This is not optional maintenance. When a ticket involves a structural change, updating the architecture document is part of the ticket.

### Update SOP When Workflows Change

When a new scan type is added, update `AEGIS_AI_HANDOFF_SOP.md` — add the workflow to Section 4, add the route to Section 2's route table, add any new sensitive area to Section 6. When a bug is discovered and fixed, add it to Section 7 with the root cause and fix.

The SOP is a living document. Its value degrades if it describes the system as it was rather than as it is.

### Update Decision Log When Major Decisions Occur

When a design decision is made that is non-obvious — "we chose X over Y because Z" — document it in `AEGIS_STORAGE_AND_STRUCTURE.md` Section 10. This is especially important when:

- A simpler approach was available but rejected
- A previous approach was replaced
- A constraint was imposed for non-obvious reasons
- A tradeoff was accepted that may be revisited later

The purpose of the decision log is to prevent future developers (human or AI) from re-litigating settled decisions without the context that informed them.

### Do Not Delete Documentation

Old sections are more valuable than they appear. Even if a feature was removed, a section describing why it was removed and what replaced it has value. Do not clean up documentation by removing history.

When a section becomes outdated, mark it as updated or superseded, and record when and why the change occurred.

---

## 9. Git Rules

### Commit Before Major Changes

Before any significant AI-assisted code change, create a checkpoint commit:

```powershell
git add -A
git commit -m "checkpoint: before [description of planned change]"
```

This is non-negotiable. If a large AI-generated change introduces a regression, the only reliable recovery path is `git checkout` to the pre-change state. Without a checkpoint, recovery requires manually undoing changes across multiple files — an error-prone process that may itself introduce new problems.

### Create Named Checkpoints for Phase Completions

Every completed development phase is a natural commit point. AEGIS uses a phase naming convention:

```
Stage 12: event-identity clustering for consensus engine
Phase 2A: AEGIS intelligence layer — scoring pass
Stage 10: Source Intelligence Model — reliability tier + editorial role
```

Use this convention. Phase labels make the git history readable as a development narrative, not just a list of file changes.

### Protect Working Versions

Never `git push --force` to a branch that contains a working version without explicit agreement. Never `git reset --hard` without committing or stashing all working changes first. Never amend a published commit that has been used as a checkpoint.

The checkpoint commit history is a safety net. Do not cut holes in the net.

### Use Branches for Experiments

Any change that:
- Introduces a new concept not yet designed
- Modifies a critical system (clustering, scoring, dedup) with uncertain outcome
- Adds a dependency that may need to be reverted
- Attempts an approach whose correctness is not yet verified

...should be made on a branch:

```powershell
git checkout -b experimental/[description]
```

Work on the branch until the change is verified. Merge to `dev` only after manual testing. Merge to `main` only after the change is stable.

### Recommended Branch Structure

| Branch | Purpose | Merge target |
|--------|---------|-------------|
| `main` | Production-stable. Only verified, tested changes. | — |
| `dev` | Active development. AI changes staged here first. | `main` (after testing) |
| `experimental/*` | Speculative or risky changes. | `dev` (after verification) |

Do not make speculative changes directly on `main`. Do not use `main` as a working branch.

---

## 10. ARC NEXUS Standards

These standards apply across AEGIS, NEXIS-LOCAL, PhotoGather, and all future ARC NEXUS projects.

### Single-Analyst First

All ARC NEXUS tools are built for a single analyst on a local machine. Multi-user features, cloud sync, remote access, and role-based permissions are out of scope unless explicitly planned for a specific project. Do not design for scale that does not exist and has not been committed to.

This means: local storage is preferred, local AI is preferred, local dependencies are preferred, and complexity justified only by multi-user or cloud-scale requirements is not welcome.

### The Analyst's Time Is the Product

Every tool exists to make the analyst faster, more informed, and more accurate. Every development decision should be evaluated against this measure. Does this make the analyst faster? Does this reduce friction? Does this surface better information?

Features that make code "cleaner" without benefiting the analyst are not improvements. Infrastructure that would "scale well" but adds deployment complexity is not progress. UI that looks impressive in a demo but slows the analyst down in daily use is a failure.

### Data Locality and Privacy

ARC NEXUS tools are designed to process sensitive, pre-published intelligence. No data created or processed by these tools should leave the analyst's machine without an explicit design decision and explicit analyst consent.

This means:
- No telemetry, no usage analytics, no crash reporting to external services
- No cloud-synced configuration or session data
- No API calls to third-party services that pass content (not just metadata)
- No logging to external services

When in doubt: keep data local.

### Consistent Documentation Standards

Every ARC NEXUS project should maintain the following documentation set:

| Document | Contents |
|----------|---------|
| `AEGIS_STORAGE_AND_STRUCTURE.md` (or equivalent) | Architecture, data flow, database schema, design decisions, failed approaches |
| `AEGIS_AI_HANDOFF_SOP.md` (or equivalent) | Operating procedures, file map, sensitive areas, known bugs, AI collaboration rules |
| `AEGIS_DEVELOPER_RULES.md` (or equivalent) | Development standards, philosophy, git rules, ARC NEXUS standards |
| `AEGIS_DECISION_LOG.md` (or equivalent) | Permanent record of why major decisions were made and what failed |
| `AEGIS_RECOVERY_AND_SETUP.md` (or equivalent) | Startup/shutdown procedures, recovery steps, port configuration, failure modes |
| `AEGIS_USER_INSTALL_GUIDE.md` (or equivalent) | End-user install guide: prerequisites, step-by-step setup, verification |

Future projects may adapt the naming, but the six-document structure should be preserved. These documents exist so that any AI assistant or developer, at any future date, can onboard to the project in minutes rather than hours.

### Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Python functions | `snake_case` | `run_all_collectors()` |
| Python classes | `PascalCase` | `SignalPipeline` |
| Python constants | `UPPER_SNAKE_CASE` | `MAX_POSTS_TO_PROCESS` |
| Python private functions | `_snake_case` | `_should_merge()` |
| React components | `PascalCase` | `SignalCard`, `RadarDashboard` |
| React state variables | `camelCase` | `consensusData`, `activeView` |
| CSS classes | `kebab-case` | `opp-card`, `consensus-tier-badge` |
| CSS custom properties | `--kebab-case` | `--bg-main`, `--amber-glow` |
| API route paths | `kebab-case` | `/consensus-scan`, `/scan-status` |
| Git branch names | `type/description` | `experimental/archive-view` |
| DB column names | `snake_case` | `significance_score`, `title_norm` |

Do not introduce new naming conventions without discussion. Consistency in names makes code searchable and reduces the cognitive load of navigating an unfamiliar file.

### Dependency Budget

Each ARC NEXUS project should have a minimal, documented dependency set. When a dependency is added, it should be added with a justification:

> Added `feedparser` because the standard library `xml.etree.ElementTree` does not handle malformed RSS reliably, and nearly all real-world feeds have minor markup errors.

Dependencies that cannot be justified in one sentence should be reconsidered.

---

## 11. Instructions For Any Future AI

This section is written directly to you — the AI assistant reading this document before working on AEGIS or any ARC NEXUS project.

---

**Your default is to preserve, not improve.**

The code you are reading has survived real use. The patterns that look unusual have reasons. Your instinct to make things cleaner, more idiomatic, or more efficient is your training speaking — but training optimizes for general patterns, not for this specific system's constraints and history. Assume the code is right until you can prove it is wrong.

---

**Read before you write.**

Before modifying any file, read it in full. Before modifying any system, read its architecture in `AEGIS_STORAGE_AND_STRUCTURE.md`. Before replacing any algorithm, read the failed approaches in Section 11 of that document. The documentation was written specifically so that you would not have to rediscover these lessons.

If you skip this step to save time, you will spend more time fixing the regression you introduce.

---

**The scope of your work is what was asked. Nothing more.**

If you are asked to fix a specific bug, fix that bug. Do not add related error handling you noticed while reading the file. Do not refactor the function while you are there. Do not improve the adjacent function that has a similar pattern. Do not add a comment that you think would help future readers.

Every action outside the stated scope is an action that was not reviewed, not tested against the full workflow, and not wanted. It is not a gift — it is noise that the project owner must evaluate and potentially revert.

---

**The project owner has more context than you do.**

You can read the codebase. You cannot read the conversation history, the planned roadmap, the decisions that were consciously deferred, or the reasons certain constraints exist. When your analysis produces a recommendation that conflicts with the existing code, the conflict is more likely to reflect your missing context than a genuine error in the code.

This does not mean the code is always right. It means that when you disagree, you should say so and explain your reasoning — not silently override the existing decision.

---

**Ask, do not assume.**

When a request is ambiguous, ask a clarifying question. The project owner would rather answer one question than review a misimplemented feature. State your interpretation before building. State your assumptions before debugging. State your concerns before implementing a change that you believe might have unintended consequences.

The question costs one message. The wrong implementation costs a full return, a review cycle, a correction, another return, and the introduction of errors that entered during the rushed second pass.

---

**Your output is only as good as your reading.**

If you do not read `database.py` before adding a database column, you may add it to `ensure_tables()` instead of `ensure_columns()`, which will fail silently on existing databases. If you do not read `front_page_consensus.py` before modifying the clustering logic, you may reintroduce the Stage 11 over-merging bug. If you do not read `radar.py` and `api.js` in parallel before modifying a route, you may break the path agreement that every frontend call depends on.

Read everything relevant. Not a summary. Not the first 50 lines. Read it.

---

**Return the full file. Always.**

When you return a modified file, return the entire file. Do not use placeholders. Do not truncate unchanged sections. Do not summarize instead of writing. The project owner replaces the old file with your output — your output must be a complete, working file.

This is the single most important operational rule. Break it and the project owner must manually merge your partial output with the original, under time pressure, across potentially multiple files. The error rate of that process is 100%.

---

**The analyst's time is the product. Protect it.**

Every feature you add that was not requested consumes the analyst's attention during review. Every UI change you make that was not requested disrupts the analyst's workflow. Every architectural decision you introduce that was not scoped consumes the analyst's time when it needs to be revisited or reversed.

The best work you can do for this project is to solve exactly the problem that was stated, return a complete correct file, explain what you changed and why, and leave everything else exactly as you found it.

---

*End of AEGIS Developer Rules — Version 1.0*  
*ARC NEXUS LLC*  
*May 28, 2026*

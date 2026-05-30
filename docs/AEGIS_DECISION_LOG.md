# AEGIS Decision Log
## ARC NEXUS LLC — Permanent Institutional Memory
### SWAT Signal Desk

**Version:** 1.0  
**Date:** May 28, 2026  
**Purpose:** Permanent record of why major decisions were made, what was tried before them, what failed, and what was learned. This document exists so that future developers and AI assistants do not revisit settled questions without knowing the cost of the paths already walked.

**Confidence notation used throughout this document:**
- *(confirmed)* — directly evidenced by code, comments, or explicit documentation
- *(inferred)* — reconstructed from code patterns, naming conventions, and architectural evidence; likely accurate but not directly stated

---

## How to Use This Log

**Before replacing any algorithm:** Search this document for the algorithm's purpose. If a failed-approach entry exists, the current implementation is the solution to that failure. Do not re-introduce the failed approach.

**Before simplifying any code:** Search this document for the component. If the complexity was earned by a failure, the simplification will reproduce the failure.

**Before redesigning any workflow:** Search this document for the workflow. If the current design replaced an earlier design, understand why the earlier design was abandoned.

**Before removing any constraint:** Search this document for the constraint's name or purpose. Constraints that appear arbitrary usually exist because an unconstrained version was tried and broke something.

**Index of searchable terms:**
`soft-delete` · `title_norm` · `ensure_columns` · `source_weight` · `reliability_tier` · `editorial_role` · `_HIGH_SALIENCE` · `_should_merge` · `one-word clustering` · `Stage 11` · `Stage 12` · `pre_score` · `category_quota` · `scan_id` · `archive` · `inline confirm` · `window.confirm` · `tracked` · `is_deleted` · `dedup` · `consensus` · `orientation` · `corroboration`

---

## Table of Contents

1. [Foundational Decisions](#section-1-foundational-decisions)
2. [Data and Storage Decisions](#section-2-data-and-storage-decisions)
3. [Source Intelligence Decisions](#section-3-source-intelligence-decisions)
4. [Consensus Engine Decisions](#section-4-consensus-engine-decisions)
5. [Failed Approaches](#section-5-failed-approaches)
6. [UI and Workflow Decisions](#section-6-ui-and-workflow-decisions)
7. [Development Process Decisions](#section-7-development-process-decisions)
8. [Lessons That Cost Time](#section-8-lessons-that-cost-time)
9. [Open Questions](#section-9-open-questions)

---

## Section 1: Foundational Decisions

---

### D-001
**Date:** Pre-launch (inferred from repo structure)
**Status:** Active — foundational, not under review
**Category:** Architecture

**Title:** Local-First Architecture

**Problem:**
The analyst needs a news intelligence system that processes potentially sensitive signals, stores editorial judgments, and runs inference on news content. Cloud-based alternatives would require routing all content through third-party infrastructure, creating privacy exposure, per-call cost accumulation, and dependency on external service availability.

**Options Considered:**
1. Cloud-hosted backend (AWS/Azure) with cloud LLM API (OpenAI, Anthropic)
2. Hybrid: local frontend + cloud backend + cloud LLM
3. Fully local: local backend + local LLM via Ollama + local SQLite *(selected)*

**Decision:**
Fully local architecture. All compute, storage, and inference runs on the analyst's machine. Internet is required only for RSS feed fetching.

**Reason:**
- News intelligence work involves content that may be politically sensitive, pre-publication, or otherwise not appropriate to route through third-party inference services
- Cloud LLM APIs accumulate per-call costs that scale with usage volume
- Cloud services introduce availability risk (rate limits, outages, deprecation)
- Local Ollama provides adequate inference quality for structured JSON extraction with `qwen2.5:7b`
- A single-analyst tool does not require the scale benefits of cloud infrastructure

**Tradeoffs Accepted:**
- Dependent on analyst's hardware performance
- LLM inference is slower than cloud APIs
- Requires Ollama installation and model download as setup step
- System is not accessible from other devices without VPN or tunneling (acceptable — not a goal)

**Implementation:**
- Backend: FastAPI + uvicorn on `127.0.0.1:8002`
- AI: Ollama on `127.0.0.1:11434`, model `qwen2.5:7b`
- Storage: SQLite at `market_radar.db` in project root
- Frontend: Vite dev server on `127.0.0.1:5175`
- All external calls: RSS feed fetching only

**Outcome:** *(confirmed)* System operates entirely offline except for RSS fetches. No data leaves the machine during analysis.

**Lessons Learned:** Local-first architecture is a constraint that simplifies several subsequent decisions — no auth, no multi-tenancy, no cloud cost management, no data compliance requirements.

**Related Files:** `main.py`, `ai/analyzer.py`, `backend/app/app.py`

**Future Notes:** NEXIS-LOCAL migration will revisit this for multi-device access. The migration target is likely a local server with LAN access, not a cloud deployment.

---

### D-002
**Date:** Pre-launch (inferred)
**Status:** Active
**Category:** Storage

**Title:** SQLite Instead of a Client/Server Database

**Problem:**
The system needs persistent storage for signals, scores, consensus results, and deduplication data. Multiple options exist across the complexity spectrum.

**Options Considered:**
1. PostgreSQL — full-featured, client/server, requires daemon process
2. MySQL/MariaDB — similar to PostgreSQL
3. SQLite — embedded, zero-configuration, file-based *(selected)*
4. In-memory only — no persistence between restarts

**Decision:**
SQLite with Python stdlib `sqlite3` module. No ORM. Raw SQL throughout.

**Reason:**
- Zero configuration: no database server to install, start, or manage
- Included in Python standard library: no additional dependency
- Single file: `market_radar.db` is trivially backed up by copying one file
- Fully sufficient for single-analyst read/write patterns
- Raw SQL keeps queries transparent and debuggable without ORM abstraction layer

**Tradeoffs Accepted:**
- File-level locking limits concurrent writes (mitigated with `check_same_thread=False` and connection sharing)
- No built-in replication or failover
- Schema migrations require manual `ALTER TABLE` rather than framework-managed migrations
- Full-text search is limited (no built-in FTS5 used currently)

**Implementation:**
`database.py::Database.__init__()` calls `sqlite3.connect(path, check_same_thread=False)`. The `check_same_thread=False` flag is required because background scan threads share the singleton `Database` instance instantiated in `radar.py` at module load time.

**Outcome:** *(confirmed)* SQLite handles the load without issue. The `ensure_columns()` migration pattern provides safe schema evolution without a migration framework.

**Lessons Learned:** The choice of `check_same_thread=False` is non-negotiable given the threading model. Do not remove it thinking it is a security bypass — it is a requirement.

**Related Files:** `backend/app/db/database.py`

**Future Notes:** NEXIS-LOCAL at scale may require PostgreSQL for full-text search, concurrent multi-process writes, and query performance on large datasets. The schema concepts transfer cleanly.

---

### D-003
**Date:** Pre-launch (inferred)
**Status:** Active
**Category:** AI / Inference

**Title:** Ollama Instead of Cloud AI APIs

**Problem:**
Each collected article requires structured intelligence extraction: topic, summary, framing, claims, signal type, significance estimate, manipulation risk, and narrative flags. This requires LLM inference. The question was where that inference should run.

**Options Considered:**
1. OpenAI API (GPT-4o, GPT-4-turbo)
2. Anthropic API (Claude)
3. Google Gemini API
4. Ollama with a local open-weight model *(selected)*

**Decision:**
Ollama running `qwen2.5:7b` locally at `http://127.0.0.1:11434`.

**Reason:**
- Consistent with D-001 (local-first): content does not leave the machine
- No per-call costs — 60 LLM calls per scan at cloud API rates would accumulate significantly over daily use
- Temperature `0.1` near-deterministic JSON output matches the structured extraction task well
- `qwen2.5:7b` provides adequate quality for the structured JSON extraction prompt
- Ollama provides a clean REST API that mirrors the cloud API pattern, making a future model swap easy

**Tradeoffs Accepted:**
- Inference is slower than cloud APIs (seconds per item vs. sub-second)
- Model quality ceiling lower than frontier models for nuanced analysis
- Requires Ollama setup and model download (~4GB for `qwen2.5:7b`)
- If Ollama is not running, scans process items but all AI fields are empty/default

**Implementation:**
`ai/analyzer.py` calls `POST http://127.0.0.1:11434/api/generate` with `model: "qwen2.5:7b"`, `temperature: 0.1`, `format: "json"`. The `call_llm()` function has a 60-second timeout. `extract_json()` provides a fallback JSON extraction when the model returns non-JSON-wrapped responses.

**Outcome:** *(confirmed)* System degrades gracefully when Ollama is unavailable — items are processed but `significance_score` defaults to `0.0`. No crashes.

**Lessons Learned:** The `format: "json"` parameter in the Ollama payload forces JSON output mode and substantially reduces malformed response rate. Always use it for structured extraction tasks.

**Related Files:** `ai/analyzer.py`, `models.py`

**Future Notes:** Model can be swapped by changing `MODEL = "qwen2.5:7b"` in `ai/analyzer.py`. A more capable local model (e.g., `qwen2.5:14b`, `llama3.1:8b`) could improve significance calibration at the cost of slower inference.

---

### D-004
**Date:** Pre-launch (inferred)
**Status:** Active — foundational
**Category:** Product scope

**Title:** Single Analyst Design

**Problem:**
Every tool architecture decision bifurcates around a fundamental question: is this system for one person or many? Authentication, session management, data isolation, multi-user concurrency, and role-based access all emerge from a multi-user requirement.

**Options Considered:**
1. Multi-user with authentication and role management
2. Single analyst, no authentication *(selected)*

**Decision:**
Single analyst, no authentication, local machine only. The system is designed as a personal intelligence tool.

**Reason:**
- The tool serves one analyst's workflow at ARC NEXUS
- Multi-user complexity adds infrastructure cost with zero benefit for the actual use case
- No authentication reduces setup friction and eliminates an entire category of bugs
- Single-analyst design allows the system to make assumptions (default Library view, unified signal store, single dedup namespace) that would require per-user isolation in a multi-user system

**Tradeoffs Accepted:**
- System cannot be shared between team members without architectural revision
- No audit trail of which analyst took which action
- Security is perimeter-based (local machine only) rather than credential-based

**Implementation:** No auth middleware in FastAPI. CORS allows only `127.0.0.1:5175` and `localhost:5175` — effectively preventing access from any other origin as a minimal boundary.

**Outcome:** *(confirmed)* Eliminates entire classes of complexity. The CORS restriction provides a lightweight boundary.

**Lessons Learned:** Committing to single-analyst design early allows several simplifications that would otherwise require careful per-user scoping: the `title_norm` dedup is a global namespace, the `tracked` flag is a global state, and the Library is a single shared store.

**Related Files:** `backend/app/app.py`

**Future Notes:** If NEXIS-LOCAL requires team access, authentication and per-analyst namespacing will be required before sharing the database.

---

### D-005
**Date:** Pre-launch (inferred)
**Status:** Active
**Category:** Engineering philosophy

**Title:** Minimal Dependency Philosophy

**Problem:**
Modern Python and JavaScript ecosystems offer frameworks, libraries, and tools for nearly every problem. Each dependency adds convenience but also adds version conflict risk, security surface, breaking change exposure, and cognitive load for anyone reading the code.

**Options Considered:**
1. Adopt popular frameworks for each layer (SQLAlchemy, Celery, Redux, Tailwind, Axios, React Query, etc.)
2. Use only what is necessary *(selected)*

**Decision:**
Maintain a minimal dependency set. Each dependency must justify its inclusion with a capability that cannot reasonably be implemented with existing tools.

**Reason:**
- The project is maintained by one person with AI assistance — every new dependency is a new surface to understand and debug
- Core functionality (RSS fetching, SQLite queries, API routing, React state) does not require additional abstractions
- Simpler dependency graph means fewer conflict issues across Python and Node upgrades

**Tradeoffs Accepted:**
- Some boilerplate that frameworks would eliminate must be written explicitly (raw SQL migrations, manual fetch wrappers)
- Less "industry standard" patterns may confuse developers familiar with framework-heavy stacks

**Implementation:**
Python backend: `fastapi`, `uvicorn`, `feedparser`, `requests`, `pydantic` — nothing more.
Frontend: `react`, `react-dom`, `vite`, `@vitejs/plugin-react` — no component library, no state manager, no HTTP client library.

**Outcome:** *(confirmed)* Stack is readable top to bottom without framework documentation. Debugging requires only language knowledge, not framework knowledge.

**Lessons Learned:** Minimal dependencies compound in value over time. The system is easier to maintain at month 12 than a fully-framework system would be, because there are no framework upgrade cycles to manage.

**Related Files:** `frontend/package.json`, `requirements.txt`

**Future Notes:** This philosophy should be the default for all ARC NEXUS projects. Departures should be documented with explicit justification.

---

## Section 2: Data and Storage Decisions

---

### D-006
**Date:** Stage 9 (inferred)
**Status:** Active — critical
**Category:** Data integrity / deduplication

**Title:** Tracked Reports Block Re-Import

**Problem:**
When the analyst saves a story to the Library, subsequent scans may collect the same story from other outlets or as a reposted/updated version. Without a block, the analyst's Library would be cluttered with near-duplicates of stories they have already saved, and the Live Feed would continuously resurface stories already reviewed.

**Options Considered:**
1. No dedup beyond URL/external_id — let duplicates in, analyst manually dismisses them
2. Block re-import based on URL exact match only
3. Block re-import based on title similarity for stories already saved or deleted *(selected)*

**Decision:**
When a signal is saved (`tracked=1`) or deleted (`is_deleted=1`), its `title_norm` fingerprint enters the dedup blocklist. Future `insert_signal()` calls that match an existing `title_norm` against this blocklist skip the insert entirely.

**Reason:**
- URL-only dedup fails when the same story is syndicated across multiple outlets with different URLs
- The analyst's decision to save or dismiss a story is an editorial judgment that should persist
- Near-duplicate title fingerprinting catches reposted and updated versions of the same story
- Without this block, every scan would re-surface already-reviewed content, defeating the triage workflow

**Tradeoffs Accepted:**
- A genuinely new development on a similar story (same topic, different event) could be incorrectly blocked if its title produces the same fingerprint — the fingerprint uses only the first 10 significant words
- The block is permanent with no undo — a story dismissed in error cannot be "undismissed" to allow future near-duplicates back in
- Requires `is_deleted` rows to remain in the database (hard-deleting them removes the dedup protection)

**Implementation:**
`database.py::_normalize_title()` strips punctuation, lowercases, removes stop words, keeps first 10 significant words. `insert_signal()` queries:
```sql
SELECT id FROM signals
WHERE title_norm = ?
  AND (tracked = 1 OR is_deleted = 1)
LIMIT 1
```
If any row matches, the insert is skipped and `None` is returned.

**Outcome:** *(confirmed)* Eliminates recurring near-duplicate clutter in Live Feed and Library. Core to the analyst's triage workflow functioning correctly over time.

**Lessons Learned:** This mechanism is invisible when working correctly. When debugging "why isn't this story appearing," always check whether it is being blocked by the dedup system before concluding there is a pipeline bug.

**Related Files:** `backend/app/db/database.py`

**Future Notes:** If the analyst wants to "reset" their dismissed items (e.g., after a major event they now want to re-investigate), there is no current mechanism. A future admin function could be: `UPDATE signals SET is_deleted = 0, title_norm = '' WHERE is_deleted = 1 AND created_at < ?`

---

### D-007
**Date:** Early development (inferred from `ensure_columns` presence in initial schema)
**Status:** Active — critical
**Category:** Data integrity

**Title:** Soft Delete Instead of Hard Delete

**Problem:**
When the analyst dismisses a signal, the system must record that dismissal. The question is whether to remove the database row entirely or mark it as deleted while keeping the row.

**Options Considered:**
1. Hard delete: `DELETE FROM signals WHERE id = ?` — row removed permanently
2. Soft delete: `UPDATE signals SET is_deleted = 1 WHERE id = ?` — row kept, hidden from queries *(selected)*

**Decision:**
Soft delete (`is_deleted=1`). Row remains in database indefinitely.

**Reason:**
The deduplication system (D-006) depends on `title_norm` fingerprints being present in the database for dismissed stories. If a row is hard-deleted, its fingerprint is removed from the blocklist, and the same story can be re-imported on the next scan — exactly the behavior the analyst intended to prevent by deleting it.

Soft delete makes the deleted row invisible to all normal queries (`WHERE is_deleted = 0` is present on every fetch query) while preserving the fingerprint for future dedup checks.

**Tradeoffs Accepted:**
- Database grows over time including dismissed items that will never be shown
- No recovery mechanism for accidental deletes
- The "delete" action in the UI is permanent and irreversible by design
- Analysts who expect a "recently deleted" recovery feature will not find one

**Implementation:**
`database.py::delete(id)`:
```python
UPDATE signals SET is_deleted = 1 WHERE id = ?
```
All fetch queries include `WHERE is_deleted = 0`. The `get_recent()` method enforces this unconditionally.

**Outcome:** *(confirmed)* Deleted items stay dismissed across all future scans. The analyst never needs to re-dismiss the same story.

**Lessons Learned:** The soft-delete/dedup connection is non-obvious. Anyone who encounters the `is_deleted` column and concludes it is "just a display toggle" that could be replaced with a hard delete will break the dedup system. This must be documented and preserved.

**Related Files:** `backend/app/db/database.py`, `backend/app/api/routes/radar.py`

**Future Notes:** If storage becomes a concern at large scale, `is_deleted=1` rows older than a configurable retention window could be purged — but only after verifying the title_norm fingerprints are preserved elsewhere (e.g., a separate dismissed_fingerprints table).

---

### D-008
**Date:** Stage 9 (inferred from comment: "Stage 9: Intake memory" in database.py)
**Status:** Active
**Category:** Data integrity / deduplication

**Title:** Title Normalization Dedup System (`title_norm`)

**Problem:**
Exact URL matching catches identical articles. But the same story is frequently published by multiple outlets with different URLs and slightly different headlines. Without a content-based dedup mechanism, every outlet covering the same event would create a separate database row, flooding the analyst's view with near-identical content.

**Options Considered:**
1. No near-duplicate dedup — all unique URLs admitted
2. Semantic similarity via embeddings — computationally expensive, requires another model
3. Exact title match — too strict, misses minor title variations
4. Normalized title fingerprint (stop-word-stripped) *(selected)*

**Decision:**
Compute `title_norm` by lowercasing, stripping punctuation, removing a curated stop-word list, and keeping the first 10 significant words. This fingerprint is stored in the database and indexed. Near-duplicates produce identical or near-identical fingerprints.

**Reason:**
- Fast: runs at O(n) string operations with no external calls
- No additional dependencies
- Covers the primary duplication pattern: the same story with minor headline variations ("Trump signs X order" vs "Trump signs executive order targeting X")
- The first 10 significant words capture the core event identity for most news headlines

**Tradeoffs Accepted:**
- Two genuinely different stories could share the same fingerprint if their first 10 significant words are identical
- The fingerprint is not semantic — it misses paraphrase-level duplicates where no words overlap
- The stop-word list is curated and may need expansion if common words that carry no event identity are not currently excluded

**Implementation:**
`database.py::_normalize_title()`: lowercase → strip `[^a-z0-9\s]` → split → filter by length ≥ 3 and not in `_TITLE_STOP` → join first 10. Index: `CREATE INDEX IF NOT EXISTS idx_signals_title_norm ON signals(title_norm)`.

**Outcome:** *(confirmed)* Substantially reduces duplicate content in the feed without requiring semantic similarity computation. Backfill migration was written to normalize all existing rows when the column was first added.

**Lessons Learned:** The `idx_signals_title_norm` index is load-bearing for scan performance. Without it, every insert triggers a full-table scan against the dedup query.

**Related Files:** `backend/app/db/database.py`

---

### D-009
**Date:** Stage 13 (inferred from comment: "Stage 13: Consensus Archive" in codebase)
**Status:** Active
**Category:** Storage / UX

**Title:** Archive Snapshot Strategy for Consensus Scans

**Problem:**
Front Page Consensus scans capture what major outlets are leading with at a specific moment. This information is perishable — the next scan may reflect a completely different editorial priority. The question was whether to store only the latest results or accumulate a historical record.

**Options Considered:**
1. Overwrite-latest: only one consensus result set stored at a time, replaced on each scan
2. Append with scan snapshots: each scan generates a unique `scan_id`, all results kept permanently *(selected)*

**Decision:**
Each scan generates a unique `scan_id` (UUID + timestamp string). All cluster rows for a scan share this ID. The database accumulates all scans indefinitely. The UI provides an archive browser.

**Reason:**
- The analyst's primary workflow is temporal comparison: "What were outlets leading with this morning vs. this afternoon?"
- Overwrite-latest destroys the ability to make this comparison
- The `scan_id` + GROUP BY pattern provides a clean archive query without additional tables
- Storage cost is minimal: 10 cluster rows per scan, each row a few KB

**Tradeoffs Accepted:**
- Database grows over time with no automatic pruning
- No current mechanism to delete individual scans from the archive
- Archive browsing UI adds complexity to `RadarDashboard.jsx`

**Implementation:**
`scan_id = f"{uuid4()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"`. All rows for one scan share this ID. `get_consensus_archive()` uses `GROUP BY scan_id`. `get_consensus_by_scan_id()` fetches one snapshot.

**Outcome:** *(confirmed)* Enables temporal editorial comparison across scans. The archive view shows a list of all historical scan snapshots with their timestamps and cluster counts.

**Lessons Learned:** See failed approach FA-002 — the overwrite-latest approach was the predecessor. Once lost, historical scan data cannot be recovered. The archive strategy should be the default for any time-series intelligence capture.

**Related Files:** `backend/app/db/database.py`, `tasks/front_page_consensus.py`, `frontend/src/pages/RadarDashboard.jsx`, `frontend/src/lib/api.js`

---

### D-010
**Date:** Early development (inferred from `ensure_columns` migration comments)
**Status:** Active
**Category:** Storage / maintenance

**Title:** Schema Evolution Through `ensure_columns()`

**Problem:**
As AEGIS developed across phases (Phase 1A → 1B → 2A → Stage 9 → Stage 10 → Stage 11 → Stage 12), new intelligence columns were added incrementally. Analysts were running live databases. Any migration approach that drops or recreates tables would destroy live data.

**Options Considered:**
1. Manual migration scripts (Alembic, Flyway, etc.)
2. Drop-and-recreate on startup with data export/import
3. `ensure_columns()`: ADD COLUMN with IF NOT EXISTS guard on every startup *(selected)*

**Decision:**
`ensure_columns()` runs at every `Database.__init__()`. It queries `PRAGMA table_info(signals)` to get current columns, then adds any missing columns with `ALTER TABLE ... ADD COLUMN ... DEFAULT ...`.

**Reason:**
- Safe to run against any existing database — only adds, never drops or modifies
- All new columns have safe defaults so existing rows are unaffected by the addition
- No separate migration scripts to track, version, or run
- Transparent: readable inline in `database.py` without consulting external migration state

**Tradeoffs Accepted:**
- `ensure_columns()` grows over time as a long list of conditional adds
- No mechanism to remove deprecated columns (they accumulate)
- No schema versioning — cannot detect "this DB was last updated at Stage 9" vs "this DB has all Stage 12 columns"

**Implementation:**
```python
def ensure_columns(self):
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(signals)")}
    with conn:
        if "column_name" not in existing:
            conn.execute("ALTER TABLE signals ADD COLUMN column_name TYPE DEFAULT value")
```
Currently covers: `is_deleted`, `claims`, `category`, `source_type`, `source_role`, all AEGIS intelligence columns, `tracked`, `title_norm`, `source_orientation`, `editorial_role`, `reliability_tier`.

**Outcome:** *(confirmed)* All schema phases have been successfully applied to the live database without data loss.

**Lessons Learned:** New columns must always be added in `ensure_columns()`, never in `ensure_tables()`. Adding a column in `ensure_tables()` only affects new databases; `ensure_columns()` applies to both new and existing.

**Related Files:** `backend/app/db/database.py`

---

## Section 3: Source Intelligence Decisions

---

### D-011
**Date:** Stage 10 (confirmed from comment: "Stage 10 Source Intelligence Model")
**Status:** Active
**Category:** Scoring / source credibility

**Title:** Source Weighting System

**Problem:**
The LLM assigns a `significance_raw` score (1–10) based on article content alone. It does not know whether the article came from AP Wire or a Reddit post. A Reddit post saying "War is starting" and an AP wire report saying "US Central Command confirms airstrike" could receive similar raw significance scores if their content is similar. This does not reflect real-world confidence levels.

**Options Considered:**
1. No weighting — treat all sources equally; let content drive significance
2. Hard filter — exclude low-credibility sources entirely
3. Multiplicative weight — source credibility multiplies the final significance score *(selected)*

**Decision:**
`source_weight` multiplies the deterministic significance score after all content-based scoring. Weights range from 0.35 to 1.25 based on `reliability_tier` × `editorial_role`.

**Reason:**
- Hard filtering discards potentially important information from low-credibility sources. A Reddit post about a local emergency is still useful signal even if its confidence is lower.
- Multiplicative weighting preserves the information while calibrating the analyst's attention proportional to source credibility
- The same event reported by AP (Tier 1) vs. Reddit (Tier 4) produces proportionally different significance scores, which correctly surfaces the AP report higher in sorted views

**Tradeoffs Accepted:**
- A genuinely significant story from a low-tier source will be scored lower than the same story from a high-tier source, even if it breaks first
- Source classification requires ongoing curation — misclassified sources produce incorrect weights
- Weights are applied uniformly to all content from a source, regardless of individual article quality

**Implementation:**
`pipeline.py::_compute_source_weight()`. Stage 10 path: `tier_weight × editorial_role_weight`, clamped to [0.35, 1.25]. Legacy path (when `reliability_tier` is absent): `_SOURCE_ROLE_WEIGHTS` dict lookup with 0.70 default. Applied in `score_item()`: `significance_score = min(penalized × source_weight, 1.0)`.

**Outcome:** *(confirmed)* High-tier sources rank proportionally higher in significance-sorted views. Reddit signal is preserved but not elevated above wire service reporting.

**Lessons Learned:** Source weighting is the final multiplier in the scoring formula, not an additive component. This means a high-significance story from a very low-tier source still surfaces — it is just ranked lower. The analyst retains visibility into all signals regardless of source tier.

**Related Files:** `backend/app/core/pipeline.py`, `config/rss_sources.json`, `config/NewsSources.md`

---

### D-012
**Date:** Stage 10 (confirmed)
**Status:** Active
**Category:** Source classification

**Title:** Reliability Tier Model (1–4)

**Problem:**
Sources needed to be classified in a way that captures verification confidence and editorial independence in a single value that could be used as a scoring multiplier.

**Options Considered:**
1. Binary: trusted / untrusted
2. Percentage: 0–100 reliability score per source (requires too much per-source judgment)
3. Four-tier model *(selected)*: Tier 1 (wire/broadcast), Tier 2 (established reporting), Tier 3 (partisan/analysis), Tier 4 (watchlist/social)

**Decision:**
Four tiers. Tier multipliers: 1.15 / 1.00 / 0.75 / 0.45.

**Reason:**
- Four tiers are enough granularity to reflect meaningful confidence differences without requiring granular per-source judgment
- The tier multipliers create meaningful but not extreme differences: a Tier-1 story at a given raw significance score will score 2.56× higher than the same story from a Tier-4 source (1.15 / 0.45)
- The model separates two distinct concepts: verification confidence (does this outlet check facts?) and editorial independence (is this outlet influenced by partisan or state interests?)

**Tradeoffs Accepted:**
- Sources within a tier are treated equally despite real quality variance within tiers
- Tier assignment requires editorial judgment and may become outdated as outlets change
- The model does not account for per-story quality — a Tier-2 outlet's exceptional investigation gets the same weight as its filler content

**Implementation:**
`config/rss_sources.json` per-source `"reliability_tier": 1|2|3|4`. `pipeline.py::_TIER_WEIGHTS: {1: 1.15, 2: 1.00, 3: 0.75, 4: 0.45}`.

**Outcome:** *(confirmed)* Produces meaningful differentiation in significance scores between wire service coverage and social media coverage of the same event.

**Lessons Learned:** New sources added to `rss_sources.json` without a `reliability_tier` field fall back to the legacy `source_role` weight (0.70 default). Always assign a tier to new sources.

**Related Files:** `backend/app/core/pipeline.py`, `config/rss_sources.json`, `config/NewsSources.md`

---

### D-013
**Date:** Stage 10 (confirmed)
**Status:** Active
**Category:** Source classification

**Title:** Editorial Orientation Model (center/left/right/watchlist)

**Problem:**
Source credibility weighting handles verification confidence, but does not address the editorial framing dimension. Knowing that a story is covered by sources across the political spectrum is different from knowing that only one political orientation is covering it.

**Options Considered:**
1. No orientation tracking — treat all sources as editorially neutral
2. Binary: mainstream / fringe
3. Four-value orientation: center / left / right / watchlist *(selected)*

**Decision:**
`source_orientation`: `center` / `left` / `right` / `watchlist`. Used primarily in consensus scoring (corroboration bonuses) and displayed in the UI (orient pills on consensus cards).

**Reason:**
- Cross-spectrum corroboration is one of the strongest editorial confidence signals available without semantic analysis
- When AP (center), The Guardian (left), and Fox News (right) all lead with the same story, that convergence is meaningful regardless of how each outlet frames it
- Four values provide sufficient granularity while being assessable for every source without requiring per-article analysis

**Tradeoffs Accepted:**
- Orientation is a simplification of complex editorial behavior — outlets have nuanced positions that vary by topic area
- "Center" does not mean correct or unbiased — it means no consistent partisan lean, which is different
- Orientation can change over time; classification requires ongoing review

**Implementation:**
`config/rss_sources.json` per-source `"source_orientation": "center"|"left"|"right"|"watchlist"`. Used in `RadarDashboard.jsx::scoreCluster()` for corroboration bonuses and in `front_page_consensus.py` for `left_count`, `center_count`, `right_count` storage.

**Outcome:** *(confirmed)* Enables cross-spectrum corroboration detection in both client-side clustering and consensus engine scoring.

**Lessons Learned:** The `watchlist` category was important to add separately from `right` — state-narrative outlets (RT), fringe outlets, and social platforms are qualitatively different from consistently right-of-center established reporting outlets. They require a separate treatment that prevents them from contributing to corroboration bonuses.

**Related Files:** `backend/app/core/pipeline.py`, `config/rss_sources.json`, `config/NewsSources.md`, `frontend/src/pages/RadarDashboard.jsx`

---

### D-014
**Date:** Stage 10 (confirmed)
**Status:** Active
**Category:** Source classification

**Title:** Editorial Role Model (facts/mixed/analysis/narrative)

**Problem:**
Even within the same reliability tier, sources produce qualitatively different output. An investigative wire report and a commentary piece from the same outlet represent different levels of factual confidence. The reliability tier alone does not capture this.

**Options Considered:**
1. Reliability tier only — editorial role ignored
2. Separate role multiplier combined with tier weight *(selected)*

**Decision:**
`editorial_role`: `facts` (1.10) / `mixed` (1.00) / `analysis` (0.90) / `narrative` (0.75). Multiplied with `reliability_tier` weight to produce `source_weight`.

**Reason:**
- A Tier-2 outlet's investigative facts piece (`editorial_role: "facts"`) should outweigh the same outlet's op-ed (`editorial_role: "analysis"`) when both cover the same event
- The combined `tier × role` produces a more accurate confidence multiplier than either dimension alone
- `narrative` role (advocacy, social pulse, framing-heavy) gets the steepest discount because its primary value is pulse signal, not factual confidence

**Tradeoffs Accepted:**
- `editorial_role` is assigned per-source, not per-article — an outlet classified as `analysis` will have all its articles weighted the same
- Most outlets produce mixed content; the `mixed` classification is the appropriate default when role is ambiguous

**Implementation:**
`pipeline.py::_EDITORIAL_ROLE_WEIGHTS: {"facts": 1.10, "mixed": 1.00, "analysis": 0.90, "narrative": 0.75}`. Combined with tier weight and clamped: `min(max(tier_w × role_w, 0.35), 1.25)`.

**Outcome:** *(confirmed)* Produces appropriately differentiated scores between primary-fact sources and analysis/narrative sources at the same tier level.

**Related Files:** `backend/app/core/pipeline.py`, `config/rss_sources.json`, `config/NewsSources.md`

---

### D-015
**Date:** Stage 11 (inferred from 15-source count in front_page_sources.json)
**Status:** Active
**Category:** Consensus engine / source selection

**Title:** Front Page Source Selection Philosophy

**Problem:**
The Front Page Consensus engine needs a curated source list that can produce meaningful cross-spectrum editorial consensus detection. The question was how many sources, which ones, and how to distribute them across the editorial spectrum.

**Options Considered:**
1. Use the full 50+ RSS feed list — noisier, harder to interpret
2. Use only Tier-1 wire services — lacks orientation diversity
3. 15 curated sources, 5 per orientation *(selected)*

**Decision:**
15 sources: 5 left-leaning (Tier 2), 5 center (Tier 1–2), 5 right-leaning (Tier 2–3). AP and BBC are the only Tier-1 sources. This creates a symmetric orientation baseline.

**Reason:**
- Equal representation across orientations (5 left, 5 center, 5 right) means orientation counts are directly comparable without normalization
- 15 sources generates enough headline volume for meaningful clustering without creating an unmanageable data set
- Including both Tier-1 sources (AP, BBC) as center sources anchors the consensus scoring — their presence adds a meaningful Tier-1 bonus
- This list is static and curated, not dynamically assembled from the main RSS feed list — this separation is intentional (see D-016)

**Tradeoffs Accepted:**
- Static list requires manual curation as outlets change editorial character over time
- 5 sources per orientation means a single dead feed shifts the balance
- Current right-leaning sources are mostly Tier 3, which means full-spectrum corroboration (left + center + right) earns the maximum orientation bonus but the cluster scores will not exceed the client-side reliability caps unless Tier-1/2 sources are also present

**Implementation:**
`config/front_page_sources.json`. 15 entries with `name`, `url`, `orientation`, `reliability_tier` fields only.

**Outcome:** *(confirmed)* 15-source list produces meaningful orientation spread counts in consensus results. Full-spectrum (left + center + right) corroboration events are rare and genuinely significant when detected.

**Related Files:** `config/front_page_sources.json`, `tasks/front_page_consensus.py`

---

## Section 4: Consensus Engine Decisions

---

### D-016
**Date:** Stage 11 (confirmed from file comment: "Phase: Stage 11")
**Status:** Active
**Category:** Architecture / separation of concerns

**Title:** Separate Consensus Engine From Main RSS Pipeline

**Problem:**
The main RSS pipeline answers: "What are the most significant news items in the current feed cycle?" The Front Page Consensus answers: "What are editors across the political spectrum choosing to lead with right now?" These are different questions with different source requirements, different algorithms, and different output formats.

**Options Considered:**
1. Integrate consensus detection into the main RSS scan as a post-processing step
2. Build as a separate scan with its own route, state, source list, table, and engine *(selected)*

**Decision:**
Completely separate system. Own route (`/consensus-scan`), own scan state dict, own source list (`front_page_sources.json`), own database table (`front_page_consensus`), own engine (`tasks/front_page_consensus.py`), own UI tab.

**Reason:**
- The consensus engine makes no LLM calls — it is pure RSS fetch + deterministic text matching. Integrating it with the LLM pipeline would couple two things that share no logic.
- The source lists are intentionally different: consensus uses 15 curated orientation-balanced sources; the main scan uses 50+ sources covering diverse topic categories
- The output (cluster cards with orientation counts and consensus scores) is structurally different from individual signal cards
- Independent scan states allow both scans to run concurrently without blocking each other
- Keeping them separate allows the consensus engine to evolve independently

**Tradeoffs Accepted:**
- Two distinct scan flows for the analyst to understand
- More code: separate route handlers, separate state management, separate frontend polling loops
- Consensus results are stored in a separate table from signals, so they cannot be queried together

**Implementation:**
`radar.py`: separate `consensus_scan_lock`, `consensus_scan_state`, `_run_consensus_background()`. `front_page_consensus.py`: completely independent module. `front_page_consensus` table: separate from `signals` table.

**Outcome:** *(confirmed)* Both scan types run independently without interference. The consensus engine has been modified (Stage 11 → Stage 12 clustering) without affecting the main pipeline.

**Related Files:** `tasks/front_page_consensus.py`, `backend/app/api/routes/radar.py`, `sources/front_page.py`, `backend/app/db/database.py`

---

### D-017
**Date:** Stage 13 (inferred from "Stage 13: Consensus Archive" comment in RadarDashboard.jsx)
**Status:** Active
**Category:** Storage / temporal analysis

**Title:** Consensus Archive

*(See D-009 for the storage decision. This entry covers the editorial rationale.)*

**Problem:**
The analyst's value question for consensus scans is temporal: "Is this story growing in editorial attention or fading? What changed between this morning's front pages and this afternoon's?" A single-latest-result system cannot answer this.

**Decision:**
Every scan creates a permanent snapshot identified by a unique `scan_id`. The UI exposes an archive browser. The analyst can compare any two snapshots.

**Reason:**
The editorial consensus captured at 8:00 AM and 2:00 PM on the same day may show a story rising from `monitored` to `confirmed` tier, or a story that was `confirmed` in the morning dropping off entirely by afternoon. This temporal pattern is itself intelligence.

**Outcome:** *(confirmed)* Archive browser implemented and functional. Snapshots accumulate indefinitely.

**Lessons Learned:** See FA-002 (Consensus Without Archive). The overwrite-latest approach made every new scan permanently destroy the previous state. This was recognized as a loss of institutional memory within the scanning workflow itself.

**Related Files:** `backend/app/db/database.py`, `backend/app/api/routes/radar.py`, `frontend/src/lib/api.js`, `frontend/src/pages/RadarDashboard.jsx`

---

### D-018
**Date:** Stage 12 (confirmed from file comment: "Phase: Stage 12 (Event Identity Refinement)")
**Status:** Active — critical
**Category:** Consensus engine / clustering

**Title:** Event Identity Clustering (Stage 12)

**Problem:**
Stage 11's clustering algorithm merged headlines by any shared significant word. This produced mega-clusters where unrelated stories merged because they shared the name of a prominent political figure.

**Decision:**
Stage 12 replaces any-word overlap with event-identity matching:
- Strip high-salience entities from the comparison set
- Require 2+ shared event words, OR 1 anchor word + same context domain, to merge
- Never merge if either headline has zero event words after stripping

**Reason:**
"Trump" appeared in ~80% of political headlines. The Stage 11 algorithm treated "Trump" as a clustering signal when it is actually a clustering anti-signal — its presence in two headlines tells us nothing about whether they cover the same event.

**Outcome:** *(confirmed)* See FA-001 for the full failed-approach history.

**Lessons Learned:** The key insight is that **high-frequency entities carry zero event-identity signal**. A word that appears in 80% of headlines cannot be used to distinguish between headlines.

**Related Files:** `tasks/front_page_consensus.py`

---

### D-019
**Date:** Stage 12 (confirmed)
**Status:** Active — critical
**Category:** Consensus engine / clustering

**Title:** High-Salience Entity Exclusion (`_HIGH_SALIENCE`)

**Problem:**
Named entities that appear in nearly every political headline (heads of state, generic government terms) were causing unrelated stories to cluster together because they shared these entities.

**Decision:**
The `_HIGH_SALIENCE` frozenset contains names and terms stripped from the comparison set before clustering: `trump`, `biden`, `harris`, `obama`, `president`, `congress`, `senate`, `white`, `house`, `administration`, `government`, `federal`, `national`, `american`, `america`, `united`, `states`, `official`, `officials`, `political`, `policy`, and others.

**Reason:**
These entities are high-frequency precisely because they are central to most political coverage. Their presence is the baseline state, not a distinguishing signal. Removing them from the comparison set forces the clustering algorithm to identify stories by the specific event-level words that actually differentiate them.

**Tradeoffs Accepted:**
- A story where the president is the unique event protagonist (e.g., a presidential health emergency) may be harder to cluster because the entity that makes it distinctive is in the blocklist
- The blocklist requires curation and will not be complete for all contexts

**Implementation:**
`front_page_consensus.py::_HIGH_SALIENCE: frozenset({...})`. Applied in `_event_words(title)`: `frozenset(extract_words(title) - _HIGH_SALIENCE)`.

**Outcome:** *(confirmed)* Eliminates the primary cause of over-clustering while preserving genuine event-level similarity detection.

**Lessons Learned:** Do not remove entries from `_HIGH_SALIENCE` because they "seem like they should be useful clustering signals." They are in the blocklist because they proved to be harmful clustering signals.

**Related Files:** `tasks/front_page_consensus.py`

---

### D-020
**Date:** Stage 11/12 (inferred)
**Status:** Active
**Category:** Consensus engine / scoring

**Title:** Multi-Factor Consensus Scoring

**Problem:**
A naive count-based consensus score (5 sources = high consensus) fails because it does not account for whether those 5 sources represent genuine cross-spectrum agreement or just 5 outlets from the same partisan orientation.

**Decision:**
Multi-factor scoring combining: source breadth as baseline, orientation spread bonus, and Tier-1 presence bonus.

**Reason:**
Three Fox News affiliates and two Daily Wire-adjacent outlets covering the same story is not cross-spectrum consensus — it is one editorial ecosystem amplifying a story. Genuine consensus requires corroboration across orientation lines. The multi-factor model distinguishes between these cases.

**Outcome:** *(confirmed)* See FA-004 for the failed simple-counting predecessor.

**Related Files:** `tasks/front_page_consensus.py`

---

### D-021
**Date:** Stage 11/12 (inferred)
**Status:** Active
**Category:** Consensus engine / scoring

**Title:** Orientation Spread Bonus

**Problem:**
The value of a consensus signal comes from its cross-spectrum nature. A story covered by AP + CNN + NYT (all center/left) is less certain than a story covered by AP + NYT + Fox News (center + left + right).

**Decision:**
Orientation bonuses in `front_page_consensus.py::_score_consensus()` (Python):
- left + center + right all present: +0.30
- (left + center) or (center + right): +0.15
- left + right without center: +0.05
- single orientation only: no bonus

Orientation bonuses in `RadarDashboard.jsx::scoreCluster()` (JavaScript, for client-side live-feed clustering):
- left + center + right all present: +0.20
- center + one of left/right: +0.10
- left + right without center: no bonus
- single orientation only: no bonus

**Reason:**
When outlets with fundamentally different editorial agendas and audiences all choose to lead with the same story, that convergence is the strongest available editorial consensus signal. The bonus is proportional to the degree of spectrum coverage achieved.

**Tradeoffs Accepted:**
- Left + right without center receives a minimal bonus (+0.05) in the Python engine rather than the same as center-inclusive pairs, because this pattern more often reflects contested framing than genuine factual consensus. The JS client-side scorer gives left+right without center no bonus at all.
- The two systems use different bonus magnitudes because they operate on different scales and source sets

**Implementation:**
`RadarDashboard.jsx::scoreCluster()` and `front_page_consensus.py::_score_consensus()`. Both implement orientation spread logic but with different magnitude values.

**Outcome:** *(confirmed)* Full-spectrum corroboration events are rare and score substantially higher than single-orientation coverage.

**Related Files:** `frontend/src/pages/RadarDashboard.jsx`, `tasks/front_page_consensus.py`

---

### D-022
**Date:** Stage 11/12 (inferred)
**Status:** Active
**Category:** Consensus engine / scoring

**Title:** Reliability Caps to Prevent Watchlist-Only Front-Paging

**Problem:**
Without reliability caps, a story covered by five Reddit communities or five state-narrative outlets could technically achieve a high consensus score based on volume, despite having no verified wire-service corroboration.

**Decision:**
- All Tier-4 (watchlist/social) sources: score capped at 0.59 (never reaches `front_page` tier)
- All Tier-3+ (no Tier-1 or Tier-2): score capped at 0.79 (never reaches `front_page` tier)
- Applied after all bonuses are computed

**Reason:**
Social and watchlist sources generate real signal about public attention and narrative, but their editorial confidence ceiling is fundamentally lower than established reporting. The caps prevent social amplification from masquerading as editorial consensus.

**Implementation:**
Currently implemented only in `RadarDashboard.jsx::scoreCluster()` (client-side live-feed clustering). The reliability caps were removed from `front_page_consensus.py::_score_consensus()` — the Python consensus engine no longer applies them. The consensus engine's tier thresholds (`confirmed`/`elevated`/`monitored`/`noise`) provide sufficient differentiation at the current source count of 15.

`RadarDashboard.jsx`: `allTier4` (all signals ≥ Tier 4) caps at 0.59; `allLowReliability` (all signals ≥ Tier 3) caps at 0.79.

**Outcome:** *(confirmed)* Watchlist-heavy clusters are correctly capped below front-page tier in client-side clustering regardless of volume. The Python consensus engine achieves similar differentiation through its tier-bonus structure.

**Related Files:** `tasks/front_page_consensus.py`, `frontend/src/pages/RadarDashboard.jsx`

---

## Section 5: Failed Approaches

---

### FA-001
**Date:** Stage 11 (confirmed from code comment: "Stage 11 merged headlines on ANY 1 shared word")
**Status:** Superseded by Stage 12
**Category:** Consensus engine / clustering

**Title:** One-Word Clustering (Stage 11)

**What Was Tried:**
Headlines were clustered by any single shared significant word (4+ characters, not in stop list). Two headlines sharing any meaningful word were merged into the same cluster.

**Why It Failed:**
High-frequency political entities — especially "trump" — appeared in approximately 80% of all political headlines. The algorithm treated "trump" as a clustering signal when it was in reality a clustering anti-signal. The result was a single massive cluster containing: an Iran military strike story, an E. Jean Carroll verdict story, a DOJ antitrust investigation story, 2024 poll data, and immigration rulings — all merged because they each mentioned "trump" in different contexts. The cluster topic label read "trump iran strikes" even though Trump had no involvement in the Iran story.

**What Replaced It:**
Stage 12 (D-018). The `_HIGH_SALIENCE` blocklist (D-019) strips high-frequency entities before comparison. `_should_merge()` requires 2+ shared event words OR 1 anchor word within the same context domain.

**Lesson:**
A word that appears in the majority of headlines cannot be used as a clustering signal. High frequency and clustering utility are inversely related for entity names.

**Related Files:** `tasks/front_page_consensus.py`

---

### FA-002
**Date:** Stage 11 (inferred — archive was added in Stage 13)
**Status:** Superseded by archive model
**Category:** Storage

**Title:** Consensus Without Archive (Overwrite-Latest)

**What Was Tried:**
Each new Front Page Consensus scan overwrote the previous results. Only the latest scan was stored and accessible.

**Why It Failed:**
The analyst's primary use for consensus scanning is temporal comparison — understanding how editorial priorities shift throughout the day. The overwrite-latest approach destroyed the previous state on every scan, making it impossible to answer "what changed since this morning?" Once overwritten, historical consensus data was permanently lost and unrecoverable.

**What Replaced It:**
Stage 13 archive model (D-009). Each scan generates a unique `scan_id`. All scans are preserved. The UI provides an archive browser for comparing historical snapshots.

**Lesson:**
For any system that captures a time-series snapshot of external state (what front pages look like right now), the archive model should be the default. Overwrite-latest destroys institutional memory at every scan.

**Related Files:** `backend/app/db/database.py`, `tasks/front_page_consensus.py`

---

### FA-003
**Date:** Early development (inferred from `liveOnly`/`trackedOnly` query params existing as explicit design)
**Status:** Superseded
**Category:** UX / workflow

**Title:** Library and Live Feed Mixing

**What Was Tried:**
All signals (tracked=0 and tracked=1) were fetched together into a single list. The user could filter between saved and unsaved items using a toggle.

**Why It Failed:**
The Live Feed and the Report Library serve fundamentally different analyst mental models. The Live Feed is an inbox requiring triage action. The Library is a curated archive requiring review and reference. Mixing them created constant visual clutter — the analyst had to mentally filter out already-saved items while triaging new ones. Bulk operations on the live feed risked accidentally affecting library items. The distinction between "new item to evaluate" and "item I already decided was important" was lost.

**What Replaced It:**
Hard separation. Two distinct views (`activeView === "live"` vs `activeView === "library"`). Each view fetches with `liveOnly=true` or `trackedOnly=true` exclusively. Switching views triggers a fresh fetch with the appropriate filter.

**Lesson:**
When two categories of data represent fundamentally different analyst states of mind, they must not share the same view. Filtering is insufficient when the distinction is semantic, not just visual.

**Related Files:** `frontend/src/pages/RadarDashboard.jsx`, `backend/app/api/routes/radar.py`, `backend/app/db/database.py`

---

### FA-004
**Date:** Stage 11 (inferred from multi-factor scoring being the current state)
**Status:** Superseded
**Category:** Consensus engine / scoring

**Title:** Simple Source Counting for Consensus Score

**What Was Tried:**
Consensus score was computed as `source_count / total_sources` — purely based on how many sources covered the story. More sources = higher score.

**Why It Failed:**
Volume without quality produced misleading results. A story covered by five Tier-3 right-oriented outlets (e.g., five Daily Wire-adjacent sites) would outscore a story covered by AP + BBC + NPR — three Tier-1/2 center sources with high editorial independence. Partisan amplification within one editorial ecosystem was scoring higher than genuine cross-spectrum corroboration. This was precisely backwards from what "editorial consensus" means.

**What Replaced It:**
Multi-factor consensus scoring (D-020) with orientation spread bonuses (D-021). Source count remains the baseline (`min(source_count/10, 1.0) × 0.40`), but orientation diversity and tier quality determine the final score.

**Lesson:**
Source count measures volume. Editorial consensus measures independence-weighted convergence. These are different things. Optimizing for count alone rewards echo chambers.

**Related Files:** `tasks/front_page_consensus.py`

---

### FA-005
**Date:** Pre-Stage 5 (inferred from the comment "the old round-robin" in run_collectors.py)
**Status:** Superseded
**Category:** Scan pipeline / intake

**Title:** Equal Source Quotas (Simple Round-Robin)

**What Was Tried:**
RSS sources were processed in a simple round-robin with equal slots per source regardless of category or content.

**Why It Failed:**
With 50+ configured feeds including many technology, sports, and entertainment sources, equal round-robin gave approximately equal processing slots to AP covering a Gaza airstrike and TechCrunch covering a gadget review. The 60 LLM slots were consumed roughly proportionally by volume, not by importance. A major geopolitical escalation from Al Jazeera could be processing slot 55 while sports and entertainment stories consumed the early slots.

**What Replaced It:**
Pre-AI prioritization (`pre_score_raw_post()` in Stage 5A) combined with per-category quota enforcement (`_CATEGORY_QUOTA` dict). All collected posts are sorted by deterministic heuristic score before the round-robin begins. Category quotas ensure geopolitical and investigative sources earn more LLM slots than tech/sports sources.

**Lesson:**
Fairness-by-volume (equal slots per source) is not the same as fairness-by-importance. A tool designed to surface the most significant signals must allocate its scarce processing budget proportional to content importance, not content volume.

**Related Files:** `tasks/run_collectors.py`

---

### FA-006
**Date:** Client-side clustering (inferred from the comment in RadarDashboard.jsx explaining the threshold change)
**Status:** Superseded
**Category:** Client-side clustering

**Title:** Fixed Threshold of 2 Shared Words for All Pairs

**What Was Tried:**
Client-side clustering in `RadarDashboard.jsx` required 2+ shared significant words to merge any two signals, regardless of their individual significance scores.

**Why It Failed:**
High-significance geopolitical stories frequently share fewer distinctive words than lower-significance stories simply because they involve specific named locations and actors that are less common in the broader corpus. The headline "Iran strikes Kuwait" and "Central Command responds to Iran attack" share only "iran" as a significant overlap word — but these are clearly the same event. The fixed threshold of 2 prevented these pairs from ever clustering, isolating them as separate singleton items despite representing the same developing story.

**What Replaced It:**
Adaptive threshold: when both signals have `significance_score ≥ 0.55`, the threshold drops to 1 shared word. This narrow window (only high-significance pairs get the lowered threshold) preserves protection against spurious low-significance clustering while correctly uniting related high-significance stories.

**Lesson:**
A fixed threshold that works well for average-significance content may be wrong for the most important content. High-significance stories often use more specific, less repetitive vocabulary — which means shared-word counts are lower even when the stories are clearly related.

**Related Files:** `frontend/src/pages/RadarDashboard.jsx`

---

## Section 6: UI and Workflow Decisions

---

### D-023
**Date:** Early development (inferred)
**Status:** Active
**Category:** UI / workflow

**Title:** Separate Live Feed and Report Library as Distinct Views

**Problem:**
Signals in the system exist in two fundamentally different states: newly collected items awaiting analyst triage (`tracked=0`), and items the analyst has deliberately saved (`tracked=1`). How to present these to the analyst?

**Decision:**
Two hard-separated views with distinct fetch calls. "Live Feed" fetches `liveOnly=true`. "Report Library" fetches `trackedOnly=true`. Items cannot appear in both views simultaneously.

**Reason:**
The two views represent different analyst tasks: Live Feed is triage (evaluate and decide); Library is reference (review what was saved). Mixing them creates cognitive context-switching during triage and makes bulk operations on the Live Feed risky.

**Outcome:** *(confirmed)* See FA-003 for the predecessor. Separation is clean and functional.

**Related Files:** `frontend/src/pages/RadarDashboard.jsx`, `frontend/src/lib/api.js`, `backend/app/api/routes/radar.py`

---

### D-024
**Date:** Development (inferred from comment in RadarDashboard.jsx: "Avoids window.confirm(), which browsers can suppress")
**Status:** Active
**Category:** UI / interaction safety

**Title:** Inline Delete Confirmation Instead of `window.confirm()`

**Problem:**
Delete is a permanent, irreversible action. It requires confirmation. The question was how to implement that confirmation.

**Options Considered:**
1. `window.confirm()` dialog — native browser dialog
2. Modal overlay — separate confirmation dialog component
3. Inline confirm: card re-renders with confirm/cancel buttons *(selected)*

**Decision:**
First click on Delete sets `pendingDeleteId = item.id`, causing the card to re-render showing "Delete this signal?" + "Yes, Delete" / "Cancel" buttons inline. Second click on "Yes, Delete" fires the actual delete API call.

**Reason:**
`window.confirm()` can be permanently suppressed by users in Chrome settings, and may be blocked by some browser configurations. Once suppressed, delete becomes a one-click irreversible action with no confirmation. Modal overlays add component complexity and require a separate render tree.

Inline confirmation keeps the confirmation in context with the specific card being deleted, is impossible to suppress, and requires no additional component infrastructure.

**Tradeoffs Accepted:**
- Card layout shifts slightly when confirm state is active (buttons appear inline)
- User must find and click cancel if they change their mind — can't press Escape to cancel

**Implementation:**
`RadarDashboard.jsx`: `pendingDeleteId` state, `handleDelete()` sets it, `handleConfirmDelete()` fires the API call, `handleCancelDelete()` clears it. `SignalCard.jsx` renders the confirm/cancel buttons when `isPendingDelete` prop is true.

**Outcome:** *(confirmed)* Reliable two-step delete flow that cannot be bypassed by browser settings.

**Related Files:** `frontend/src/pages/RadarDashboard.jsx`, `frontend/src/components/SignalCard.jsx`

---

### D-025
**Date:** Development (inferred)
**Status:** Active
**Category:** UI / workflow

**Title:** Save to Library as Explicit Analyst Action (Not Automatic)

**Problem:**
Should the system automatically save high-significance signals to the Library, or require explicit analyst action?

**Decision:**
Library membership is always an explicit analyst action. No automatic promotion. The "Save to Library" button appears on live feed cards only.

**Reason:**
Automatic promotion would undermine the Library's function as a curated collection reflecting the analyst's editorial judgment. If high-significance items are auto-saved, the Library becomes a machine-generated list rather than an analyst-curated archive. The analyst's act of saving is itself information — it records what the analyst considered worth keeping.

**Tradeoffs Accepted:**
- Analyst must manually review and save important items; there is no automatic capture
- Items that the analyst does not see (e.g., during a high-volume scan period) may not be saved even if they are significant

**Outcome:** *(confirmed)* Library remains a clean curated collection that reflects analyst judgment.

**Related Files:** `frontend/src/pages/RadarDashboard.jsx`, `frontend/src/components/SignalCard.jsx`

---

### D-026
**Date:** Stage 13 (inferred)
**Status:** Active
**Category:** UI / consensus

**Title:** Consensus Archive Access via Archive Browser Tab

**Problem:**
The consensus archive stores historical scans. How should the analyst navigate between them?

**Decision:**
"Archive" tab in the dashboard. Opening the tab fetches the list of all historical scan IDs with timestamps and cluster counts. Clicking a snapshot loads its cluster data into the consensus display area.

**Reason:**
The archive is secondary functionality — most visits to the Consensus tab will be to see the latest scan. The archive should be accessible without cluttering the primary consensus view. A separate expandable panel (now implemented as a tab) provides clear separation.

**Implementation:**
`showArchive` state in `RadarDashboard.jsx`. `handleToggleArchive()` fetches snapshot list. `handleLoadSnapshot(scanId)` loads a specific snapshot. "View Current Scan" button returns to the latest.

**Outcome:** *(confirmed)* Archive is accessible without interfering with the default latest-scan view.

**Related Files:** `frontend/src/pages/RadarDashboard.jsx`, `frontend/src/lib/api.js`

---

### D-027
**Date:** Stage 11 (inferred from separation in UI)
**Status:** Active
**Category:** UI / workflow separation

**Title:** Front Page Consensus Scan Separate From "Refresh Reports"

**Problem:**
Should "Refresh Reports" (full RSS scan) and "Scan Front Pages" (consensus scan) be the same button or separate?

**Decision:**
Completely separate buttons, separate scan states, separate progress indicators, separate results views.

**Reason:**
The two scans have different purposes, different sources, different outputs, and different run times. A user pressing "Refresh Reports" wants new signal items in their feed. A user pressing "Scan Front Pages" wants to see what editors are leading with. These are independent analyst needs that should not be coupled. Running one should never block or trigger the other.

**Outcome:** *(confirmed)* Both scans are independently controllable and can run concurrently.

**Related Files:** `frontend/src/pages/RadarDashboard.jsx`, `backend/app/api/routes/radar.py`

---

## Section 7: Development Process Decisions

---

### D-028
**Date:** Documentation phase (confirmed from AEGIS_DEVELOPER_RULES.md)
**Status:** Active — process rule
**Category:** AI collaboration

**Title:** Full File Return Requirement

**Problem:**
When an AI assistant modifies a file, it may return a partial excerpt, a diff, or a snippet with surrounding context rather than the complete updated file. This forces the developer to manually merge the AI's changes with the original, which introduces human error.

**Decision:**
Any AI assistant working on this project must return the complete updated file when making modifications. No partial returns, no diffs, no placeholders.

**Reason:**
The developer replaces the old file with the AI's output. A partial output produces a broken file. The error rate of manual merging under time pressure across multiple files is too high to accept.

**Outcome:** *(confirmed)* Established as a non-negotiable rule in `AEGIS_DEVELOPER_RULES.md` Section 2.

---

### D-029
**Date:** Documentation phase (confirmed)
**Status:** Active — process rule
**Category:** AI collaboration

**Title:** No Feature Inference Rule

**Problem:**
AI assistants have a tendency to add adjacent features they believe would logically complete a request. These inferred additions are untested, may conflict with planned development, and create scope that was not agreed upon.

**Decision:**
AI assistants working on AEGIS must implement exactly what was requested, nothing more. Inferred features require explicit confirmation before implementation.

**Reason:**
Project history includes cases where unrequested UI buttons were added with no persistence layer, creating broken affordances. The cost of removing unrequested code is higher than the cost of asking a clarifying question.

**Outcome:** *(confirmed)* Established as a rule in `AEGIS_DEVELOPER_RULES.md` Section 3.

---

### D-030
**Date:** Documentation phase (confirmed)
**Status:** Active — process rule
**Category:** AI collaboration / maintenance

**Title:** Documentation-First Philosophy

**Problem:**
As the system evolves across phases and stages, knowledge about why decisions were made accumulates in the minds of the developer and in git commit messages. An AI assistant reading the code at a future date has none of this context.

**Decision:**
Maintain three documentation documents in parallel with the codebase: `AEGIS_STORAGE_AND_STRUCTURE.md` (architecture), `AEGIS_AI_HANDOFF_SOP.md` (operating procedures), `AEGIS_DEVELOPER_RULES.md` (development standards), and `AEGIS_DECISION_LOG.md` (this document). Update documentation when architecture changes.

**Reason:**
An AI assistant that reads these documents before touching code is substantially less likely to inadvertently undo a deliberate design decision. The documentation converts implicit knowledge into explicit, searchable institutional memory.

**Related Files:** `docs/`

---

### D-031
**Date:** Development (confirmed from AEGIS_DEVELOPER_RULES.md Section 9)
**Status:** Active — process rule
**Category:** Version control

**Title:** Checkpoint Commit Workflow

**Problem:**
When an AI assistant makes a large change that introduces a regression, recovery requires undoing changes across multiple files. Without a checkpoint commit, the pre-change state is inaccessible.

**Decision:**
Before any significant AI-assisted change, create a checkpoint commit:
```powershell
git add -A
git commit -m "checkpoint: before [description of planned change]"
```

**Reason:**
Checkpoint commits make recovery deterministic: `git checkout` to the checkpoint is always possible. Without checkpoints, recovery requires manually undoing multi-file changes under time pressure — an error-prone process that may itself introduce new problems.

**Outcome:** Established as a non-negotiable rule in `AEGIS_DEVELOPER_RULES.md` Section 9.

---

### D-032
**Date:** Documentation phase (confirmed from AEGIS_AI_HANDOFF_SOP.md Section 6)
**Status:** Active — process rule
**Category:** Maintenance awareness

**Title:** Critical File Identification

**Problem:**
Not all files have equal blast radius if incorrectly modified. Files like `database.py`, `front_page_consensus.py`, `RadarDashboard.jsx`, `api.js`, and `rss_sources.json` have disproportionate impact on system behavior.

**Decision:**
Formally document which files are "critical" — meaning: mistakes here can break behavior in ways that are hard to diagnose — and catalog the specific failure modes for each.

**Reason:**
An AI assistant that knows `api.js` path strings must exactly match `radar.py` route paths will check that agreement. One that does not know this will change route paths in one place without checking the other, producing 404 errors that silently break UI buttons.

**Outcome:** Section 6 of `AEGIS_AI_HANDOFF_SOP.md` and Section 9 of `AEGIS_STORAGE_AND_STRUCTURE.md` both document critical files with specific failure mode tables.

**Related Files:** `docs/AEGIS_AI_HANDOFF_SOP.md`, `docs/AEGIS_STORAGE_AND_STRUCTURE.md`

---

## Section 8: Lessons That Cost Time

This section documents specific lessons learned through development friction. Each lesson represents a failure mode that was encountered and resolved.

---

**L-001: Do not merge headlines by public figure names.**

High-frequency entity names (political figures, generic government terms) appear in too many headlines to carry event-identity signal. "Trump" alone merging every political headline into one cluster was the root cause of Stage 11's failure. Strip high-salience entities before any clustering comparison. See FA-001, D-018, D-019.

---

**L-002: Do not overwrite historical consensus scan data.**

Each consensus scan captures a moment in editorial time. Overwriting it on the next scan permanently destroys the ability to compare editorial priorities across time. Archive every scan with a unique ID. See FA-002, D-009, D-017.

---

**L-003: Do not mix analyst workflow states (triage vs. archive).**

The Live Feed and the Report Library represent different analyst mental models. Mixing them into a single view creates cognitive overhead during triage and makes bulk operations risky. Hard-separate them with distinct fetch calls. See FA-003, D-023.

---

**L-004: Do not allow soft-deleted items to re-import.**

When an analyst deletes a signal, their decision must persist. Without dedup protection, the same story returns in the next scan. The `is_deleted` flag must be checked by the `title_norm` dedup query, not just by the display filter. See D-006, D-007.

---

**L-005: Do not trust source count alone as a consensus signal.**

Volume of coverage is not the same as editorial consensus. Five outlets from the same partisan ecosystem amplifying a story is not cross-spectrum corroboration. Consensus scoring must account for orientation diversity and source tier. See FA-004, D-020, D-021.

---

**L-006: Do not hard-delete rows that serve as dedup anchors.**

The soft-delete design is not just about "undo" capability. Deleted rows are active participants in the dedup system via `title_norm`. Hard-deleting them removes their fingerprints from the blocklist, allowing the same stories to re-import. See D-007.

---

**L-007: Do not run inference on all collected items equally.**

With 50+ feeds and a 60-item LLM cap, equal round-robin processing distributes scarce inference budget proportional to volume rather than importance. Pre-score all items deterministically before the round-robin, then apply category quotas, so LLM slots go to the most SWAT-relevant content. See FA-005, D-005.

---

**L-008: Do not use `window.confirm()` for destructive actions.**

`window.confirm()` can be permanently suppressed by users in browser settings, converting a confirmed destructive action into an unconfirmed one-click action. Always implement inline confirmation flows. See D-024.

---

**L-009: Do not simplify clustering code without checking the failure history.**

The Stage 12 clustering algorithm in `front_page_consensus.py` appears over-engineered. It is the direct solution to Stage 11's over-merging failure. Simplifying it reproduces the failure. Always search the decision log before removing complexity from this file. See FA-001, D-018, D-019.

---

**L-010: Do not use a fixed word-overlap threshold for all significance levels.**

The same fixed threshold (2 shared words) that correctly prevents spurious merges for average-significance content may incorrectly prevent merges for the most significant content, where specific vocabulary is sparse. Apply an adaptive threshold for high-significance pairs. See FA-006.

---

**L-011: The port agreement across three files is a persistent source of bugs.**

Backend port, CORS origin, and frontend API base URL are configured in three separate files: `main.py`, `backend/app/app.py`, and `frontend/src/lib/api.js`. Any change to one that does not update all three produces silent failures. Always check all three when a port-related issue appears.

---

**L-012: New columns must go in `ensure_columns()`, not `ensure_tables()`.**

`ensure_tables()` only runs `CREATE TABLE IF NOT EXISTS` — it will not add a new column to a table that already exists. `ensure_columns()` runs `ALTER TABLE ADD COLUMN IF NOT EXISTS` on every startup. New columns added only to `ensure_tables()` will appear in fresh databases but silently be absent from existing databases. See D-010.

---

## Section 9: Open Questions

These items represent architectural questions that have not been resolved. They are documented here so that future work can build on the reasoning rather than starting from scratch.

---

**OQ-001: NEXIS-LOCAL Migration**
**Status:** Unresolved — future planning  
**Question:** When AEGIS is extended into NEXIS-LOCAL, which components migrate intact versus get rewritten? The source intelligence model, pipeline scoring engine, and database concepts are expected to survive. FastAPI routing, SQLite, and the single-process threading model may need to be replaced at scale.  
**Decision pending:** What is the minimum viable architecture change that enables multi-device access without requiring a full cloud rewrite?

---

**OQ-002: PostgreSQL Migration**
**Status:** Unresolved — contingent on OQ-001  
**Question:** At what point does the signals database require PostgreSQL? SQLite handles the current single-analyst load without issue. The migration trigger is likely: multi-device access, concurrent multi-process writes, or database size requiring full-text search performance.  
**Decision pending:** Define the size/load threshold that triggers migration evaluation.

---

**OQ-003: Advanced Trend Analysis**
**Status:** Unresolved — future feature  
**Question:** `trend_score` is reserved (always 0.0) for a future Phase 6 that requires social API data. What would meaningful trend scoring look like without social APIs? Could RSS publication velocity (same story appearing across multiple feeds within a short time window) serve as a proxy for trend detection?  
**Decision pending:** Define the data sources available for trend scoring that are consistent with the local-first architecture.

---

**OQ-004: Narrative Drift Detection**
**Status:** Unresolved — future feature  
**Question:** Currently each item is analyzed independently. A future enhancement would compare framing patterns across a 24-hour window — "how is the framing of story X changing across outlets over time?" This requires either storing framing vectors or running a cross-corpus comparison on stored `framing` fields.  
**Decision pending:** What is the minimum architecture change in the DB and pipeline that enables cross-item framing comparison without requiring an embedding store?

---

**OQ-005: Source Reputation Evolution**
**Status:** Unresolved — maintenance question  
**Question:** Source classifications (`reliability_tier`, `editorial_role`, `source_orientation`) in `rss_sources.json` are static. Outlets change their editorial character over time. Should there be a mechanism for updating source classifications based on observed behavior, or should classification remain a fully manual editorial judgment?  
**Decision pending:** Define the governance model for source classification updates.

---

**OQ-006: Dedup Retention Policy**
**Status:** Unresolved — maintenance question  
**Question:** Soft-deleted and tracked rows accumulate indefinitely as dedup anchors. At what database size does this become a storage concern? Should there be a retention policy that prunes old dedup records while preserving the fingerprints in a smaller dedicated table?  
**Decision pending:** Establish size monitoring and define a retention threshold.

---

**OQ-007: Front Page Source List Refresh**
**Status:** Unresolved — maintenance question  
**Question:** The 15 front-page consensus sources are hardcoded in `config/front_page_sources.json`. Some of these outlets may change their editorial orientation or reliability over time. How frequently should this list be reviewed and updated?  
**Decision pending:** Establish a review cadence for consensus source classification.

---

**OQ-008: Report Quality Improvements**
**Status:** Unresolved — future feature  
**Question:** The LLM prompt currently produces a fixed set of fields: topic, summary, framing, claims, signal_type, significance_raw, manipulation_risk, narrative_flags. Future improvements might include: named entity extraction, geographic tagging, confidence estimate from the LLM, or improved significance calibration for mid-range (4–6) items which appear under-differentiated in practice.  
**Decision pending:** What new fields would most improve analyst triage quality, and which are feasible with a 7B local model?

---

*End of AEGIS Decision Log — Version 1.0*  
*ARC NEXUS LLC / SWAT Signal Desk*  
*May 28, 2026*

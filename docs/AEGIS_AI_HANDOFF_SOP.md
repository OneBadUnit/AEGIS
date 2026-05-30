# AEGIS AI Handoff SOP
## SWAT Signal Desk — ARC NEXUS LLC
### Standard Operating Procedure for AI-Assisted Maintenance, Debugging, and Extension

**Document version:** 1.0  
**Date:** May 28, 2026  
**Prepared for:** Deep Coder and future AI coding agents  
**Prepared by:** GitHub Copilot (Claude Sonnet 4.6) — deep-scan of live codebase  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Folder and File Map](#2-folder-and-file-map)
3. [Runtime Instructions](#3-runtime-instructions)
4. [Current Architecture](#4-current-architecture)
5. [Important Rules for Future AI Coding](#5-important-rules-for-future-ai-coding)
6. [Known Sensitive Areas](#6-known-sensitive-areas)
7. [Common Bugs and Fixes](#7-common-bugs-and-fixes)
8. [Git Workflow](#8-git-workflow)
9. [Future Roadmap](#9-future-roadmap)
10. [Instructions for Deep Coder](#10-instructions-for-deep-coder)

---

## 1. Project Overview

### What AEGIS Is

**AEGIS** (Artificial Event & Global Intelligence System) is a self-hosted, local-first news intelligence platform built for a single analyst. Its full product name is **SWAT Signal Desk**, operated under **ARC NEXUS LLC**.

AEGIS automatically collects news from a curated set of RSS feeds, analyzes each article using a locally-running LLM (via Ollama), scores it across multiple significance dimensions (constitutional risk, censorship signals, war escalation, narrative manipulation), and surfaces the highest-significance items in a React-based analyst dashboard.

The system is deliberately designed around **constitutional watchdog** priorities: it weights civil liberties, press freedom, government overreach, and armed conflict signals more heavily than general news cycle events, and actively deprioritizes entertainment, celebrity, and shallow culture war content.

### Current Purpose

- Collect and analyze news from 50+ curated RSS sources spanning left, center, right, and watchlist editorial orientations
- Score each item for significance, public interest, manipulation risk, and narrative integrity
- Cluster related stories to surface multi-source consensus patterns
- Enable the analyst to scan front pages of 15 curated sources for editorial consensus on what is being covered
- Allow the analyst to save important items to a Report Library for archival
- Provide a live signal feed, keyword/topic scan, and Front Page Consensus view in one dashboard

### Major Workflows

1. **Full RSS Scan** — Fetches all configured feeds, pre-scores raw posts, sends top items to the LLM for analysis, persists scored signals to SQLite.
2. **Keyword Scan** — Ad-hoc topic search that collects only posts matching a keyword query from RSS feeds.
3. **Front Page Consensus** — Fetches front-page RSS headlines from 15 curated sources, clusters them by event identity, scores clusters for editorial consensus, and saves snapshot results to the database.
4. **Save to Library** — Analyst marks a Live Feed item as "tracked," promoting it from the temporary live feed into the persistent Report Library.
5. **Delete** — Soft-deletes a signal (`is_deleted = 1`). Deleted items are permanently suppressed from all views and also suppress future near-duplicate intake.

### What AEGIS Is NOT

- Not a real-time streaming system (it runs on-demand scans)
- Not a multi-user system (single analyst, local machine only)
- Not cloud-hosted (all data is local; Ollama runs locally)
- Not a full NLP pipeline (LLM calls are per-item, not cross-corpus)
- Not a censorship tool (it uses source weighting for confidence, not suppression)
- Not a market or financial analyzer

---

## 2. Folder and File Map

### `backend/app/app.py`

**FastAPI application factory.**

- Creates the `FastAPI` instance titled "SWAT Signal Desk API"
- Registers CORS for `http://127.0.0.1:5175` and `http://localhost:5175` only
- Mounts `radar_router` at `/api/radar`
- Exposes `/health` endpoint
- The `app` object is the entry point used by `main.py` and uvicorn

> **Note:** CORS origins are hardcoded to port 5175. If you change the Vite dev port, you must update this file.

---

### `backend/app/api/routes/radar.py`

**All HTTP API routes for the system.**

This is the main API surface. Every button in the UI calls a route here. Routes are prefixed `/api/radar`. Current routes:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/recent` | Fetch signals (live feed, library, or both) |
| `POST` | `/run` | Start a background full RSS scan |
| `GET` | `/scan-status` | Poll scan progress |
| `POST` | `/search-run` | Start a background keyword scan |
| `GET` | `/search-status` | Poll keyword scan progress |
| `POST` | `/consensus-scan` | Start a background Front Page Consensus scan |
| `GET` | `/consensus-status` | Poll consensus scan progress |
| `GET` | `/consensus` | Fetch latest consensus results |
| `GET` | `/consensus/archive` | Fetch all historical consensus snapshots |
| `GET` | `/consensus/snapshot/{scan_id}` | Fetch one historical snapshot by ID |
| `PATCH` | `/{signal_id}/track` | Save signal to Report Library |
| `DELETE` | `/{signal_id}` | Soft-delete a signal |

Scans run as daemon threads. Each scan type (full, keyword, consensus) has its own lock and state dict so they do not conflict. State dicts carry `running`, `started_at`, `finished_at`, `summary`, and `error` fields polled by the frontend.

> **SENSITIVE:** Route paths here must exactly match the `BASE_URL` + path strings in `frontend/src/lib/api.js`. Any mismatch causes 404 errors that silently break UI buttons.

---

### `backend/app/core/pipeline.py`

**Deterministic scoring engine — the intelligence layer.**

Receives an `analysis` object (from the LLM) and a `RawPost` (source metadata) and computes all significance scores. **Makes no LLM calls.** Fully local and deterministic.

**Score components:**

| Score | Formula |
|-------|---------|
| `significance_score` | `(ai_sig×0.45 + constitutional×0.20 + war×0.15 + censorship×0.10 + narrative×0.10) × (1 - low_sig_penalty×0.40) × source_weight` |
| `public_interest_score` | `ai_sig×0.40 + constitutional×0.25 + censorship×0.20 + war×0.15` |
| `constitutional_score` | Keyword match (0–1) against `_CONSTITUTIONAL_KW` list |
| `censorship_score` | Keyword match (0–1) against `_CENSORSHIP_KW` list |
| `war_score` | Keyword match (0–1) against `_WAR_KW` list |
| `narrative_score` | AI `manipulation_risk` base + flag count boost |

**Source weight (Stage 10 model):**
- If `reliability_tier` is set: `tier_weight × editorial_role_weight`, clamped to [0.35, 1.25]
- Tier 1 (wire/broadcast) = 1.15, Tier 2 = 1.00, Tier 3 = 0.75, Tier 4 = 0.45
- Editorial roles: `facts` = 1.10, `mixed` = 1.00, `analysis` = 0.90, `narrative` = 0.75
- Falls back to legacy `source_role` lookup if tier is absent

---

### `backend/app/db/database.py`

**SQLite persistence layer.**

Database file: `market_radar.db` in the project root (resolved relative to this file's location 3 parents up).

**`signals` table columns (current schema):**

Core fields: `id`, `title`, `source`, `feed_name`, `url` (UNIQUE), `external_id` (UNIQUE), `category`, `source_type`, `source_role`, `source_orientation`, `editorial_role`, `reliability_tier`, `topic`, `summary`, `framing`, `claims`, `filtered`, `filter_reason`, `is_deleted`, `created_at`

AEGIS intelligence columns (added via `ensure_columns` migrations): `signal_type`, `significance_score`, `trend_score`, `constitutional_score`, `censorship_score`, `war_score`, `narrative_score`, `public_interest_score`, `source_weight`, `manipulation_risk`, `narrative_flags`, `tracked`, `title_norm`

**`front_page_consensus` table columns:** `id`, `scan_id`, `topic`, `keywords`, `headlines`, `source_count`, `left_count`, `center_count`, `right_count`, `tier1_count`, `consensus_score`, `consensus_tier`, `created_at`

**Deduplication logic (Stage 9):**
- Exact dedup on `url` and `external_id`
- Near-duplicate dedup on `title_norm` (stop-word-stripped fingerprint) — blocks re-intake of stories already in the Library (`tracked=1`) or deleted (`is_deleted=1`)

**Schema migrations:** All new columns are added via `ensure_columns()` using `ALTER TABLE` with `IF NOT EXISTS` guards. This is safe to run against an existing database — it only adds missing columns and never drops anything.

> **SENSITIVE:** Do not add `DROP COLUMN`, `DROP TABLE`, or `DELETE FROM signals` statements without a confirmed backup. The deduplication system depends on `is_deleted` rows remaining in the table — hard-deleting them would allow previously dismissed stories to re-appear.

---

### `ai/analyzer.py`

**Ollama LLM integration.**

- Model: `qwen2.5:7b`
- Endpoint: `http://127.0.0.1:11434/api/generate`
- Temperature: `0.1` (near-deterministic)
- Timeout: 60 seconds per call
- Output format: `json`

The prompt instructs the model to act as "AEGIS — a constitutional-watchdog signal analyzer." It returns a structured JSON object parsed into a `SignalAnalysis` Pydantic model with fields: `topic`, `summary`, `framing`, `claims`, `signal_type`, `significance_raw` (1–10 int), `manipulation_risk`, `narrative_flags`, `filtered`, `filter_reason`.

If the LLM returns malformed JSON, `extract_json()` attempts to extract the first `{...}` block. If that also fails, an empty dict is returned and the item is skipped.

> **Ollama must be running locally for any scan to process items.** Items that fail LLM analysis are skipped gracefully — they do not crash the scan.

---

### `tasks/run_collectors.py`

**Orchestrates RSS collection and pipeline processing.**

**Two entry points:**
- `run_all_collectors()` — full scan of all configured feeds
- `run_keyword_scan(query)` — targeted scan filtering posts by keyword match

**Processing flow:**
1. Load `config/rss_sources.json`
2. `RSSCollector.fetch()` — fetches all feeds, returns `List[RawPost]`
3. Pre-AI intake prioritization: each `RawPost` is scored deterministically (no LLM) using three keyword tier lists (`_T1_CONFLICT`, `_T1_CONSTITUTIONAL`, `_T1_CENSORSHIP`, etc.) and sorted by score descending
4. Per-category quota enforcement: max N items per category to prevent tech/sports feeds from crowding out geopolitical coverage
5. Up to `MAX_POSTS_TO_PROCESS = 60` items are sent through `SignalPipeline.process()` (which calls the LLM once per item)
6. `MAX_RUNTIME_SECONDS = 240` hard cap prevents runaway scans

**Category quotas (per source):** `geopolitical`/`investigative` = 3, `censorship`/`ai_watch` = 2, most others = 2, `public_signal`/`technology`/`science`/`sports` = 1.

> **Raising `MAX_POSTS_TO_PROCESS` without raising `MAX_RUNTIME_SECONDS` proportionally will cause scans to time out before finishing.**

---

### `tasks/front_page_consensus.py`

**Front Page Editorial Consensus engine (Stage 12).**

**Flow:**
1. Load sources from `config/front_page_sources.json`
2. `FrontPageCollector.fetch()` — fetches top RSS headlines from each source
3. `_union_find_cluster()` — clusters headlines by event identity
4. `_deduplicate_group()` — max 1 article per outlet per cluster, wire services prioritized
5. Scores each cluster by source count, orientation spread, tier-1 presence
6. Persists clusters as a snapshot to `front_page_consensus` table with a unique `scan_id`

**Stage 12 clustering algorithm (critical — do not simplify):**

The clustering algorithm uses Union-Find with `_should_merge()` to decide whether two headlines cover the same event. The rules (in order):

1. If either headline has zero event words after stripping `_HIGH_SALIENCE` entities → **never merge**
2. 2+ shared event words → **merge** (strong content similarity)
3. 1 shared anchor word (`_ANCHOR_WORDS`) **AND** same context domain (`_CONTEXT_KEYWORDS`) → **merge**
4. All other cases → **do not merge**

**`_HIGH_SALIENCE` blocklist:** Names like `trump`, `biden`, `president`, `congress`, `government` are stripped before comparison. These appear in too many headlines to carry event-identity signal — allowing them would merge unrelated stories.

**Context domains:** `legal`, `military`, `election`, `economic`, `diplomatic`, `social`, `general`. Two headlines in different domains cannot merge on a single shared word.

> **SENSITIVE:** The clustering logic in this file is the result of multiple debugging iterations to fix over-merging. Do not "simplify" the merge logic. In Stage 11, any 1 shared word triggered a merge, which caused "trump" to pull every presidential headline into a single mega-cluster. Stage 12 fixed this.

---

### `sources/rss.py`

**RSS feed fetcher.**

- Uses `feedparser` + `requests` for feed fetching
- Sets a browser-like `User-Agent` to avoid feed server blocks
- Reddit feeds are rewritten to `old.reddit.com` for more reliable RSS responses
- Sponsored/ad entries are filtered by `is_sponsored_entry()` (checks for `"promoted"`, `"sponsored"`, `"advertisement"`, etc.)
- Passes through all source metadata fields from `rss_sources.json` (`source_orientation`, `editorial_role`, `reliability_tier`, etc.) into each `RawPost`

---

### `config/rss_sources.json`

**Master list of all RSS feed sources.**

Each entry contains:

| Field | Type | Purpose |
|-------|------|---------|
| `name` | string | Display name shown in the UI |
| `url` | string | RSS feed URL |
| `category` | string | Content category for quota enforcement |
| `source_type` | string | `news`, `reddit`, etc. |
| `source_role` | string | Legacy role: `baseline`, `independent`, `public`, `geopolitical`, `censorship_watch`, `ai_watch` |
| `source_orientation` | string | `center`, `left`, `right`, `watchlist` |
| `editorial_role` | string | `facts`, `mixed`, `analysis`, `narrative` |
| `reliability_tier` | int | `1`–`4` per Stage 10 Source Intelligence Model |

> **SENSITIVE:** Changes here affect source weighting scores on all future items from that source. Adding a new feed without the `reliability_tier` field causes it to fall back to the legacy `source_role` weight (0.70 default). Do not remove or rename existing fields — they are mapped directly into `RawPost` and persisted to the database.

---

### `config/NewsSources.md`

**Human-readable documentation of the Stage 10 Source Intelligence Model.**

Defines editorial orientation codes (`center`, `left`, `right`, `watchlist`), reliability tiers (1–4), and editorial role codes (`facts`, `mixed`, `analysis`, `narrative`). Explains the scoring philosophy, cross-spectrum corroboration principles, and what each classification means.

This is a reference document, not loaded at runtime. It governs how new sources should be classified when adding them to `rss_sources.json`.

---

### `frontend/src/pages/RadarDashboard.jsx`

**Main React page — the entire analyst UI.**

This is a large, multi-state component. Key state variables:

| State | Purpose |
|-------|---------|
| `items` | All signals fetched from the backend for the current view |
| `activeView` | Current dashboard tab: `"live"` \| `"library"` \| `"consensus"` \| `"archive"` |
| `sortMode` | Current sort: `"significance"` \| `"recency"` |
| `showFiltered` | Whether to include noise/filtered items |
| `consensusData` | Latest consensus scan cluster results |
| `consensusArchive` | List of all historical scan snapshots |
| `selectedScanId` | Which archive snapshot is being viewed (null = latest) |
| `scanning` / `keywordScanning` / `consensusScanning` | Per-scan-type in-progress flags, polled every 2.5s |

**View routing logic:** The `activeView` state variable controls which content block renders. Adding a new view tab requires: (1) adding the tab button, (2) adding the render block, and (3) potentially adding new fetch calls. Missing the render block causes the tab to appear clickable but show nothing.

**Clustering (client-side):** Signals are grouped by `clusterSignals()` (Union-Find on shared topic words), then each cluster is scored by `scoreCluster()` for front-page tier placement. The scoring respects source orientation, tier-1 presence, and keyword importance patterns.

**Quick Scan presets:** Seven preset buttons at the top (`PRESETS` array) each fire a keyword scan. Clicking them **adds items to the database** — they do not filter the existing view.

---

### `frontend/src/components/SignalCard.jsx`

**Individual signal card component.**

- Two render modes: `compact` (for cluster leads) and full
- Significance badge displayed for scores ≥ 0.20: `medium` (0.20–0.44), `high` (0.45–0.69), `critical` (≥ 0.70)
- `data-significance` attribute on the card element drives the CSS border color override
- Below 0.20 significance, the card falls back to `data-category` color coding
- `narrative_flags` is stored as a JSON string in the DB; it is parsed at render time and displayed as individual flag badges
- Delete flow: first click → shows confirm/cancel inline (no modal); second click confirms → `onConfirmDelete` fires
- `Save to Library` button only shown when `viewMode === "live"`

---

### `frontend/src/lib/api.js`

**All frontend–backend API calls.**

Base URL: `http://127.0.0.1:8002/api/radar`

All calls use `requestJson()` which throws `Error` on non-2xx responses (parses the FastAPI `detail` field if available).

**Exported functions:**

| Function | HTTP | Path |
|----------|------|------|
| `fetchRecent(limit, includeFiltered, trackedOnly, liveOnly)` | GET | `/recent` |
| `runScan()` | POST | `/run` |
| `fetchScanStatus()` | GET | `/scan-status` |
| `deleteSignal(id)` | DELETE | `/{id}` |
| `runSearchScan(query)` | POST | `/search-run` |
| `fetchSearchStatus()` | GET | `/search-status` |
| `trackReport(id)` | PATCH | `/{id}/track` |
| `runConsensusScan()` | POST | `/consensus-scan` |
| `fetchConsensusScanStatus()` | GET | `/consensus-status` |
| `fetchConsensus()` | GET | `/consensus` |
| `fetchConsensusArchive()` | GET | `/consensus/archive` |
| `fetchConsensusSnapshot(scanId)` | GET | `/consensus/snapshot/{scanId}` |

> **SENSITIVE:** The port `8002` is hardcoded here. If the backend port changes, this file must be updated.

---

### `frontend/src/styles.css`

**All UI styling.**

Uses CSS custom properties (design tokens) defined in `:root`. Key tokens:

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-main` | `#10151c` | Page background |
| `--panel` | `#151d26` | Card/panel background |
| `--amber` | `#d69a38` | Primary accent, links |
| `--monitor-green` | `#5ccf91` | Success states, live indicators |
| `--live-red` | `#d64b3f` | Alert/critical states |
| `--font-brand` | Barlow Condensed | Headers, labels |
| `--font-mono` | JetBrains Mono | Scores, metadata |

Card border colors are driven by `data-category` and `data-significance` CSS attribute selectors. The `data-significance` attribute (set on `SignalCard`) overrides the category color. Breaking the attribute name on either side (JSX or CSS) causes all cards to fall back to the default category styling.

Fonts are loaded from Google Fonts (`@import` at top of file). In an offline/air-gapped environment, this import will silently fail and the system will fall back to system fonts.

---

## 3. Runtime Instructions

### Starting the Backend

From the **project root** (`d:\ARC NEXUS LLC\AEGIS`):

```powershell
python main.py
```

This starts uvicorn on `http://127.0.0.1:8002`. The server runs synchronously (no `--reload`) to avoid worker-count issues with the SQLite connection.

**Required Python interpreter:** Use the project's virtual environment (`.venv` or the VS Code selected interpreter). The VS Code workspace interpreter must match the environment where `fastapi`, `uvicorn`, `feedparser`, `requests`, and `pydantic` are installed. Pylance/IntelliSense may show false import errors if the wrong interpreter is selected in VS Code even when the runtime works correctly.

**Alternative (uvicorn directly):**
```powershell
uvicorn backend.app.app:app --host 127.0.0.1 --port 8002
```

**Prerequisite:** Ollama must be running at `http://127.0.0.1:11434` with `qwen2.5:7b` pulled:
```powershell
ollama serve          # in a separate terminal if not already running
ollama pull qwen2.5:7b
```

---

### Starting the Frontend

```powershell
cd frontend
npm install           # first time only
npm run dev
```

Frontend runs at `http://127.0.0.1:5175`.

---

### Port Summary

| Service | Port | Where configured |
|---------|------|-----------------|
| Backend (FastAPI/uvicorn) | **8002** | `main.py`, `backend/app/app.py` (CORS), `frontend/src/lib/api.js` |
| Frontend (Vite dev server) | **5175** | `frontend/vite.config.js`, `frontend/package.json`, `backend/app/app.py` (CORS) |
| Ollama | **11434** | `ai/analyzer.py` (`OLLAMA_URL`) |

---

### Python Interpreter Notes

- The project uses standard Python imports via `backend.*`, `sources.*`, `tasks.*`, `ai.*` — all resolved relative to the **project root**.
- Always run `python main.py` from the project root. Running from a subdirectory will break all relative imports.
- VS Code must have its Python interpreter set to the same virtualenv that has the dependencies installed (check with `python -c "import fastapi; print(fastapi.__version__)"`).

---

### Ollama / Local AI Assumptions

- Model: `qwen2.5:7b` — balanced speed/quality for signal analysis
- All inference is local — no external API calls, no cloud LLM
- Temperature `0.1` — near-deterministic for consistent JSON output
- If Ollama is not running, scans will complete but all items will have empty AI analysis fields (significance scores will be 0.0 or defaults)
- The system is designed to degrade gracefully when the LLM is unavailable

---

## 4. Current Architecture

### Live Feed

**What it is:** The default view on load. Shows all signals with `tracked = 0` and `is_deleted = 0`, ordered by creation time (newest first) or sorted by significance/public interest.

**How items arrive:**
1. Analyst clicks "Scan All Feeds" → `POST /api/radar/run` → background thread
2. `run_all_collectors()` fetches RSS, pre-scores all raw posts, sends top-priority items to the LLM pipeline
3. Scored `SignalItem` objects are inserted via `db.insert_signal()`
4. Deduplication: exact URL/external_id match, and near-duplicate title fingerprint match against Library + deleted items
5. Frontend polls scan status every 2 seconds; when scan finishes, `fetchRecent()` refreshes the feed

**Clustering (client-side):** When the "Cluster" toggle is on, `clusterSignals()` groups items by shared topic words using Union-Find. Clusters with 2+ signals are labeled with the top 3 shared words. Clusters with `back_page` or `noise` tier and 3+ signals are compressed into a collapsed card.

---

### Report Library

**What it is:** Items the analyst has explicitly saved. Shows signals with `tracked = 1` and `is_deleted = 0`.

**How items arrive:** Analyst clicks "Save to Library" on a live feed item → `PATCH /{id}/track` → `db.track_signal(id)` sets `tracked = 1`.

**Behavior:** Saved items are excluded from the live feed view (`live_only = true`). The Library view fetches with `tracked_only = true`. Items in the Library are also excluded from future near-duplicate intake (a story already saved will not reappear as a new item even after a fresh scan).

---

### Front Page Consensus

**What it is:** A separate scanning mode that checks what 15 curated sources are currently running as their top headlines — without going through the LLM pipeline. Pure RSS fetch + deterministic clustering.

**How it works:**
1. Analyst clicks "Scan Front Pages" → `POST /api/radar/consensus-scan`
2. `run_front_page_consensus()` fetches top 10 headlines per source from `config/front_page_sources.json`
3. Headlines are clustered by event identity (Stage 12 algorithm — see `front_page_consensus.py` notes)
4. Each cluster is scored for editorial consensus: how many sources covered it, what orientations are represented, whether Tier-1 wire services are present
5. Consensus tier assigned: `confirmed` (≥0.70), `elevated` (≥0.45), `monitored` (≥0.20), `noise` (<0.20)
6. Results saved to `front_page_consensus` table with a UUID `scan_id` and timestamp
7. Frontend displays the latest scan results

**Displayed in:** The "Consensus" tab of the dashboard.

---

### Consensus Archive

**What it is:** Historical record of every front-page consensus scan ever run, browsable by the analyst.

**How it works:** Each `run_front_page_consensus()` call generates a new `scan_id` (UUID + timestamp). After the scan, results are accessible via `GET /consensus/archive` (returns a list of snapshot summaries) and `GET /consensus/snapshot/{scan_id}` (returns full cluster detail for one scan).

**Displayed in:** The "Archive" tab of the dashboard. Analyst clicks a snapshot to expand it.

> **Known issue:** If the Archive tab render block is accidentally removed or placed inside a wrong conditional in `RadarDashboard.jsx`, the tab will appear but render nothing. Always verify the `view === "archive"` render block exists.

---

### Save to Library

- Triggered by "Save to Library" button on any Live Feed card
- Calls `PATCH /{id}/track`
- Sets `tracked = 1` in the database
- Item disappears from Live Feed (which fetches `live_only = true`)
- Item appears in Report Library (which fetches `tracked_only = true`)
- Item's `title_norm` fingerprint is now in the dedup blocklist: future scans will not re-import near-identical stories

---

### Delete Behavior

- Soft-delete only — `is_deleted = 1` is set, row is never removed
- Deleted items are excluded from all frontend queries (`is_deleted = 0` condition is always present)
- The deleted item's `title_norm` fingerprint is added to the dedup blocklist, preventing the same story from cycling back in after future scans
- There is no "undo delete" — once deleted, the signal is permanently suppressed (by design)

---

### Source Weighting

Two-stage model (Stage 10):

**Stage 10 (preferred — uses `reliability_tier` + `editorial_role`):**
- `source_weight = tier_weight × editorial_role_weight`, clamped [0.35, 1.25]
- Tier 1 (AP, BBC, Reuters): 1.15 × role modifier
- Tier 4 (Reddit, RT, fringe): 0.45 × role modifier

**Legacy fallback (uses `source_role` string):**
- `baseline` (AP, Reuters): 1.00
- `geopolitical`: 1.15
- `censorship_watch`: 1.10
- `independent` (TechCrunch, Wired): 0.85
- `public` (Reddit): 0.55

Source weight is the final multiplier on `significance_score`. A Tier 4 source can still surface high-significance content but its scores are reduced proportionally. Tier 1 wire services can push scores above 1.0 (before clamping) for genuinely significant stories.

---

### Cluster Scoring

Client-side cluster scoring (in `RadarDashboard.jsx`) assesses a cluster's editorial importance using:

1. **Max/avg significance scores** (60% of weight) — the highest-scored item in the cluster drives editorial relevance
2. **Item count** — more sources covering a story = more significant
3. **Unique source count** — cross-outlet coverage boosts the score
4. **Front-page keyword boost** — presence of patterns like "nuclear", "ceasefire", "supreme court", "executive order" boosts up to +0.50
5. **Section keyword boost** — secondary policy/national-interest patterns add up to +0.20
6. **Back-page penalty** — entertainment/tech-review content penalized -0.25
7. **Corroboration bonus** — left + center + right all covering the same story: +0.20; partial: +0.10; 2+ Tier 1 sources: +0.20
8. **Reliability caps** — all-Tier-4 clusters capped at 0.59 (never FRONT_PAGE); all Tier-3+ capped at 0.79

---

### Front-Page Consensus Scanning

The consensus engine (Python, `tasks/front_page_consensus.py`) is separate from the live feed scoring (which also runs cluster scoring on the JS side). Key distinctions:

- **Source set:** Only the 15 sources in `config/front_page_sources.json` (not the full 50+ RSS feeds)
- **No LLM:** Pure RSS + deterministic text matching — fast, no Ollama required
- **Clustering algorithm:** Python Union-Find with `_should_merge()` — event-identity based, not topic-word overlap
- **Output:** Saved to `front_page_consensus` table with left/center/right/tier1 counts per cluster
- **Purpose:** Answers "what are editors across the political spectrum leading with right now?" — editorial consensus, not AI-scored significance

---

### Event Identity Clustering

Used in `front_page_consensus.py`. The Stage 12 algorithm clusters by **event identity**, not entity mention:

- `_HIGH_SALIENCE` words (political figures, generic government terms) are stripped before comparing
- Two headlines must share 2+ non-salience event words, OR 1 anchor word in the same context domain
- Context domains (legal, military, election, economic, diplomatic, social) prevent cross-domain false merges
- Per-source dedup: max 1 article per outlet per cluster, wire services preferred

This is different from the client-side clustering in `RadarDashboard.jsx` which uses simple shared-word Union-Find on significance-scored signals.

---

## 5. Important Rules for Future AI Coding

These rules exist because of past issues. Follow them without exception.

### Return Full Updated Files

When modifying a file, return the **complete updated file**, not a diff or partial snippet. The human uses the returned file to replace the original. Partial returns cause missed context, merge errors, and broken behavior.

### Do Not Infer New Features

If the user asks to fix a bug, fix only that bug. If the user asks to add one feature, add only that feature. Do not add related features you believe "would help." Every unasked addition risks breaking tested behavior.

### Do Not Add Hide/Archive/Remove Unless Explicitly Requested

The UI delete/track workflow was carefully designed. Do not add "Hide," "Archive," "Dismiss," "Remove," or any status-toggle buttons unless the user explicitly requests them. These would require schema changes, API routes, and frontend state management that have not been scoped.

### Do Not Redesign the UI Unless Asked

The dark panel + amber accent design is intentional. Do not change component structure, layout, or visual hierarchy unless the user says to. Adding unsolicited whitespace, changing font sizes, or restructuring cards breaks the established signal desk aesthetic.

### Preserve Working Workflows

Before changing any file, confirm that the workflow it participates in still works end-to-end after your change. The most important workflows (in order of criticality):
1. Full RSS scan → signal appears in Live Feed
2. Save to Library → signal moves to Library
3. Delete → signal disappears permanently
4. Front Page Consensus scan → results appear in Consensus tab
5. Keyword scan → results appear in Live Feed

### Make Additive Changes Where Possible

Prefer extending existing functions over replacing them. Prefer adding new API routes over modifying existing ones. Prefer adding new columns to the DB via `ensure_columns()` migration rather than modifying `ensure_tables()`.

### Explain Changed Files

In your response, list every file you modified and summarize what changed in each. This helps the analyst apply changes in the right order and understand scope.

### Avoid Broad Rewrites

If a function works, do not rewrite it to be "cleaner" or more idiomatic. Each rewrite risks introducing subtle behavior changes. Make targeted, minimal edits.

---

## 6. Known Sensitive Areas

These files have historically caused breaking issues when modified carelessly.

### `backend/app/api/routes/radar.py` — Route Paths

Every path string here must match the path in `frontend/src/lib/api.js`. A typo in either location produces a 404 that silently breaks the corresponding UI button. Route parameters (e.g., `/{signal_id}`) must match the FastAPI path parameter name and the JS URL construction.

The scan state dicts and locks are module-level globals. If you refactor them into a class, all route handlers that reference `scan_state` must be updated. Missing one causes KeyError or race conditions.

### `backend/app/db/database.py` — Schema/Migrations

- `ensure_columns()` is the safe migration path. New columns go here, not in `ensure_tables()`.
- Never remove columns. The application code references column names by string — removing a column causes `KeyError` on any row fetch.
- `is_deleted` column behavior is load-bearing: the deduplication system (`insert_signal`) checks `is_deleted = 1` rows. Dropping this column or changing its semantics breaks the intake dedup.
- `title_norm` and its index are also load-bearing for dedup.
- The SQLite connection uses `check_same_thread=False` to support background scan threads. Do not change this.

### `tasks/front_page_consensus.py` — Clustering Logic

The `_HIGH_SALIENCE`, `_ANCHOR_WORDS`, `_CONTEXT_KEYWORDS`, and `_should_merge()` function are a carefully tuned system. Do not:
- Remove words from `_HIGH_SALIENCE` without understanding that those words appear in many unrelated headlines
- Lower the merge threshold from 2 to 1 (this was the Stage 11 bug that caused over-clustering)
- Change the context-domain cross-check (removing it would allow "iran sanctions" to merge with "iran nuclear strike")
- Simplify `_union_find_cluster()` — the path compression in `find()` is O(α(n)) and correct

### `frontend/src/pages/RadarDashboard.jsx` — State and View Logic

- The `view` state variable controls which render block is shown. Each tab (live, library, consensus, archive) has a dedicated `view === "..."` conditional block. Remove one and that tab shows nothing.
- Scan polling (`useEffect` with `setInterval`) must be cleaned up with `clearInterval` on the return. Missing cleanup causes memory leaks and stale state updates after component unmount.
- The `useMemo` hooks for `filteredSignals` and `clusteredSignals` depend on specific state variables. Adding new filter state without updating the `useMemo` dependency array causes stale renders.
- JSX comment syntax is `{/* comment */}`. Do NOT use `// comment` inside JSX return blocks — it causes a React runtime error. This has broken the build before.

### `config/rss_sources.json` — Source Metadata

- Each source entry feeds directly into `RawPost` fields and is persisted to the DB on first scan.
- The `reliability_tier` field must be an integer 1–4 (not a string). The RSS collector reads it with `feed.get("reliability_tier")` and passes it as-is to `RawPost`.
- Missing `reliability_tier` causes the source to fall back to legacy scoring (fine, but unintended for new sources).
- Source `name` is used as `feed_name` in the DB and displayed in the UI. Changing a source name on existing records does not retroactively update old signals.

### `frontend/src/styles.css` — Card Layout

- Card borders are set by `data-category` and `data-significance` CSS attribute selectors. The attribute names are case-sensitive and must match exactly what `SignalCard.jsx` sets.
- The `.opp-card--compact` class is used by clustered lead cards. Removing or renaming it breaks the compressed cluster view.
- The significance badge classes (`medium`, `high`, `critical`) are referenced by both CSS and `SignalCard.jsx`. Rename one without renaming both and badges lose their color.

---

## 7. Common Bugs and Fixes

### VS Code / Pylance Interpreter Issue

**Symptom:** Pylance shows red underlines on `from fastapi import FastAPI` or `from backend.app...` imports even though the app runs fine.

**Cause:** VS Code has selected the system Python instead of the project virtualenv.

**Fix:** `Ctrl+Shift+P` → "Python: Select Interpreter" → choose the `.venv` or the interpreter where project dependencies are installed. Pylance must index the correct environment. This does not affect runtime behavior — only affects IDE warnings.

---

### Backend Port Mismatch

**Symptom:** Frontend shows no data, API calls fail with CORS errors or `net::ERR_CONNECTION_REFUSED`.

**Cause:** Backend is running on a port other than 8002, or `frontend/src/lib/api.js` has an old port value.

**Fix:** Ensure `main.py` has `port=8002`, `backend/app/app.py` CORS origins include `http://127.0.0.1:5175`, and `api.js` has `BASE_URL = "http://127.0.0.1:8002/api/radar"`. All three must agree.

---

### `node_modules` Should Be Ignored

**Symptom:** Git shows thousands of changed files after `npm install`, or VS Code file search is very slow.

**Cause:** `node_modules/` is not in `.gitignore`, or `.gitignore` is missing.

**Fix:** Ensure `.gitignore` includes `node_modules/`. Do not commit `node_modules`.

---

### Database and Log Files Ignored by Git

**Symptom:** `market_radar.db` or Python log files are staged for commit.

**Fix:** `.gitignore` should include:
```
market_radar.db
*.db
*.log
__pycache__/
*.pyc
.venv/
node_modules/
```

The SQLite database is local runtime data, not source code. It must never be committed to version control.

---

### JSX Comment Syntax Issue

**Symptom:** Vite build fails with a cryptic JSX parse error. Browser shows blank page.

**Cause:** A `// single-line comment` was written inside a JSX return block instead of `{/* JSX comment */}`.

**Fix:** All comments inside JSX must use `{/* comment */}`. This error is easy to introduce when adding conditional blocks and is hard to spot visually.

---

### Archive UI Not Rendering

**Symptom:** "Archive" tab is clickable but shows nothing.

**Cause:** The `view === "archive"` render block was accidentally placed inside a `view === "consensus"` conditional, or was deleted during a refactor.

**Fix:** Verify that `RadarDashboard.jsx` has a top-level conditional block: `{view === "archive" && <div className="archive-view">...</div>}` that is not nested inside any other view conditional.

---

### Source Clustering Merging by Entity Instead of Event

**Symptom:** Front Page Consensus shows one giant cluster that contains completely unrelated stories (e.g., an Iran sanctions story, a Trump DOJ probe, and a NATO alliance meeting all merged into one card).

**Cause:** The Stage 12 event-identity clustering logic was bypassed, simplified, or reverted to Stage 11 behavior (any 1 shared word triggers a merge).

**Fix:** Confirm `_should_merge()` in `front_page_consensus.py` requires either 2+ shared event words OR 1 anchor word + same context domain. Confirm `_HIGH_SALIENCE` contains `"trump"`, `"biden"`, `"president"`, `"congress"`, etc. Confirm `_HIGH_SALIENCE` words are stripped in `_event_words()` before comparison.

---

## 8. Git Workflow

### Commit Before Major AI Changes

Before asking an AI agent to make any significant code change, run:

```powershell
git add -A
git commit -m "checkpoint: before [description of planned change]"
```

This creates a restore point. If the AI change introduces a regression, you can `git checkout` the checkpoint commit without losing your working state.

### Use Checkpoints for Every Phase

AEGIS has been developed in named phases (Phase 1A, 1B, 2A, Stage 10, Stage 11, Stage 12). Each phase boundary is a natural commit point. Commit with a message that includes the phase label:

```
git commit -m "Stage 12: event-identity clustering for consensus engine"
```

### Branch Recommendations

| Branch | Purpose |
|--------|---------|
| `main` | Production-stable. Only merge here after manual testing. |
| `dev` | Active development. AI changes go here first. |
| `experimental` | Untested or speculative changes. Never merges directly to main. |

### `.gitignore` Notes

Minimum required ignores for this project:

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/

# Runtime data
market_radar.db
*.db
*.log

# Frontend
node_modules/
frontend/dist/

# OS
.DS_Store
Thumbs.db

# Editor
.vscode/settings.json
```

Do not commit `.env` files, local secrets, or the SQLite database.

---

## 9. Future Roadmap

These are likely next improvements based on the current system's design trajectory. None of these are currently implemented.

### Faster Dedup / Indexing

The current `title_norm` index handles dedup at intake. If the database grows beyond ~50,000 rows, query performance on `INSERT OR IGNORE` may degrade. Next steps: periodic vacuum/archive of old signals, or a separate "seen titles" bloom filter in memory.

### Front-Page Quality Tuning

The consensus score thresholds (`confirmed` at 0.70, `elevated` at 0.45, `monitored` at 0.20) and keyword boost lists are tuned for the current source set. Adding more sources or changing the curated 15 may require recalibrating boost weights and tier thresholds.

### Narrative Drift Detection

Currently, each item is analyzed independently. A future enhancement would compare current framing patterns across a 24-hour window to detect coordinated narrative shifts (same story gaining different editorial framing over time).

### Better Source Freshness Checks

RSS feeds occasionally serve stale cached content. A future enhancement would track `pubDate` per feed and skip items older than a configurable window (e.g., 48 hours) to prevent re-surfacing old news.

### Report Quality Improvements

The LLM prompt currently extracts topic, summary, framing, and claims. Future improvements: extract key named entities, add a confidence estimate, improve the `significance_raw` scale calibration for mid-range (4–6) items which are currently under-differentiated.

### NEXIS-LOCAL Later Reuse

AEGIS is being built as a foundation for a broader local intelligence system (NEXIS-LOCAL). The source intelligence model, scoring pipeline, and database schema are designed to be reusable. Future integration points: direct document ingestion (PDF, DOCX), cross-corpus analysis, analyst note-taking layer.

---

## 10. Instructions for Deep Coder

**Read this section before modifying any code in this project.**

These are non-negotiable operating rules. Follow them every time.

---

**1. Do a file read before writing.**  
Before modifying any file, read its current content in full. Never assume you know what's in a file based on a previous session or a summary. Code changes since your last context may have changed the file significantly.

**2. Return the complete file.**  
When you return a modified file, return the entire file — not a partial excerpt, not a diff, not "here are the lines that changed." The human replaces the old file with your output. A partial return results in a broken file.

**3. Name every file you touched.**  
In your response, list every file you modified. One line per file, brief description of what changed. This is required for the human to understand the scope of changes and apply them correctly.

**4. Do not add features that were not requested.**  
If asked to fix a bug in `radar.py`, fix only that bug. Do not add logging, error handling for unrelated cases, or refactored helpers unless specifically asked.

**5. Do not change the port, model name, or DB path unless explicitly told to.**  
Port 8002 (backend), port 5175 (frontend), model `qwen2.5:7b`, and DB path `market_radar.db` in the project root are current working configuration. Changing them without being asked will break the running system.

**6. Do not simplify the clustering logic.**  
The `_should_merge()` function in `front_page_consensus.py` and the `clusterSignals()` / `scoreCluster()` functions in `RadarDashboard.jsx` are the result of iterative debugging. Do not simplify, "clean up," or "optimize" them without being explicitly asked. The complexity is intentional.

**7. Do not add UI buttons without a full implementation plan.**  
Every button requires: a CSS class, a handler function, a state variable, an API call, a backend route, and a DB operation. Adding a button without all of these creates a UI affordance that does nothing or throws an error. Do not add partial implementations.

**8. Respect the soft-delete contract.**  
`is_deleted = 1` is not a display toggle. It permanently suppresses re-intake of near-duplicate stories via `title_norm` dedup. Do not convert soft-deletes to hard-deletes. Do not add an "undo delete." The design is intentional.

**9. Check for JSX comment syntax.**  
Any time you add a comment inside a JSX return block, use `{/* comment */}`. Using `//` inside JSX is a build-breaking error.

**10. Verify port agreement across all three locations.**  
If a port-related change is requested, update all three: `main.py` (backend port), `backend/app/app.py` (CORS origins), and `frontend/src/lib/api.js` (BASE_URL). Missing one location causes silent failures.

**11. When in doubt, ask.**  
If a request is ambiguous or would require changes to multiple sensitive systems, state your interpretation and ask for confirmation before proceeding. A clarifying question is less costly than a broad rewrite that breaks production behavior.

---

*End of AEGIS AI Handoff SOP — Version 1.0*  
*ARC NEXUS LLC / SWAT Signal Desk*  
*Generated: May 28, 2026*

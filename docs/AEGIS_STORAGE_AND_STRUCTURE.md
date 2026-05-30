# AEGIS — Storage, Structure & Architecture Reference
## SWAT Signal Desk / ARC NEXUS LLC
### Technical Architecture Document

**Version:** 1.0  
**Date:** May 28, 2026  
**Purpose:** Definitive technical reference for AI agents and developers. Covers physical layout, data flow, storage schema, frontend/backend architecture, source intelligence model, runtime environment, design decisions, and failed approaches.

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [File Dependency Map](#2-file-dependency-map)
3. [Data Flow](#3-data-flow)
4. [Database Architecture](#4-database-architecture)
5. [Frontend Architecture](#5-frontend-architecture)
6. [Backend Architecture](#6-backend-architecture)
7. [Source Intelligence Model](#7-source-intelligence-model)
8. [Runtime Environment](#8-runtime-environment)
9. [Critical Files](#9-critical-files)
10. [Architectural Decisions](#10-architectural-decisions)
11. [Failed Approaches](#11-failed-approaches)
12. [Future Migration to NEXIS-LOCAL](#12-future-migration-to-nexis-local)

---

## 1. Project Structure

```
d:\ARC NEXUS LLC\AEGIS\        ← Project root (CWD for all runtime calls)
│
├── main.py                               Runtime entry point — starts uvicorn on port 8002
├── models.py                             Pydantic models: RawPost, SignalAnalysis, SignalItem
├── analyzer.py                           Root-level alias (not the active analyzer — see ai/)
├── __init__.py
│
├── backend/                              FastAPI application
│   └── app/
│       ├── __init__.py
│       ├── app.py                        App factory: creates FastAPI, registers CORS + router
│       ├── api/
│       │   └── routes/
│       │       └── radar.py              All HTTP routes (/api/radar/*)
│       ├── core/
│       │   └── pipeline.py               Scoring engine: RawPost + LLM output → SignalItem
│       └── db/
│           └── database.py               SQLite persistence: schema, migrations, queries
│
├── ai/                                   LLM integration
│   ├── __init__.py
│   └── analyzer.py                       Ollama client: builds prompt, calls qwen2.5:7b, parses JSON
│
├── sources/                              Data collectors
│   ├── __init__.py
│   ├── base.py                           Abstract BaseCollector — enforces fetch() contract
│   ├── rss.py                            RSS feed fetcher (feedparser + requests)
│   └── front_page.py                     Front-page headline fetcher (consensus source only)
│
├── tasks/                                Orchestration layer
│   ├── run_collectors.py                 Full scan + keyword scan orchestrators
│   └── front_page_consensus.py           Front Page Consensus scan engine (Stage 12)
│
├── config/                               Static configuration files
│   ├── rss_sources.json                  All 50+ RSS feed definitions with source metadata
│   ├── front_page_sources.json           15 curated sources for consensus scanning
│   └── NewsSources.md                    Human-readable documentation of the source model
│
├── frontend/                             React single-page application
│   ├── index.html                        Vite entry HTML
│   ├── package.json                      Node dependencies (React, Vite)
│   ├── vite.config.js                    Vite dev server config (host 127.0.0.1, port 5175)
│   └── src/
│       ├── App.jsx                       Root React component — renders RadarDashboard
│       ├── main.jsx                      ReactDOM.createRoot entry point
│       ├── styles.css                    All styling — design tokens, layout, cards
│       ├── components/
│       │   ├── SignalCard.jsx            Individual signal card (full + compact modes)
│       │   ├── OpportunityCard.jsx       Legacy component (not actively used)
│       │   ├── OpportunityDetail.jsx     Legacy component (not actively used)
│       │   └── OpportunityFeed.jsx       Legacy component (not actively used)
│       ├── lib/
│       │   └── api.js                    All frontend→backend API calls
│       └── pages/
│           └── RadarDashboard.jsx        Main analyst UI — all views, state, clustering
│
├── docs/                                 Documentation (not loaded at runtime)
│   ├── AEGIS_AI_HANDOFF_SOP.md
│   ├── AEGIS_DECISION_LOG.md
│   ├── AEGIS_DEVELOPER_RULES.md
│   ├── AEGIS_RECOVERY_AND_SETUP.md
│   ├── AEGIS_STORAGE_AND_STRUCTURE.md   ← this file
│   └── AEGIS_USER_INSTALL_GUIDE.md
│
├── market_radar.db                       SQLite database (runtime data, not committed to git)
│
└── [utility files]
    ├── Kill_Python.bat                   Force-kills Python processes
    ├── Launch Market Radar.vbs           Windows script to start backend + frontend
    ├── Stop Market Radar.bat             Stops running services
    └── tree.txt                          Folder snapshot
```

### Folder Purposes

| Folder | Purpose |
|--------|---------|
| `backend/` | FastAPI web server — routes, pipeline, database |
| `ai/` | Ollama LLM client — analyzes raw text, returns structured JSON |
| `sources/` | Data collectors — fetch RSS feeds, return `RawPost` objects |
| `tasks/` | Orchestrators — coordinate collectors, pipeline, and DB storage |
| `config/` | Static JSON/Markdown source configuration |
| `frontend/` | React SPA — the analyst dashboard |
| `docs/` | Architecture and handoff documentation |

---

## 2. File Dependency Map

### Complete Dependency Chains

#### Full RSS Scan Flow

```
main.py
  └── uvicorn → backend/app/app.py (creates FastAPI app)
                  └── backend/app/api/routes/radar.py (registers all routes)
                        └── POST /run → tasks/run_collectors.py::run_all_collectors()
                              ├── config/rss_sources.json (feed list)
                              ├── sources/rss.py::RSSCollector.fetch() → List[RawPost]
                              │     └── sources/base.py::BaseCollector (interface)
                              ├── pre_score_raw_post() (pure Python, no imports)
                              ├── backend/app/core/pipeline.py::SignalPipeline.process_item()
                              │     ├── ai/analyzer.py::analyze_item() → SignalAnalysis
                              │     │     └── Ollama HTTP API (port 11434)
                              │     └── score_item(analysis, raw_post) → dict of scores
                              ├── backend/app/db/database.py::insert_signal()
                              └── models.py (RawPost, SignalAnalysis, SignalItem)
```

#### Frontend Render Chain

```
frontend/src/main.jsx
  └── frontend/src/App.jsx
        └── frontend/src/pages/RadarDashboard.jsx
              ├── frontend/src/lib/api.js (all HTTP calls)
              │     └── http://127.0.0.1:8002/api/radar/* (backend)
              ├── frontend/src/components/SignalCard.jsx (renders each signal)
              └── frontend/src/styles.css (imported globally in main.jsx)
```

#### Front Page Consensus Chain

```
radar.py::POST /consensus-scan
  └── tasks/front_page_consensus.py::run_front_page_consensus()
        ├── config/front_page_sources.json (15 curated sources)
        ├── sources/front_page.py::FrontPageCollector.fetch() → List[Dict]
        ├── _union_find_cluster() → groups headlines by event identity
        │     ├── _event_words() → strips _HIGH_SALIENCE entities
        │     ├── _classify_context() → assigns domain (legal/military/etc)
        │     └── _should_merge() → 2+ shared event words OR 1 anchor + same domain
        ├── _deduplicate_group() → max 1 article per outlet, tier-1 first
        ├── _score_consensus() → float 0.0–1.0
        ├── _consensus_tier() → "confirmed" | "elevated" | "monitored" | "noise"
        └── database.py::insert_consensus()
```

### Per-File Dependency Table

| File | Called By | Calls | Depended On By |
|------|-----------|-------|----------------|
| `main.py` | OS / startup script | `backend.app.app:app` (uvicorn) | — |
| `backend/app/app.py` | `main.py`, uvicorn | `radar.py` (router) | All routes |
| `backend/app/api/routes/radar.py` | `app.py` | `database.py`, `run_collectors.py`, `front_page_consensus.py` | Frontend via HTTP |
| `backend/app/core/pipeline.py` | `run_collectors.py` | `ai/analyzer.py`, `models.py` | `run_collectors.py` |
| `backend/app/db/database.py` | `radar.py`, `run_collectors.py`, `front_page_consensus.py` | SQLite (`market_radar.db`) | All data persistence |
| `ai/analyzer.py` | `pipeline.py` | Ollama HTTP API, `models.py` | `pipeline.py` |
| `sources/base.py` | `sources/rss.py`, `sources/front_page.py` | `models.py` | Source collectors |
| `sources/rss.py` | `run_collectors.py` | `feedparser`, `requests`, `models.py` | `run_collectors.py` |
| `sources/front_page.py` | `front_page_consensus.py` | `feedparser`, `requests` | `front_page_consensus.py` |
| `tasks/run_collectors.py` | `radar.py` (background thread) | `sources/rss.py`, `pipeline.py`, `database.py`, `config/rss_sources.json` | `radar.py` |
| `tasks/front_page_consensus.py` | `radar.py` (background thread) | `sources/front_page.py`, `database.py`, `config/front_page_sources.json` | `radar.py` |
| `models.py` | `ai/analyzer.py`, `pipeline.py`, `sources/rss.py` | `pydantic` | Most backend files |
| `config/rss_sources.json` | `run_collectors.py` | — | All RSS scans |
| `config/front_page_sources.json` | `front_page_consensus.py` | — | Consensus scans |
| `frontend/src/lib/api.js` | `RadarDashboard.jsx` | Backend HTTP | `RadarDashboard.jsx` |
| `frontend/src/pages/RadarDashboard.jsx` | `App.jsx` | `api.js`, `SignalCard.jsx` | End user |
| `frontend/src/components/SignalCard.jsx` | `RadarDashboard.jsx` | `styles.css` (via className) | `RadarDashboard.jsx` |
| `frontend/src/styles.css` | `main.jsx` (import) | Google Fonts (CDN) | All UI |

---

## 3. Data Flow

### 3.1 Full RSS Scan

```
1. TRIGGER
   Analyst clicks "Refresh Reports" in the UI
   → fetchRecent POST /api/radar/run (api.js)
   → radar.py::run_scan() handler
   → spawns daemon thread: _run_scan_background()

2. COLLECTION
   tasks/run_collectors.py::run_all_collectors()
   → opens config/rss_sources.json (50+ feeds)
   → RSSCollector(feeds, limit=25)
   → for each feed: requests.get(url) → feedparser.parse(text)
   → sponsored/ad entries filtered by is_sponsored_entry()
   → Reddit URLs rewritten to old.reddit.com for reliability
   → returns List[RawPost] — each post carries source metadata fields

3. PRE-AI PRIORITIZATION
   posts.sort(key=pre_score_raw_post, reverse=True)
   → purely deterministic string scoring — NO LLM calls
   → Tier 1 keywords (conflict, constitutional, censorship, AI manipulation, corruption):
     score += min(hits, 4) × weight (2.0–3.0 per tier)
   → Source role bonus: geopolitical +4.0, censorship_watch +3.0, etc.
   → Penalties: celebrity/gossip -2.0/hit, sports -2.0/hit, outrage language -1.5/hit
   → Category penalty: sports or entertainment: -5.0 flat
   → Higher score = processed first; score floored at 0.0

4. QUOTA BUCKETING
   posts bucketed by feed_name (source)
   round-robin across sources, quota per category:
     geopolitical/investigative = 3 items max per source
     general/politics/economy = 2
     tech/science/sports = 1
   → prevents one high-volume feed from consuming all LLM slots

5. LLM ANALYSIS (per item, up to MAX_POSTS_TO_PROCESS=60)
   pipeline.process_item(raw_post)
   → ai/analyzer.py::analyze_item(text)
   → builds prompt: "You are AEGIS — a constitutional-watchdog signal analyzer"
   → POST http://127.0.0.1:11434/api/generate
     model: qwen2.5:7b, temperature: 0.1, format: json
   → extracts JSON: {topic, summary, framing, claims, signal_type,
     significance_raw (1–10), manipulation_risk, narrative_flags, filtered}
   → validates all fields — rejects hallucinated signal types and flag names
   → returns SignalAnalysis

6. DETERMINISTIC SCORING (pipeline.py::score_item)
   Inputs: SignalAnalysis + RawPost source metadata
   
   source_weight:
     if reliability_tier is set: tier_weight × editorial_role_weight, clamp [0.35, 1.25]
     else: legacy source_role lookup (baseline=1.00, geopolitical=1.15, etc.)
   
   constitutional_score: keyword match against _CONSTITUTIONAL_KW (0.0–1.0)
   censorship_score:     keyword match against _CENSORSHIP_KW (0.0–1.0)
   war_score:            keyword match against _WAR_KW (0.0–1.0)
   narrative_score:      manipulation_risk base + narrative_flags count boost
   low_sig_penalty:      keyword match against _LOW_SIGNIFICANCE_KW (celebrity etc.)
   ai_sig:               (significance_raw - 1) / 9.0 → normalized 0.0–1.0
   
   significance_score:
     raw = ai_sig×0.45 + constitutional×0.20 + war×0.15 + censorship×0.10 + narrative×0.10
     penalized = raw × (1.0 - low_sig_hit × 0.40)
     final = min(penalized × source_weight, 1.0)
   
   public_interest_score:
     = min(ai_sig×0.40 + constitutional×0.25 + censorship×0.20 + war×0.15, 1.0)
   
   trend_score: hardcoded 0.0 (reserved for Phase 6, social API not implemented)

7. DEDUPLICATION CHECK (database.py::insert_signal)
   Exact dedup: URL already in db → return existing, skip insert
   Exact dedup: external_id already in db → return existing, skip insert
   Near-dup dedup: title_norm (stop-word-stripped fingerprint)
     → if fingerprint matches any row where tracked=1 OR is_deleted=1 → skip
   Reason: prevents re-importing stories already saved or dismissed

8. STORAGE
   INSERT OR IGNORE INTO signals (...)
   All 30 columns populated from SignalItem.model_dump()
   title_norm computed and stored as dedup index field

9. SCAN COMPLETION
   scan_state["running"] = False, summary returned
   Frontend polls GET /api/radar/scan-status every 2.5 seconds
   When scan.running = False and scan.summary exists → loadData() refreshes UI
```

---

### 3.2 Keyword Scan

```
1. TRIGGER
   Analyst types query or clicks a Quick Scan preset
   → api.js::runSearchScan(query) → POST /api/radar/search-run
   → radar.py spawns daemon thread: _run_search_scan_background(query)

2. COLLECTION
   tasks/run_collectors.py::run_keyword_scan(query)
   → tokenizes query: split on whitespace/comma, min 2 chars per term
   → RSSCollector(feeds, limit=50) — higher per-feed limit than full scan
   → fetches ALL feeds (same as full scan)
   → filters: entry_matches(post) — any term found in title+body+source
   
3. PRE-AI PRIORITIZATION
   matching.sort(key=pre_score_raw_post, reverse=True)
   same scoring as full scan — SWAT-relevant matches processed first
   
4–8. IDENTICAL TO FULL SCAN
   Steps 5–8 are identical: LLM analysis, scoring, dedup, storage
   Note: keyword scan does NOT apply category quotas — all matching items
   compete purely on pre_score rank up to MAX_POSTS_TO_PROCESS=60

9. COMPLETION
   search_scan_state updated, frontend polls /search-status
   When complete, keyword message shows: "X found, Y saved"
```

---

### 3.3 Front Page Consensus Scan

```
1. TRIGGER
   Analyst clicks "Scan Front Pages"
   → api.js::runConsensusScan() → POST /api/radar/consensus-scan
   → radar.py spawns daemon thread: _run_consensus_background()

2. COLLECTION (NO LLM)
   tasks/front_page_consensus.py::run_front_page_consensus()
   → scan_id = f"{uuid4()}_{timestamp}"
   → opens config/front_page_sources.json (15 sources: 5 left, 5 center, 5 right)
   → FrontPageCollector.fetch() — fetches top 10 headlines per source
   → returns List[Dict]: {title, url, source_name, orientation, reliability_tier}
   → source failures are silently skipped — one dead feed doesn't abort scan

3. EVENT-IDENTITY CLUSTERING (Stage 12 Union-Find)
   _union_find_cluster(all_headlines)
   
   Pre-computation per headline:
     event_words = all significant words (4+ chars, not in stop list)
                   MINUS _HIGH_SALIENCE entities (trump, biden, president, congress, etc.)
     context_domain = dominant domain from _CONTEXT_KEYWORDS intersection
                      (legal / military / election / economic / diplomatic / social / general)
   
   Merge decision for each pair (i, j):
     Rule 1: if either headline has 0 event words → never merge
     Rule 2: shared event words ≥ 2 → merge (strong content similarity)
     Rule 3: 1 shared anchor word + same context domain → merge
              (anchor words = iran, ukraine, ceasefire, impeachment, etc.)
     Rule 4: all other cases → do not merge
   
   Result: List[List[Dict]] — each inner list is one event cluster

4. PER-SOURCE DEDUPLICATION
   _deduplicate_group(group)
   → max 1 article per outlet
   → sort preference: Tier-1 first, then center→left→right for orientation variety
   → prevents 5 NYT articles from dominating one cluster card

5. CONSENSUS SCORING
   _score_consensus(deduped_group)
   
   source_breadth = min(source_count / 10, 1.0) × 0.40
   
   orientation bonuses:
     left + center + right all present: +0.30 (full spectrum consensus)
     (left + center) or (center + right): +0.15
     left + right without center: +0.05
     only one orientation: no bonus
   
   tier bonuses:
     3+ Tier-1 sources: +0.20
     1–2 Tier-1 sources: +0.10
   
   consensus_tier:
     ≥ 0.70 → "confirmed"
     ≥ 0.45 → "elevated"
     ≥ 0.20 → "monitored"
     < 0.20 → "noise" (discarded, not stored)

6. STORAGE
   Top 10 clusters by consensus_score saved to front_page_consensus table
   Each row: scan_id, topic, keywords (JSON), headlines (JSON),
             source_count, left_count, center_count, right_count,
             tier1_count, consensus_score, consensus_tier
   
   topic label derived from event words only (never from high-salience entities)

7. COMPLETION
   consensus_scan_state updated
   Frontend polls /consensus-status every 2.5 seconds
   When complete: loadConsensus() fetches latest results
                  if archive is open: fetchConsensusArchive() refreshes snapshot list
```

---

### 3.4 Save to Library

```
1. TRIGGER
   Analyst clicks "Save to Library" on a Live Feed card
   → api.js::trackReport(id) → PATCH /api/radar/{id}/track
   → radar.py::track_signal(signal_id)
   → database.py::track_signal(id): UPDATE signals SET tracked = 1 WHERE id = ?

2. SIDE EFFECTS
   Item disappears from Live Feed:
     Live Feed fetches with liveOnly=true → tracked=0 filter → item excluded
   Item appears in Report Library:
     Library fetches with trackedOnly=true → tracked=1 filter → item included
   
3. DEDUP CONSEQUENCE (design-critical)
   title_norm is now in the dedup blocklist:
     future insert_signal() checks: WHERE title_norm = ? AND (tracked=1 OR is_deleted=1)
     near-duplicate stories will be skipped on all future scans
   
   This means: saving a story to the Library permanently suppresses
   future imports of near-identical stories from other sources or future scans.
   This is intentional — prevents the same saved story from cycling back.

4. UI RESPONSE
   On PATCH success: item removed from local items state (no full reload)
   "Save to Library" button only visible when viewMode === "live"
```

---

### 3.5 Delete Flow

```
1. TRIGGER (first click)
   Analyst clicks "Delete" on any card (live or library)
   → handleDelete(item): setPendingDeleteId(item.id)
   → card re-renders with "Delete this signal?" confirm/cancel inline
   → NO modal, NO window.confirm() (browsers can suppress)

2. CONFIRM (second click — "Yes, Delete")
   → handleConfirmDelete()
   → api.js::deleteSignal(id) → DELETE /api/radar/{id}
   → radar.py::delete_signal(signal_id)
   → database.py::delete(id): UPDATE signals SET is_deleted = 1 WHERE id = ?

3. LOCAL STATE UPDATE
   item removed from React items state immediately (no full reload)
   if item was in selectedIds: removed from selection Set

4. DEDUP CONSEQUENCE (same as Save to Library)
   title_norm is now in dedup blocklist:
     WHERE title_norm = ? AND (tracked=1 OR is_deleted=1)
   Future scans will not re-import near-identical stories
   
5. PERMANENCE
   Soft-delete only — row remains in database with is_deleted=1
   All queries carry WHERE is_deleted=0 — row never surfaces again
   No undo mechanism exists — this is intentional (see Section 10)
   
6. BULK DELETE
   Analyst checks multiple cards → bulk action bar appears
   "Delete Selected" → setBulkDeletePending(true) → confirm bar
   On confirm: serial DELETE calls for each id
   Failed ids tracked; UI reports count of failed deletes
```

---

## 4. Database Architecture

### File Location

```
market_radar.db
```

Resolved in `database.py`:
```python
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "market_radar.db"
```

This resolves to the project root regardless of current working directory — three directories up from `backend/app/db/database.py`.

Connection: `sqlite3.connect(path, check_same_thread=False)` — `check_same_thread=False` is required because background scan threads share the same `Database` instance that is instantiated at module load time in `radar.py`.

---

### Table: `signals`

Primary data store for all collected and scored news signals.

#### Schema (current — all columns including migrations)

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `id` | INTEGER PK AUTOINCREMENT | — | Row identifier |
| `title` | TEXT | `''` | Raw headline from feed |
| `source` | TEXT | `''` | Source domain/name (raw from feed) |
| `feed_name` | TEXT | NULL | Display name from `rss_sources.json` |
| `url` | TEXT UNIQUE | — | Article URL — primary exact dedup key |
| `external_id` | TEXT UNIQUE | — | Feed entry ID — secondary exact dedup key |
| `category` | TEXT | `''` | Feed category (geopolitical, censorship, etc.) |
| `source_type` | TEXT | `''` | `news`, `reddit`, etc. |
| `source_role` | TEXT | `''` | Legacy role: baseline, geopolitical, etc. |
| `source_orientation` | TEXT | `''` | center \| left \| right \| watchlist |
| `editorial_role` | TEXT | `''` | facts \| mixed \| analysis \| narrative |
| `reliability_tier` | INTEGER | 0 | 1–4 per Stage 10 model |
| `topic` | TEXT | `''` | LLM-extracted topic (1–2 sentences) |
| `summary` | TEXT | `''` | LLM-extracted neutral summary |
| `framing` | TEXT | `''` | LLM-detected editorial framing angle |
| `claims` | TEXT | `''` | LLM-extracted specific factual claims |
| `signal_type` | TEXT | `''` | verified_news \| narrative_pulse \| narrative_integrity |
| `significance_score` | REAL | 0.0 | Master significance (0.0–1.0) |
| `trend_score` | REAL | 0.0 | Reserved (always 0.0 — Phase 6) |
| `constitutional_score` | REAL | 0.0 | Constitutional/civil liberties relevance |
| `censorship_score` | REAL | 0.0 | Press freedom / censorship relevance |
| `war_score` | REAL | 0.0 | Armed conflict relevance |
| `narrative_score` | REAL | 0.0 | Manipulation / narrative risk |
| `public_interest_score` | REAL | 0.0 | Broad civic relevance composite |
| `source_weight` | REAL | 0.5 | Source credibility multiplier used in scoring |
| `manipulation_risk` | TEXT | `'low'` | low \| medium \| high |
| `narrative_flags` | TEXT | `''` | JSON-serialized List[str] of anomaly flags |
| `filtered` | INTEGER | 0 | 1 = spam/gibberish, excluded from normal views |
| `filter_reason` | TEXT | `''` | Why item was filtered |
| `is_deleted` | INTEGER | 0 | 1 = soft-deleted, excluded from all views |
| `tracked` | INTEGER | 0 | 1 = saved to Report Library |
| `title_norm` | TEXT | `''` | Stop-word-stripped dedup fingerprint |
| `created_at` | TIMESTAMP | CURRENT_TIMESTAMP | Intake timestamp |

#### Indexes

| Index | Column | Purpose |
|-------|--------|---------|
| (implicit) | `url` UNIQUE | Fast exact URL dedup on insert |
| (implicit) | `external_id` UNIQUE | Fast exact ID dedup on insert |
| `idx_signals_title_norm` | `title_norm` | Fast near-duplicate title lookup at intake |

#### Deduplication Mechanics

**Level 1 — Exact URL:** `get_by_url(url)` called before any insert. If a row exists with that URL, `insert_signal()` returns the existing row immediately — no insert, no LLM call wasted.

**Level 2 — Exact external_id:** Same pattern for feed entry IDs.

**Level 3 — Near-duplicate title (Stage 9):**
```python
title_norm = _normalize_title(item["title"])
# normalize: lowercase, strip punctuation, drop stop words, keep first 10 significant words
blocked = conn.execute(
    "SELECT id FROM signals WHERE title_norm = ? AND (tracked = 1 OR is_deleted = 1) LIMIT 1",
    (title_norm,)
)
if blocked: return None  # skip — near-identical story already in Library or deleted
```

This is the most important dedup mechanism for the analyst UX:
- Stories saved to Library (`tracked=1`) suppress future near-duplicates → same story doesn't cycle back
- Stories deleted (`is_deleted=1`) suppress future near-duplicates → dismissed stories stay dismissed

**What `title_norm` looks like:**
- Input: `"Trump Signs Executive Order Targeting Federal Employees, Officials Say"`
- Output: `"trump signs executive order targeting federal employees officials"` (stops removed, lowercased, first 10)

#### `tracked` and `is_deleted` State Machine

```
NEW ITEM INSERTED
  tracked=0, is_deleted=0
      │
      ├── analyst clicks "Save to Library"
      │     → tracked=1, is_deleted=0
      │     → appears in Library, removed from Live Feed
      │     → title_norm now in dedup blocklist (tracked=1)
      │
      ├── analyst clicks "Delete" (from Live Feed)
      │     → is_deleted=1, tracked=0
      │     → hidden from all views
      │     → title_norm now in dedup blocklist (is_deleted=1)
      │
      └── analyst clicks "Delete" (from Library)
            → is_deleted=1, tracked=1 (tracked preserved)
            → hidden from all views
            → title_norm still in dedup blocklist
```

#### Schema Migration Strategy

New columns are added via `ensure_columns()` which runs at every startup:

```python
def ensure_columns(self):
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(signals)")}
    with conn:
        if "new_column" not in existing:
            conn.execute("ALTER TABLE signals ADD COLUMN new_column TYPE DEFAULT value")
```

This is safe against existing databases — it only adds missing columns, never drops or modifies existing ones. All new columns have safe defaults so existing rows are unaffected.

---

### Table: `front_page_consensus`

Stores results from Front Page Consensus scans. Each scan writes a batch of rows sharing the same `scan_id`.

#### Schema

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `id` | INTEGER PK AUTOINCREMENT | — | Row identifier |
| `scan_id` | TEXT NOT NULL | — | UUID + timestamp identifying one scan batch |
| `topic` | TEXT NOT NULL | — | Event label derived from event words (not entity names) |
| `keywords` | TEXT | `'[]'` | JSON array of top 10 event words for this cluster |
| `headlines` | TEXT | `'[]'` | JSON array of up to 8 headline objects: {title, source_name, orientation, url} |
| `source_count` | INTEGER | 0 | Number of distinct outlets in this cluster |
| `left_count` | INTEGER | 0 | Number of left-orientation sources |
| `center_count` | INTEGER | 0 | Number of center-orientation sources |
| `right_count` | INTEGER | 0 | Number of right-orientation sources |
| `tier1_count` | INTEGER | 0 | Number of Tier-1 (wire service) sources |
| `consensus_score` | REAL | 0.0 | Composite editorial consensus score (0.0–1.0) |
| `consensus_tier` | TEXT | `''` | confirmed \| elevated \| monitored \| noise |
| `created_at` | TIMESTAMP | CURRENT_TIMESTAMP | Scan timestamp |

#### Indexes

| Index | Column | Purpose |
|-------|--------|---------|
| `idx_fp_scan_id` | `scan_id` | Fast scan_id grouping for archive queries |

#### Archive Query Pattern

```sql
-- Get all distinct scans (newest first) for archive list
SELECT scan_id, MIN(created_at) AS created_at, COUNT(*) AS cluster_count
FROM front_page_consensus
GROUP BY scan_id
ORDER BY MIN(created_at) DESC

-- Get all clusters for one scan
SELECT * FROM front_page_consensus
WHERE scan_id = ?
ORDER BY consensus_score DESC
```

---

## 5. Frontend Architecture

### Component Tree

```
main.jsx
  └── App.jsx
        └── RadarDashboard.jsx (all state lives here)
              ├── ConsensusCard (local component, defined in RadarDashboard.jsx)
              └── SignalCard.jsx (imported component)
```

### State Ownership (`RadarDashboard.jsx`)

All application state lives in `RadarDashboard`. There is no global state manager (no Redux, no Context API for data). Every state variable is a React `useState` hook.

#### Complete State Inventory

| State Variable | Type | Purpose |
|----------------|------|---------|
| `items` | `Array` | All signals fetched from backend for current view |
| `loading` | `boolean` | Shows loading indicator |
| `scanning` | `boolean` | Full RSS scan in progress |
| `keywordScanning` | `boolean` | Keyword scan in progress |
| `consensusScanning` | `boolean` | Consensus scan in progress |
| `error` | `string` | Error message (cleared on next successful action) |
| `scanMessage` | `string` | Status message for full scan |
| `keywordMessage` | `string` | Status message for keyword scan |
| `consensusMessage` | `string` | Status message for consensus scan |
| `searchQuery` | `string` | Value of the feed-scan input (drives keyword scans) |
| `sortQuery` | `string` | Local text filter (never triggers a scan) |
| `lastQuickScan` | `string\|null` | Label of last Quick Scan preset used |
| `sortMode` | `"significance"\|"recency"` | Sort order for signal list |
| `showFiltered` | `boolean` | Whether to include noise/filtered items |
| `pendingDeleteId` | `number\|null` | Card ID awaiting inline delete confirmation |
| `selectedIds` | `Set<number>` | IDs checked for bulk operations |
| `bulkDeletePending` | `boolean` | Bulk delete confirmation bar visible |
| `activeView` | `"live"\|"library"\|"consensus"\|"archive"` | Current dashboard tab |
| `expandedClusters` | `Set<number>` | Which compressed clusters are manually expanded |
| `unclusteredExpanded` | `boolean` | Whether the "Other Reports" footer section is expanded |
| `consensusData` | `Array` | Consensus cluster results for current/selected scan |
| `consensusScannedAt` | `string\|null` | Timestamp of displayed consensus scan |
| `consensusArchive` | `Array` | List of all historical scan snapshots |
| `showArchive` | `boolean` | Whether archive panel is visible |
| `archiveLoading` | `boolean` | Archive list fetch in progress |
| `selectedScanId` | `string\|null` | Which archive snapshot is being viewed (null = latest) |

### View Switching

`activeView` controls which content block renders. Switching views:

1. `switchView(newView)` called on tab click
2. Sets `activeView`
3. Resets `sortQuery`, `lastQuickScan`, `scanMessage`, `keywordMessage`
4. Calls `loadData(showFiltered, newView)` which passes `trackedOnly` or `liveOnly` to the API

View-to-API mapping:
```
activeView === "live"      → fetchRecent(100, showFiltered, false, true)   [liveOnly]
activeView === "library"   → fetchRecent(100, showFiltered, true, false)   [trackedOnly]
activeView === "consensus" → no fetchRecent; shows consensusData state
activeView === "archive"   → no fetchRecent; shows consensusArchive state
```

### Scan Polling

Each scan type uses a `useEffect` with `setInterval(fn, 2500)` that runs while the scan is active. The `useEffect` returns `clearInterval` as cleanup so polling stops on component unmount or when the scan flag becomes false.

```javascript
useEffect(() => {
  if (!scanning) return;
  const interval = setInterval(() => checkScanStatus(), 2500);
  return () => clearInterval(interval);
}, [scanning]);
```

Three independent polling loops: `scanning`, `keywordScanning`, `consensusScanning`.

### Client-Side Signal Clustering

Two `useMemo` hooks transform `items` into a clustered, scored display list.

#### Step 1: Filter + Sort (`filteredItems`)
```
items
  → if sortQuery: filter to items containing query text in title/topic/summary/etc.
  → if sortMode === "significance": sort by significance_score DESC
  → else: preserve API order (recency)
```

#### Step 2: Cluster (`clusters`)
```
filteredItems → clusterSignals(filteredItems)
```

`clusterSignals()` uses Union-Find:
- For each pair (i, j), compute shared words from `getSignalWords(signal)` (topic + title + summary, lowercase, punctuation stripped, 4+ chars, not in STOP_WORDS)
- If both signals have `significance_score ≥ 0.55`: threshold = 1 shared word (high-sig stories share fewer distinctive words)
- Otherwise: threshold = 2 shared words
- Union-Find path compression for O(α(n)) performance
- Returns grouped arrays sorted by group size (largest first)
- Groups of 1 get `label: null`; multi-groups get `label: top3words.join(" · ")`

#### Step 3: Score Clusters (`scoredClusters`)
```
clusters → clusters.map(c => ({...c, ...scoreCluster(c)}))
```

`scoreCluster()` produces `{cluster_importance, cluster_tier, cluster_reason}`:
- `maxSig × 0.40 + avgSig × 0.20` (backbone)
- Item count bonus: ≥5 +0.15, ≥3 +0.10, ≥2 +0.05
- Unique source count: `min(uniqueSources/5, 1) × 0.10`
- Front-page keyword boost: accumulates up to +0.50 (each hit × 0.18)
- Section keyword boost: accumulates up to +0.20 (each hit × 0.08)
- Back-page penalty: -0.25 on any entertainment/consumer keyword match
- Corroboration bonus: left+center+right: +0.20; partial: +0.10; 2+ Tier-1: +0.20; 1 Tier-1: +0.10
- Reliability cap: all-Tier-4: cap 0.59; all Tier-3+: cap 0.79
- Cluster tier thresholds: `front_page`≥0.80, `major`≥0.60, `section`≥0.40, `back_page`≥0.20, `noise`<0.20

#### Display Split
```
mainClusterList:    scoredClusters where cluster_importance ≥ 0.20, sorted by importance DESC
unclusteredSignals: scoredClusters where cluster_importance < 0.20, flattened, sorted by sig score
```

Compressed clusters: clusters with `cluster_tier === "back_page" || "noise"` AND `signals.length ≥ 3` are rendered collapsed. User can expand with `toggleClusterExpand(i)`.

### Archive Behavior

When `showArchive` becomes `true`:
1. `fetchConsensusArchive()` → `GET /consensus/archive` → list of `{scan_id, created_at, cluster_count}`
2. Displayed as a list of clickable snapshot entries
3. Clicking a snapshot: `handleLoadSnapshot(scanId)` → `fetchConsensusSnapshot(scanId)` → loads that scan's clusters into `consensusData`
4. "View Current Scan" button: `handleViewCurrentScan()` → `loadConsensus()` → resets to latest scan

---

## 6. Backend Architecture

### `backend/app/app.py` — Application Factory

Single responsibility: create and configure the FastAPI application.

```python
app = FastAPI(title="SWAT Signal Desk API", version="1.0.0")
# CORS: allows only 127.0.0.1:5175 and localhost:5175
# Router: mounts radar_router at prefix /api/radar
# Health: GET /health → {"status": "ok"}
```

This file has no business logic. Changes here affect: allowed origins (CORS), route prefix, app metadata. The `app` object is imported by `main.py` and referenced by uvicorn.

---

### `backend/app/api/routes/radar.py` — Route Handlers

All API surface for the application. Three independent scan state systems, each with their own lock and state dict.

#### Threading Model

```
Module load time:
  db = Database()          ← singleton, shared across all requests and threads
  scan_state = {...}       ← module-level dict, protected by scan_lock
  search_scan_state = {...} ← protected by search_scan_lock
  consensus_scan_state = {...} ← protected by consensus_scan_lock

On POST /run:
  if scan_state["running"]: return "already_running"
  else: Thread(target=_run_scan_background, daemon=True).start()
```

Daemon threads: `daemon=True` means the thread is killed when the main process exits. This prevents orphaned threads from keeping the process alive after shutdown.

Locks (`threading.Lock()`): Each scan type has its own lock for reading/writing its state dict. Locks are not held during the actual scan work — only during state dict updates. This means multiple scan types can run concurrently (full scan + consensus scan can overlap).

---

### `backend/app/core/pipeline.py` — Scoring Engine

`SignalPipeline.process_item(raw_post: RawPost) → SignalItem`

Two sequential steps:
1. `analyze_item(text)` — LLM call → `SignalAnalysis`
2. `score_item(analysis, raw_post)` — deterministic scoring → scores dict

The `score_item()` function is pure: same inputs always produce same outputs. No I/O, no randomness, no state. All scoring happens here — the LLM only produces the raw fields (topic, summary, significance_raw, etc.) that this function then transforms into calibrated scores.

---

### `backend/app/db/database.py` — Persistence Layer

`Database` class is instantiated once at module load in `radar.py` and shared across all route handlers and background threads. SQLite's `check_same_thread=False` is required for this sharing pattern.

Startup sequence on instantiation:
1. `sqlite3.connect(path, check_same_thread=False)`
2. `row_factory = sqlite3.Row` — enables column-name access on rows
3. `ensure_tables()` — creates signals and front_page_consensus tables if missing
4. `ensure_columns()` — adds any missing columns via ALTER TABLE

---

### `tasks/run_collectors.py` — Scan Orchestrator

No FastAPI dependency — pure Python. Called by background threads in `radar.py`.

Two public functions:
- `run_all_collectors()` → full scan, returns summary dict
- `run_keyword_scan(query: str)` → targeted scan, returns summary dict

Hard limits (both functions):
- `MAX_POSTS_TO_PROCESS = 60` — absolute cap on LLM calls per scan
- `MAX_RUNTIME_SECONDS = 240` — hard wall clock timeout

The pre-score + quota system ensures these 60 slots go to the most SWAT-relevant content.

---

### `tasks/front_page_consensus.py` — Consensus Engine

No LLM dependency — entirely deterministic. Uses only:
- `sources/front_page.py` for RSS fetching
- `backend/app/db/database.py` for storage
- Python standard library for clustering

The separation from `run_collectors.py` is intentional — consensus scanning and signal scanning are independent workflows that should not block each other. They use separate API routes, separate scan state dicts, and separate database tables.

---

## 7. Source Intelligence Model

### Two Source Lists

| File | Feeds | Used By | Has |
|------|-------|---------|-----|
| `config/rss_sources.json` | 50+ feeds | `run_collectors.py` (full + keyword scans) | Full metadata |
| `config/front_page_sources.json` | 15 feeds | `front_page_consensus.py` | orientation + tier only |

---

### `rss_sources.json` — Full Source Metadata

Each entry structure:
```json
{
  "name": "Associated Press",
  "url": "https://feeds.apnews.com/...",
  "category": "general",
  "source_type": "news",
  "source_role": "baseline",
  "source_orientation": "center",
  "editorial_role": "facts",
  "reliability_tier": 1
}
```

#### `source_orientation` — Editorial Lean

| Value | Meaning | Examples |
|-------|---------|---------|
| `center` | No consistent partisan lean | AP, BBC, NPR, The Hill |
| `left` | Consistent left-of-center editorial pattern | Guardian, ProPublica, Intercept |
| `right` | Consistent right-of-center editorial pattern | Reason, Washington Examiner |
| `watchlist` | State-narrative, fringe, social, low-verified | Reddit, RT |

Used by: cluster scoring (corroboration bonus), consensus scoring (orientation spread counts), display (orient pills on consensus cards).

#### `editorial_role` — Output Type

| Value | Meaning | Weight Multiplier |
|-------|---------|-----------------|
| `facts` | Wire-style primary fact reporting | 1.10 |
| `mixed` | Reporting + analysis combined | 1.00 |
| `analysis` | Commentary, opinion, analysis | 0.90 |
| `narrative` | Advocacy, framing, social pulse | 0.75 |

Used by: `pipeline.py::_compute_source_weight()` — combined with `reliability_tier` to form final source_weight.

#### `reliability_tier` — Verification Confidence

| Tier | Meaning | Examples | Weight |
|------|---------|---------|--------|
| 1 | Wire services, major broadcast | AP, BBC, Reuters | 1.15 |
| 2 | Established reporting | NPR, Guardian, Al Jazeera, ProPublica | 1.00 |
| 3 | Partisan / analysis / advocacy | Reason, Intercept, Reclaim the Net | 0.75 |
| 4 | Watchlist / social / low-confidence | Reddit, RT, fringe outlets | 0.45 |

Used by: source_weight calculation, cluster scoring (tier-1 bonuses), consensus scoring (tier1_count), reliability caps in cluster scoring.

#### `source_role` — Legacy Operational Role

| Value | Weight | Notes |
|-------|--------|-------|
| `baseline` | 1.00 | Wire services |
| `geopolitical` | 1.15 | Conflict/foreign-policy focused |
| `censorship_watch` | 1.10 | Press freedom monitors |
| `ai_watch` | 1.00 | AI/disinformation trackers |
| `independent` | 0.85 | Quality independent outlets |
| `public` | 0.55 | Reddit and social aggregators |

Used only as fallback when `reliability_tier` is absent. All new sources should use `reliability_tier` + `editorial_role` instead.

#### `category` — Content Domain

Used for per-category quota enforcement in `run_collectors.py`:
- `geopolitical`, `investigative`: 3 items/source per scan
- `censorship`, `ai_watch`, `general`, `politics`, `economy`, `local`: 2 items/source
- `technology`, `science`, `sports`, `public_signal`: 1 item/source

Also used in `pre_score_raw_post()` for source role bonus (geopolitical: +3.0, censorship: +2.5, investigative: +2.5) and category penalties (sports/entertainment: -5.0 flat).

---

### Weighting Formula

```python
# Stage 10 (preferred path — requires reliability_tier)
tier_weight = {1: 1.15, 2: 1.00, 3: 0.75, 4: 0.45}[reliability_tier]
role_weight = {"facts": 1.10, "mixed": 1.00, "analysis": 0.90, "narrative": 0.75}[editorial_role]
source_weight = clamp(tier_weight × role_weight, 0.35, 1.25)

# Legacy fallback (when reliability_tier absent)
source_weight = {"baseline": 1.00, "geopolitical": 1.15, "censorship_watch": 1.10,
                 "ai_watch": 1.00, "independent": 0.85, "public": 0.55}.get(source_role, 0.70)

# Applied in pipeline.py::score_item()
significance_score = min(raw_significance × source_weight, 1.0)
```

**Why weighting exists:** A Tier-4 social source (Reddit) can surface genuinely important information. Rather than filtering it out, AEGIS reduces its confidence multiplier. If the same story appears in Reddit (Tier 4, weight ~0.45) and AP (Tier 1, weight ~1.15), the AP item will have a significantly higher significance_score — placing it higher in sorted views and more likely to reach the FRONT_PAGE cluster tier.

---

### `config/front_page_sources.json` — Consensus Source List

15 curated sources chosen to span the editorial spectrum:

| Orientation | Sources |
|-------------|---------|
| Left (Tier 2) | CNN, New York Times, Washington Post, The Guardian, Politico |
| Center (Tier 1-2) | Associated Press (T1), BBC News (T1), NPR (T2), The Hill (T2), PBS NewsHour (T2) |
| Right (Tier 2-3) | Fox News (T2), Washington Examiner (T3), National Review (T3), Daily Wire (T3), The Free Press (T3) |

These sources are specifically chosen so that left + center + right consensus detection is meaningful. When AP, BBC, CNN, Fox News, and National Review all lead with the same story, that is genuine cross-spectrum editorial consensus.

---

## 8. Runtime Environment

### Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend language | Python | 3.11+ (f-strings, `match` syntax used) |
| Web framework | FastAPI | latest (`requirements.txt` is empty — install manually) |
| ASGI server | uvicorn | standard |
| Data validation | Pydantic v2 | `model_dump()` not `.dict()` |
| Database | SQLite (stdlib) | No ORM — raw SQL |
| Feed parsing | feedparser | latest |
| HTTP client | requests | latest |
| LLM runtime | Ollama | local |
| LLM model | qwen2.5:7b | local via Ollama |
| Frontend framework | React | latest |
| Build tool | Vite | latest |
| CSS | Plain CSS (no framework) | — |

### Ports

| Service | Port | Configured In |
|---------|------|--------------|
| FastAPI backend | **8002** | `main.py` (uvicorn), `app.py` (CORS), `api.js` (BASE_URL) |
| Vite dev server | **5175** | `vite.config.js`, `package.json`, `app.py` (CORS origins) |
| Ollama API | **11434** | `ai/analyzer.py` (`OLLAMA_URL`) |

### Startup Order

The services are independent but have a logical dependency order:

```
1. Ollama (prerequisite for scans — but not for serving existing data)
   ollama serve          ← starts Ollama daemon
   ollama pull qwen2.5:7b ← first-time model download only

2. Backend (must start before frontend makes API calls)
   cd d:\ARC NEXUS LLC\AEGIS
   python main.py        ← starts FastAPI on port 8002

3. Frontend (can start in any order, but API calls fail until backend is up)
   cd frontend
   npm run dev           ← starts Vite on port 5175
```

Browser access: `http://127.0.0.1:5175`

### Runtime Dependencies

```
Backend requires:
  - Python 3.11+ in PATH (or virtualenv activated)
  - fastapi, uvicorn, feedparser, requests, pydantic installed
  - market_radar.db writable (auto-created if missing)
  - config/rss_sources.json present
  - config/front_page_sources.json present
  - CWD = project root (relative paths in run_collectors.py, front_page_consensus.py)

Frontend requires:
  - Node.js + npm
  - node_modules/ installed (npm install)
  - Backend running on 8002

Scans additionally require:
  - Ollama running on 11434
  - qwen2.5:7b model pulled
  - Internet access for RSS feed fetching
```

### Python Path Note

All module imports use package paths rooted at the project root:
```python
from backend.app.db.database import Database
from tasks.run_collectors import run_all_collectors
from sources.rss import RSSCollector
```

Python must be launched from the project root so these paths resolve. Running `python backend/app/api/routes/radar.py` directly will fail — always use `python main.py` from the root.

---

## 9. Critical Files

These files have disproportionate impact on system behavior. Mistakes here can silently corrupt the system or cause failures that are difficult to trace.

---

### `backend/app/db/database.py`

**Why it matters:** Every piece of data that enters or leaves the system passes through this file. The schema, dedup logic, and query methods define what the analyst sees.

**What breaks if modified incorrectly:**

| Mistake | Consequence |
|---------|------------|
| Adding `DROP COLUMN` or `DROP TABLE` | Destroys data. No recovery without backup. |
| Removing `is_deleted = 0` from queries | Deleted signals reappear in UI |
| Removing `is_deleted` or `tracked` from dedup check | Near-duplicate stories re-import after deletion/save |
| Changing `check_same_thread=False` | SQLite threading errors in background scan threads |
| Modifying `ensure_tables()` column types | May conflict with existing data types in DB |
| Hard-deleting `is_deleted=1` rows | Removes dedup blocklist entries → dismissed stories cycle back |
| Changing `row_factory = sqlite3.Row` | All `row_to_dict()` calls return tuples instead of dicts |

---

### `backend/app/api/routes/radar.py`

**Why it matters:** Every UI action calls a route here. Route paths must exactly match `api.js`. The scan state dicts are the only way the frontend knows if a scan is running.

**What breaks if modified incorrectly:**

| Mistake | Consequence |
|---------|------------|
| Changing route path strings | Frontend gets 404 errors; buttons silently fail |
| Removing scan state locks | Race conditions — multiple scans can corrupt shared state dicts |
| Making `daemon=False` on scan threads | Threads block process shutdown |
| Removing error handling on scan threads | Unhandled exception leaves `scan_state["running"] = True` forever |
| Modifying state dict keys | Frontend polling breaks — checks for `scan.running`, `scan.summary`, `scan.error` |

---

### `tasks/front_page_consensus.py`

**Why it matters:** The Stage 12 clustering algorithm was the result of multiple debugging cycles. Its complexity is deliberate.

**What breaks if modified incorrectly:**

| Mistake | Consequence |
|---------|------------|
| Removing from `_HIGH_SALIENCE` | High-frequency entities (trump, president) over-merge unrelated stories |
| Lowering merge threshold from 2 to 1 | Stage 11 regression — mega-clusters with unrelated stories |
| Removing context domain check from `_should_merge()` | Cross-domain false merges (Iran sanctions ← → Iran military strike) |
| Changing `_event_words()` to not strip `_HIGH_SALIENCE` | Same as removing from blocklist |
| Removing `_deduplicate_group()` | One outlet (e.g., NYT) can have 5 articles in one cluster card |

---

### `frontend/src/pages/RadarDashboard.jsx`

**Why it matters:** All UI state lives here. View switching, clustering, scan polling, archive display — all coordinated from this one component.

**What breaks if modified incorrectly:**

| Mistake | Consequence |
|---------|------------|
| Nesting a view block inside another view's conditional | That view renders nothing when selected |
| Removing `clearInterval` from `useEffect` cleanup | Memory leak; stale poll updates after unmount |
| Adding filter state without updating `useMemo` deps | Stale renders — filter appears to not work |
| Using `//` comments inside JSX return block | Build-breaking parse error |
| Changing `activeView` initial value from `"library"` | UI starts on wrong tab |
| Breaking `clusterSignals()` or `scoreCluster()` | All cluster tiering and importance scoring breaks |

---

### `frontend/src/lib/api.js`

**Why it matters:** Single source of truth for all backend URLs. A path mismatch here breaks every feature that depends on that route.

**What breaks if modified incorrectly:**

| Mistake | Consequence |
|---------|------------|
| Changing `BASE_URL` port | Every API call fails |
| Mismatching path string with `radar.py` route | That specific feature 404s silently |
| Removing error propagation from `requestJson()` | API errors swallowed, UI appears to work but data not saved |
| Breaking `fetchConsensusArchive()` return parsing | Archive panel shows empty even with data |

---

### `config/rss_sources.json`

**Why it matters:** Every field in every entry is mapped directly into `RawPost` and persisted to the DB. This file governs source weighting for all future scans.

**What breaks if modified incorrectly:**

| Mistake | Consequence |
|---------|------------|
| Setting `reliability_tier` as string instead of integer | `int()` cast in `rss.py` fails; source gets tier=0 |
| Removing `url` field from an entry | Feed silently skipped |
| Invalid `source_orientation` value | No bonus/penalty but breaks consensus orientation counts |
| Malformed JSON (trailing comma, etc.) | `json.load()` throws; entire scan fails to start |

---

### `frontend/src/styles.css`

**Why it matters:** Card border colors and significance badges depend on CSS attribute selectors matching exactly what JSX sets.

**What breaks if modified incorrectly:**

| Mistake | Consequence |
|---------|------------|
| Renaming `data-significance` CSS selector | All significance-colored card borders revert to default |
| Renaming `.sig-score-badge.medium/high/critical` | Significance badges lose color |
| Removing `.opp-card--compact` styles | Compressed cluster lead cards display unstyled |
| Removing `.consensus-tier-*` selectors | Consensus cards lose tier color coding |
| Changing `--bg-main` or layout tokens | Entire dashboard visual appearance breaks |

---

## 10. Architectural Decisions

### Why Soft Delete Exists

Permanently deleting a row from SQLite would remove the `title_norm` fingerprint from the deduplication blocklist. The next scan would re-import the same story as if it had never existed, undoing the analyst's dismiss action. Soft delete (`is_deleted=1`) keeps the fingerprint in place while hiding the row from all queries. This is the only way to implement "dismiss permanently" without an explicit denied-list table.

---

### Why Tracked Reports Block Re-Import

When an analyst saves a story to the Library, they have made an editorial decision that this story matters. Re-importing the same story (perhaps from a different outlet covering the same event) would create Library clutter and confuse the analyst's curated collection. The `title_norm` dedup check prevents near-duplicates from re-entering the system once a canonical version has been saved.

---

### Why Front Page Consensus Is a Separate Engine

The main RSS pipeline processes 50+ feeds through an LLM, scoring each item individually. The Front Page Consensus engine has completely different goals: it asks "what are editors choosing to lead with?" — a structural question about the news ecosystem rather than a content-level question about individual articles. It requires no LLM, uses a different source list, stores in a separate table, and produces different output (cluster cards with orientation counts rather than individual scored signals). Merging them would couple two fundamentally different workflows and make both harder to maintain.

---

### Why the Consensus Archive Exists

The Front Page Consensus captures a snapshot of what front pages looked like at one moment in time. This is perishable data — by the next scan, the same outlets may be leading with different stories. The archive stores every scan's results so the analyst can compare editorial consensus over time: "What were front pages leading with yesterday morning vs. this morning?" Without the archive, every new scan would overwrite the previous one.

---

### Why Event Identity Clustering Exists (Stage 12)

Stage 11 used any-word overlap for clustering. The root cause failure: "trump" appeared in 80% of all political headlines. Any story mentioning Trump would cluster with every other Trump-mentioning story regardless of the actual event — Iran strikes, DOJ investigation, immigration ruling, and poll results would all merge into one massive card because they all share "trump." Stage 12 solves this by stripping high-frequency entities from the comparison set, requiring either 2+ meaningful event words to overlap OR 1 anchor word within the same narrative context domain.

---

### Why Source Weighting Exists

Without weighting, a Reddit post saying "I think war is about to start" and an AP wire dispatch saying "US Central Command confirms airstrike" would receive the same raw significance score from the LLM (both mention "airstrike", "military", etc.). Source weighting recognizes that the same factual information has different confidence levels depending on who reported it. A Tier-1 wire service confirming an event is qualitatively different from social speculation. Weighting propagates that confidence into the significance_score so the AP item ranks higher in sorting and more easily reaches front-page cluster tier.

---

### Why Local Ollama Is Used

AEGIS is a single-analyst, local-machine tool. Using a cloud LLM API would: (1) send potentially sensitive news analysis data to third-party servers, (2) incur per-call costs that accumulate over hundreds of daily analyses, (3) require internet connectivity even for processing, and (4) introduce latency and rate-limit dependencies. Local Ollama with qwen2.5:7b provides adequate quality for structured JSON extraction at near-zero marginal cost with full data locality.

---

### Why SQLite Was Chosen

The system has one user on one machine. SQLite is:
- Zero-configuration (no server process)
- Included in Python stdlib (no additional dependency)
- Sufficient for read/write patterns of a single-analyst tool
- Simple to back up (single file copy)
- Supports the full SQL feature set needed

The only requirement for thread safety is `check_same_thread=False` since multiple background scan threads share one connection. SQLite's file-level locking handles concurrent writes without additional infrastructure.

---

### Why Pre-AI Prioritization Exists

With 50+ feeds contributing up to 25 items each (1,250 potential items), and a per-scan cap of 60 LLM calls, naive round-robin would give each feed roughly 1 processed item. An AP wire story about a NATO Article 5 invocation and a TechCrunch gadget review would both receive exactly one LLM slot. Pre-scoring using fast keyword matching (no LLM, no I/O, <1ms per post) ensures the 60 LLM slots go to the highest-signal content across all feeds — conflict, constitutional, censorship, corruption — before tech/sports/entertainment content consumes quota.

---

## 11. Failed Approaches

### One-Word Clustering (Stage 11 Consensus)

**Tried:** Front page headlines were clustered by ANY shared significant word (4+ chars, not stop word).

**Failure:** "trump" appeared in ~80% of headlines. Every political story got merged into a single mega-cluster regardless of event. The cluster card for "Iran strikes US base" would also contain E. Jean Carroll verdict, DOJ antitrust probe, and 2024 poll numbers — all sharing only "trump." The topic label became "trump iran strikes" even when Trump had no role in the Iran event.

**Replaced by:** Stage 12 — `_HIGH_SALIENCE` blocklist strips high-frequency entities before comparison. Merge requires 2+ shared event words OR 1 anchor word within the same context domain.

---

### Consensus Without Archive

**Tried:** Front Page Consensus scan results were stored in a single "latest" record, overwritten on each new scan.

**Failure:** Every new scan destroyed the previous results. The analyst had no way to compare what outlets were leading with an hour ago vs. now. Trend analysis (is this story growing or fading?) was impossible.

**Replaced by:** Archive model — each scan generates a UUID `scan_id`, all clusters saved with that ID. `get_consensus_archive()` returns all distinct scan IDs. `get_consensus_by_scan_id()` retrieves any historical snapshot.

---

### Library/Live Feed Mixing

**Tried:** Fetching all signals (tracked=0 and tracked=1) together and letting the user filter in-UI by a saved/unsaved toggle.

**Failure:** The distinction between "triage inbox" (live feed) and "curated archive" (library) was lost. The analyst had to mentally filter while triaging. Bulk operations on the live feed risked accidentally affecting saved library items.

**Replaced by:** Hard separation via `liveOnly` and `trackedOnly` API parameters. Two distinct views with separate fetch calls. The Library and Live Feed never mix in the same query.

---

### Simple Source Counting for Consensus Score

**Tried:** Consensus score = `source_count / total_sources` — purely count-based. More sources = higher consensus.

**Failure:** A story covered by 5 Daily Wire sister sites (all Tier-3 right) would outscore a story covered by AP + BBC + NPR (Tier-1/2 center). Quantity without quality produced misleading consensus signals.

**Replaced by:** Multi-factor consensus score: source breadth as baseline (`min(source_count/10, 1.0) × 0.40`), orientation spread bonus (left+center+right: +0.30), tier-1 presence bonus (+0.10/+0.20). Note: reliability caps were removed from the Python consensus engine but remain in the client-side `scoreCluster()` in `RadarDashboard.jsx`.

---

### Lowered Clustering Threshold for High-Significance Pairs

**Tried (initially):** In the client-side `clusterSignals()`, the threshold for high-sig pairs was initially set to 1 shared word for all pairs regardless of significance.

**Failure:** Even at threshold=1, low-significance items about unrelated topics would merge if they shared any common significant word. "Iran" + "market" appearing in both a war story and an oil prices story would incorrectly merge them.

**Replaced by:** Threshold reduction (`2 → 1`) only when BOTH items have `significance_score ≥ 0.55`. This is a narrow window where two genuinely high-significance geopolitical stories correctly merge even when their vocabulary overlap is low ("Iran strikes Kuwait" and "Central Command responds to Iran" share only "iran" and "central" but are the same story).

---

### Equal Quota Per Source

**Tried:** Round-robin with equal slots per source regardless of category.

**Failure:** With 10 tech feeds and 2 geopolitical feeds, the quota system gave 5× more LLM slots to tech content. A major arms deal or ceasefire announcement from Al Jazeera would be processed after 10 tech gadget reviews.

**Replaced by:** Per-category quota enforcement (`_CATEGORY_QUOTA` dict). Geopolitical and investigative sources earn 3 slots per scan; tech/sports earn 1. Combined with pre-score sorting, the highest-signal geopolitical content always reaches the LLM queue before lower-priority categories exhaust their slots.

---

## 12. Future Migration to NEXIS-LOCAL

AEGIS is being built as a foundation component of a larger local intelligence platform called NEXIS-LOCAL. The following architectural decisions were made with reusability in mind.

### Components Expected to Survive Migration

#### Source Intelligence Model
The `reliability_tier` + `editorial_role` + `source_orientation` schema in `rss_sources.json` and the `_compute_source_weight()` function in `pipeline.py` are designed as a standalone classification model. Any future NEXIS-LOCAL ingestion pipeline can import this model directly. The `config/NewsSources.md` document defines the classification principles independently of any specific feed list.

#### Pipeline Scoring Engine
`pipeline.py::score_item()` is a pure function with no dependencies on FastAPI, SQLite, or the specific frontend. Given any `SignalAnalysis` and `RawPost`, it produces deterministic scores. This can be imported directly into any Python data pipeline. The keyword lists (`_CONSTITUTIONAL_KW`, `_CENSORSHIP_KW`, `_WAR_KW`, etc.) represent domain expertise that would transfer to any constitutional-watchdog analysis workflow.

#### Database Schema Concepts
The `signals` table schema — particularly the `tracked`/`is_deleted` state machine, the `title_norm` dedup strategy, and the multi-dimensional scoring columns — represents a general-purpose architecture for a signal intelligence store. NEXIS-LOCAL would likely use PostgreSQL at scale, but the column semantics and migration-via-ensure-columns pattern would be replicated.

#### Consensus Archive Concepts
The `scan_id` + snapshot model in `front_page_consensus` is a general-purpose pattern for any time-series analysis: run a scan, capture a snapshot with a unique ID, store permanently, browse history. This pattern can be reused for any periodic intelligence snapshot in NEXIS-LOCAL.

#### AI Analyzer Interface
`ai/analyzer.py` is already abstracted from the specific model. Changing `MODEL = "qwen2.5:7b"` and `OLLAMA_URL` is all that's needed to point at a different local model or a different Ollama endpoint. The prompt structure and JSON extraction logic (`extract_json()`, validation in `analyze_item()`) are model-agnostic and would transfer to any structured JSON extraction task.

#### Frontend Component Architecture
`SignalCard.jsx` and the CSS design tokens in `styles.css` represent a reusable signal display system. The `data-significance` / `data-category` attribute pattern for CSS-driven card variants is a flexible approach that could be extended for new signal types in NEXIS-LOCAL.

### Components Likely to Be Rewritten for NEXIS-LOCAL

| Component | Why Rewritten |
|-----------|--------------|
| SQLite → PostgreSQL | Multi-user, scale, concurrent writes, full-text search |
| FastAPI single-router → service-oriented routes | Multiple modules (signals, documents, reports, etc.) |
| In-process threading → task queue (Celery/RQ) | Background scan reliability, retries, concurrency |
| React SPA (single dashboard) → multi-page app | Multiple analyst workflows, auth, user sessions |
| feedparser RSS only → multi-source ingest | Document ingestion, API feeds, structured data sources |

### Interface Contracts to Preserve

If AEGIS components are imported directly into NEXIS-LOCAL rather than rewritten, these interfaces must be preserved:

- `RawPost` Pydantic model in `models.py` — the common denominator for any collector
- `SignalAnalysis` Pydantic model — the LLM output contract
- `analyze_item(text: str) → SignalAnalysis` — any caller expecting this signature will work with any local model
- `score_item(analysis: SignalAnalysis, raw_post: RawPost) → dict` — pure function, composable with any pipeline

---

*End of AEGIS Storage and Structure Reference — Version 1.0*  
*ARC NEXUS LLC / SWAT Signal Desk*  
*Generated: May 28, 2026*

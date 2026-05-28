# AEGIS Source Intelligence Model
## config/NewsSources.md
### SWAT Signal Desk / ARC NEXUS LLC
#### Version: 1.0 — Stage 10

---

## Purpose

The AEGIS Source Intelligence Model defines how each news source is understood, weighted, and used for editorial confidence scoring. This system governs **corroboration strength**, **confidence scoring**, and **front-page placement eligibility**.

This is not a censorship system. It is an editorial confidence system.

### Core Principles

1. **AEGIS does not suppress sources based on orientation alone.** A consistent right-wing report and a consistent left-wing report on the same event are both signals. Orientation indicates framing context, not reliability.

2. **AEGIS does not assume "center" equals truth.** Center-classified outlets can still be wrong, incomplete, or editorially captured. Center classification means consistent independence from a visible partisan agenda — not omniscience.

3. **AEGIS does not assume "fringe" equals false.** A watchlist source reporting something that later proves true is still reportage. Watchlist classification means low verifiability and elevated narrative risk — not guaranteed fabrication.

4. **Cross-spectrum corroboration raises confidence.** When left + center + right outlets all cover the same event, AEGIS treats that as an editorial consensus signal, regardless of how each outlet frames it. Convergence across orientation lines is one of the strongest confidence indicators in the model.

5. **Tier 4 / watchlist sources cannot front-page a story alone.** Social platforms (Reddit) and state-narrative/fringe outlets generate useful pulse data — they show what audiences are engaging with — but factual confidence requires at least one established outlet.

6. **Tier 1 source presence is weighted, not required.** A story without any Tier 1 wire service coverage is not suppressed, but its confidence ceiling is lower. When AP or BBC corroborates, that ceiling rises.

---

## 1. Editorial Orientation

| Code        | Meaning                                                                  | Examples                                        |
|-------------|--------------------------------------------------------------------------|-------------------------------------------------|
| `center`    | Broadly independent; no consistent partisan lean across coverage         | AP, BBC, NPR, Foreign Policy, Bloomberg         |
| `left`      | Consistent left-of-center editorial orientation                          | Guardian, Axios, ProPublica, The Intercept      |
| `right`     | Consistent right-of-center editorial orientation                         | Reason, FIRE, Washington Examiner, Sky News     |
| `watchlist` | State-controlled, fringe, high-narrative, social, or low-verified        | Reddit, RT, Infowars, Gateway Pundit, OAN       |

**Notes on "watchlist":**
- Includes social aggregators (Reddit) because their content is user-generated and not editorially verified.
- Includes state-funded narrative outlets with documented editorial interference.
- Does NOT mean false. Means: treat as pulse/narrative signal, not as factual anchor.

**Notes on "left/right":**
- Orientation is assessed on consistent editorial pattern, not individual articles.
- An outlet can produce excellent factual journalism and still have a consistent orientation.
- ProPublica (left) produces highly reliable investigative work. The Intercept (left) is more analytical and narrative-oriented. Both are classified correctly at their respective tiers.

---

## 2. Source Role (Editorial Function)

| Code       | Meaning                                                           | Examples                                     |
|------------|-------------------------------------------------------------------|----------------------------------------------|
| `facts`    | Primary fact reporting; wire-style; emphasis on verified events   | AP, Reuters, BBC (breaking news)             |
| `mixed`    | Combination of fact reporting and analysis/context                | BBC long-form, NPR, Guardian, Al Jazeera     |
| `analysis` | Commentary, analysis, opinion, policy context                     | Foreign Policy, War on the Rocks, Reason     |
| `narrative`| Narrative framing, advocacy, or social pulse                      | Reddit posts, RT, fringe commentary          |

**How `editorial_role` affects scoring:**
- `facts` sources are given a slight score boost (×1.10) because wire-style reporting is more likely to be the foundational record of events.
- `analysis` sources are slightly down-weighted (×0.90) because analysis is interpretive — it can be valuable context but is not itself the event.
- `narrative` sources are significantly down-weighted (×0.75) because narrative content is opinion-dominant and has elevated manipulation risk.
- `mixed` is the baseline (×1.00).

**Important:** `editorial_role` is distinct from `source_role` in AEGIS. `source_role` is an operational category (geopolitical, censorship_watch, ai_watch, baseline, public) that governs which processing queue and quota a source belongs to. `editorial_role` is an intelligence classification that governs confidence scoring.

---

## 3. Reliability Tier

| Tier   | Meaning                                                                                   | Weight Multiplier |
|--------|-------------------------------------------------------------------------------------------|-------------------|
| Tier 1 | Factual baseline — wire services, major broadcast. High accountability, editorial standards. | ×1.15            |
| Tier 2 | Established reporting — recognized outlets with consistent editorial standards.             | ×1.00            |
| Tier 3 | Partisan / analysis / advocacy — may have strong orientation or lower accountability.       | ×0.75            |
| Tier 4 | Watchlist / low confidence — social, state-narrative, fringe, or unverified.               | ×0.45            |

**Combined source_weight formula:**
```
source_weight = tier_multiplier × editorial_role_multiplier
cap: [0.35, 1.25]
```

Example calculations:
- **AP (Tier 1, facts):** 1.15 × 1.10 = 1.265 → capped at 1.25
- **BBC (Tier 1, mixed):** 1.15 × 1.00 = 1.15
- **Guardian (Tier 2, mixed):** 1.00 × 1.00 = 1.00
- **Reason (Tier 3, analysis):** 0.75 × 0.90 = 0.675
- **Reddit (Tier 4, narrative):** 0.45 × 0.75 = 0.3375 → clamp to 0.35

**Tier 1 examples:** AP, Reuters, BBC, PBS NewsHour, Bloomberg (news wire)
**Tier 2 examples:** NPR, The Hill, Al Jazeera, Foreign Policy, ProPublica, MIT Technology Review, Bellingcat
**Tier 3 examples:** Reason, The Intercept, Reclaim the Net, National Review, Middle East Eye
**Tier 4 examples:** Reddit (all subs), RT, Infowars, Gateway Pundit, OAN, BeforeItsNews

---

## 4. Corroboration System

### Cross-Spectrum Corroboration

When a cluster (or single-story group) contains sources from multiple orientation categories, AEGIS awards a corroboration bonus to cluster importance score:

| Coverage                              | Bonus  | Reason                                             |
|---------------------------------------|--------|----------------------------------------------------|
| left + center + right all present     | +0.20  | Full editorial consensus across the spectrum       |
| center + either left or right         | +0.10  | Partial cross-spectrum confirmation                |
| only left + only right (no center)    | No bonus | Oppositional framing, not corroboration          |
| only one orientation                  | No bonus | No corroboration signal                          |

**Why this matters:** If AP (center), Guardian (left), and Fox News (right) all cover the same event, AEGIS treats that convergence as a strong signal that something real happened — regardless of how each outlet framed it. The story is real even if the framing is contested.

### Tier Reliability Corroboration

| Tier 1 presence in cluster            | Bonus  | Reason                                             |
|---------------------------------------|--------|----------------------------------------------------|
| 2 or more Tier 1 sources              | +0.20  | Multiple wire services confirm the event           |
| 1 Tier 1 source                       | +0.10  | One wire service anchor present                    |
| No Tier 1 sources                     | No bonus | No wire service verification                     |

**These bonuses stack:** A story with left + center + right coverage AND 2+ Tier 1 sources can receive a combined +0.40 boost to cluster importance.

### Reliability Caps

| Source composition                    | Cap                    | Behavior                                           |
|---------------------------------------|------------------------|----------------------------------------------------|
| All Tier 4 sources only               | Max importance = 0.59  | Cannot reach FRONT_PAGE tier (requires 0.80)       |
| All Tier 3 + Tier 4 only              | Max importance = 0.79  | Cannot reach FRONT_PAGE, can reach MAJOR           |
| Any Tier 1 or Tier 2 source present   | No cap                 | Full scoring range available                       |

**Purpose:** Reddit threads and watchlist sources can surface important narratives before mainstream outlets cover them. AEGIS preserves this as a "narrative pulse" signal (visible as MAJOR or SECTION at best) without letting it compete with verified multi-source front-page stories.

---

## 5. Source Role vs. Source Function

AEGIS uses two different role fields:

| Field            | Values                                                    | Used By                   | Purpose                                      |
|------------------|-----------------------------------------------------------|---------------------------|----------------------------------------------|
| `source_role`    | baseline, independent, geopolitical, censorship_watch, ai_watch, public | pipeline.py, run_collectors.py | Operational routing, category quota, processing priority |
| `editorial_role` | facts, analysis, mixed, narrative                         | pipeline.py (scoring)     | Confidence weighting                         |

These are orthogonal. Al Jazeera has `source_role=geopolitical` (operational) and `editorial_role=mixed` (editorial confidence). They serve different purposes in the pipeline.

---

## 6. Front-Page Eligibility Rules

A cluster/story is eligible for FRONT_PAGE tier (importance ≥ 0.80) if:

1. It contains at least one story with significance_score ≥ 0.80 OR
2. Multiple stories cluster around a FRONT_PAGE_PATTERN keyword AND
3. At least one source is Tier 1, 2, or 3 (not exclusively Tier 4/watchlist)

A cluster will **never reach FRONT_PAGE** if all sources are Tier 4 (watchlist/social only).

A cluster will **never reach FRONT_PAGE** (capped at MAJOR, 0.79) if all sources are Tier 3 or lower.

**Reasoning:** A story that exists only in Reddit posts and fringe blogs should not compete for front-page placement with a story confirmed by AP, BBC, and Al Jazeera. AEGIS preserves these signals at MAJOR tier so they are visible, but distinguishes them from verified multi-source events.

---

## 7. Current Source Classifications

### CENTER / BASELINE — TIER 1 (Wire / Broadcast)

| Source               | Orientation | Editorial Role | Tier | Notes                                    |
|----------------------|-------------|----------------|------|------------------------------------------|
| Associated Press     | center      | facts          | 1    | Primary wire service; factual anchor     |
| BBC News             | center      | mixed          | 1    | Major international broadcaster          |
| BBC World            | center      | mixed          | 1    | International news edition               |
| BBC Politics         | center      | mixed          | 1    | UK/US political coverage                 |
| BBC Business         | center      | mixed          | 1    | Economic reporting                       |
| BBC Technology       | center      | mixed          | 1    | Technology news from broadcast angle     |
| BBC Science          | center      | mixed          | 1    | Science reporting from broadcast angle   |
| BBC Sport            | center      | mixed          | 1    | Sports reporting                         |
| AP Politics          | center      | facts          | 1    | Wire-service political reporting         |
| AP Business          | center      | facts          | 1    | Wire-service economic reporting          |
| AP Technology        | center      | facts          | 1    | Wire-service technology reporting        |
| AP Science           | center      | facts          | 1    | Wire-service science reporting           |
| AP Sports            | center      | facts          | 1    | Wire-service sports reporting            |

### CENTER — TIER 2 (Established Reporting)

| Source               | Orientation | Editorial Role | Tier | Notes                                    |
|----------------------|-------------|----------------|------|------------------------------------------|
| NPR News             | center      | mixed          | 2    | Public broadcasting; policy depth        |
| NPR Politics         | center      | mixed          | 2    | Public radio political coverage          |
| NPR Economy          | center      | mixed          | 2    | Public radio economics                   |
| NPR Science          | center      | mixed          | 2    | Public radio science                     |
| The Hill             | center      | mixed          | 2    | Capitol Hill reporting; moderate lean    |
| Al Jazeera English   | center      | mixed          | 2    | Qatari-funded; maintains editorial independence in English edition |
| Foreign Policy       | center      | analysis       | 2    | Established foreign affairs analysis     |
| War on the Rocks     | center      | analysis       | 2    | Defense/security analysis                |
| Breaking Defense     | center      | mixed          | 2    | Defense industry reporting               |
| Techdirt             | center      | analysis       | 2    | Platform law and policy analysis         |
| MIT Technology Review| center      | analysis       | 2    | Technology policy and research           |
| Bellingcat           | center      | analysis       | 2    | OSINT-based investigative journalism     |
| Poynter              | center      | analysis       | 2    | Media industry and press freedom         |
| Ars Technica         | center      | analysis       | 2    | In-depth technology and science          |
| TechCrunch           | center      | mixed          | 2    | Startup/tech industry reporting          |
| ScienceDaily         | center      | mixed          | 2    | Research aggregator                      |
| Ohio Capital Journal | center      | mixed          | 2    | State-level independent journalism       |
| WCPO Cincinnati      | center      | mixed          | 2    | Local broadcast news                     |
| Columbus Dispatch    | center      | mixed          | 2    | Ohio regional newspaper                  |
| Louisville Courier-Journal | center | mixed         | 2    | Kentucky regional newspaper              |

### LEFT / LEAN LEFT

| Source               | Orientation | Editorial Role | Tier | Notes                                    |
|----------------------|-------------|----------------|------|------------------------------------------|
| The Guardian World   | left        | mixed          | 2    | UK-origin; strong investigative output   |
| Axios                | left        | mixed          | 2    | "Smart brevity" model; generally accurate but framing tends left |
| ProPublica           | left        | analysis       | 2    | High-accuracy nonprofit investigative    |
| CREW (Ethics Watch.) | left        | analysis       | 2    | Government ethics advocacy/watchdog      |
| EFF Deep Links       | left        | analysis       | 2    | Digital rights advocacy; factual on tech law |
| Wired                | left        | analysis       | 2    | Tech/society analysis; consistent left lean |
| The Verge            | left        | mixed          | 2    | Consumer tech; moderate left-tech lean   |
| The Intercept        | left        | analysis       | 3    | Adversarial journalism; important scoops but narrative risk higher |
| Middle East Eye      | left        | mixed          | 3    | Pro-Palestinian editorial lean; regional reporting |

### RIGHT / LEAN RIGHT

| Source               | Orientation | Editorial Role | Tier | Notes                                    |
|----------------------|-------------|----------------|------|------------------------------------------|
| Times of Israel      | right       | mixed          | 2    | Israeli regional perspective; factual within its framing |
| FIRE (Free Speech)   | right       | analysis       | 2    | Campus speech advocacy; accurate on legal facts |
| Reclaim the Net      | right       | mixed          | 3    | Tech censorship focus; right-leaning, some accuracy concerns |
| Reason               | right       | analysis       | 3    | Libertarian magazine; consistent orientation, factual quality varies |

### WATCHLIST / SOCIAL / LOW-CONFIDENCE

| Source               | Orientation | Editorial Role | Tier | Notes                                    |
|----------------------|-------------|----------------|------|------------------------------------------|
| r/worldnews          | watchlist   | narrative      | 4    | Aggregated user content; pulse signal only |
| r/news               | watchlist   | narrative      | 4    | Aggregated user content; pulse signal only |
| r/politics           | watchlist   | narrative      | 4    | Strongly liberal-coded subreddit; narrative signal |
| r/geopolitics        | watchlist   | narrative      | 4    | User analysis; pulse/narrative signal    |
| r/IsraelPalestine    | watchlist   | narrative      | 4    | High-engagement partisan subreddit       |
| r/iran               | watchlist   | narrative      | 4    | Community signal; watch for diaspora reporting |

### UNCLASSIFIED / NOT IN CURRENT FEEDS

| Source               | Default Classification                | Notes                                    |
|----------------------|---------------------------------------|------------------------------------------|
| RT (Russia Today)    | watchlist, narrative, tier 4          | State-controlled; documented editorial interference |
| Infowars             | watchlist, narrative, tier 4          | Fringe; documented fabrications          |
| Gateway Pundit       | watchlist, narrative, tier 4          | Partisan fringe; accuracy record poor    |
| OAN                  | watchlist, narrative, tier 4          | Far-right broadcast; narrative-dominant  |
| BeforeItsNews        | watchlist, narrative, tier 4          | Fringe conspiracy aggregator             |
| Unknown blogs/Substack | watchlist, narrative, tier 4        | Default until manually classified        |
| X/Twitter trends     | watchlist, narrative, tier 4          | Social pulse; not factual confirmation   |

---

## 8. How Weighting Flows Through AEGIS

```
RSS Feed (rss_sources.json)
  ├── source_orientation   ──→ stored in signals DB → scoreCluster() corroboration
  ├── editorial_role       ──→ pipeline.py _compute_source_weight()
  ├── reliability_tier     ──→ pipeline.py _compute_source_weight()
  └── source_role          ──→ run_collectors.py quota + pipeline.py legacy fallback

pipeline.py score_item()
  ├── reliability_tier × editorial_role → source_weight (replaces legacy role lookup)
  └── source_weight × raw_sig → significance_score (stored in DB)

RadarDashboard.jsx scoreCluster()
  ├── base: maxSig + avgSig + count + uniqueSources
  ├── pattern boost: FRONT_PAGE / SECTION / BACK_PAGE keyword match
  ├── corroboration: orientation diversity + tier 1 presence bonuses
  ├── caps: tier 4 only → max 0.59 / tier 3+4 only → max 0.79
  └── → cluster_importance → cluster_tier → display placement
```

---

## 9. Testing This System

### Test Case A: Wire Service Cluster (Reuters + AP + BBC)
- Three Tier 1 / center / facts sources on same story
- Expected: tier1Count = 3 → +0.20 tier bonus; orientations = {"center"} → no spectrum bonus
- Expected cluster_importance: high MAJOR or FRONT_PAGE based on content
- Expected: NOT penalized by tier cap (all Tier 1)

### Test Case B: Cross-Spectrum Convergence (AP + Guardian + Reason)
- Center (Tier 1) + Left (Tier 2) + Right (Tier 3) on same Iran/war story
- Expected: orientations = {left, center, right} → +0.20 spectrum bonus; tier1Count = 1 → +0.10 tier bonus
- Combined corroboration bonus: +0.30 on top of base score
- Expected: cluster_importance elevated significantly, likely FRONT_PAGE

### Test Case C: Partisan-Only Cluster (Intercept + Reason)
- Left Tier 3 + Right Tier 3 sources
- Expected: all tiers = [3, 3] → allLowReliability = true → cap at 0.79 (MAJOR at best)
- No corroboration bonus (no center source; left+right without center = contested, not corroborated)

### Test Case D: Watchlist-Only Cluster (Reddit × 4)
- All Tier 4 / watchlist / narrative
- Expected: allTier4 = true → cap at 0.59 (SECTION at best, never FRONT_PAGE)
- Source weights: ~0.35 each → low significance_score from pipeline
- Expected result: appears as SECTION or BACK_PAGE, never competes with wire service stories

### Test Case E: Single High-Significance AP Story (no cluster)
- AP, Tier 1, facts, center — single source Iran escalation, sig=0.88
- Expected: base = 0.88×0.40 + 0.88×0.20 = 0.528; "iran" + "military" hits → +0.50 pattern boost → ~1.0 → capped 1.0
- tier1Count = 1 → +0.10; orientations = {center} → no spectrum bonus
- Expected: FRONT_PAGE, SINGLE SOURCE tag shown, appears in main list above any Reddit clusters

---

## 10. Classification Update Log

| Date       | Change                                                        | Reason                                |
|------------|---------------------------------------------------------------|---------------------------------------|
| 2026-05-28 | Initial classification of all 51 configured feeds            | Stage 10: Source Intelligence Model   |
| —          | —                                                             | —                                     |

# ==========================================
# AEGIS
# File: tasks/front_page_consensus.py
# Phase: Stage 12 (Event Identity Refinement)
# ==========================================
#
# Stage 12 changes vs Stage 11:
#
#   ROOT CAUSE FIXED:
#   Stage 11 merged headlines on ANY 1 shared word, so "trump" alone
#   pulled every headline mentioning the president into one mega-cluster
#   (Iran strikes + DOJ probe + E. Jean Carroll + demographics + â€¦).
#
#   SOLUTION:
#   1. High-salience entity blocking â€” "trump", "biden", "congress",
#      "president" etc. are stripped from the comparison set.  They
#      appear in too many headlines to carry any event-identity signal.
#
#   2. Merge threshold raised â€” headlines must share 2+ event words
#      (non-high-salience), OR 1 anchor word (specific country /
#      institution / event type) within the same context domain.
#
#   3. Context domain classification â€” legal / military / election /
#      economic / diplomatic / social / general.  Cross-domain merges
#      are never allowed on a single shared word.
#
#   4. Per-source deduplication â€” max 1 article per outlet per cluster
#      (tier-1 wire services preferred as the representative pick).
#
#   5. Topic labels derived from event words only â€” no more
#      "trump iran strikes" when Trump is the only shared word.
# ==========================================

import json
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

from backend.app.db.database import Database
from sources.front_page import FrontPageCollector, extract_words

_FP_SOURCES_PATH = "config/front_page_sources.json"


# â”€â”€â”€ High-salience entity blocklist â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# These entities appear in so many headlines that their presence carries
# zero clustering signal.  Headlines must share 2+ OTHER content words,
# or 1 anchor word within the same context domain, to be merged.
_HIGH_SALIENCE: frozenset = frozenset({
    # Top US political figures â€” appear in a huge fraction of all headlines
    "trump", "biden", "harris", "obama", "clinton", "pence", "desantis",
    "pelosi", "schumer", "mcconnell",
    # Generic political / government terms
    "president", "white", "house", "administration", "government",
    "congress", "senate", "democrat", "republican", "party",
    "federal", "national", "american", "america", "united", "states",
    "official", "officials", "political", "policy",
})


# â”€â”€â”€ Context domain classifier â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Assigns a broad narrative category to a headline's event words.
# Two headlines in DIFFERENT domains cannot merge on a single anchor word.
_CONTEXT_KEYWORDS: Dict[str, frozenset] = {
    "legal": frozenset({
        "court", "trial", "lawsuit", "indictment", "verdict", "judge",
        "jury", "charges", "appeal", "testimony", "prosecutor", "attorney",
        "sentence", "criminal", "justice", "ruling", "case", "plea",
        "conviction", "fraud", "corruption", "investigation", "probe",
        "subpoena", "deposition", "settlement", "acquittal",
    }),
    "military": frozenset({
        "strike", "strikes", "attack", "attacks", "bomb", "bombing",
        "missile", "missiles", "troops", "military", "army", "navy",
        "force", "soldier", "invasion", "conflict", "battle", "weapon",
        "weapons", "drone", "nuclear", "defense", "airstrike", "raid",
        "combat", "casualty", "casualties", "ceasefire", "truce",
        "offensive", "siege", "hostage", "warfare",
    }),
    "election": frozenset({
        "vote", "votes", "voting", "election", "ballot", "candidate",
        "poll", "polls", "primary", "campaign", "voter", "voters",
        "electoral", "midterm", "runoff", "recount",
    }),
    "economic": frozenset({
        "economy", "trade", "tariff", "tariffs", "inflation", "interest",
        "rate", "bank", "market", "stock", "budget", "debt", "deficit",
        "recession", "gdp", "employment", "jobs", "wage", "wages",
        "cost", "price", "prices", "supply", "chain", "sanctions",
        "currency", "dollar", "reserve",
    }),
    "diplomatic": frozenset({
        "summit", "deal", "treaty", "embassy", "diplomat", "diplomatic",
        "foreign", "agreement", "negotiations", "ceasefire", "accord",
        "bilateral", "multilateral", "envoy", "alliance",
    }),
    "social": frozenset({
        "protest", "protests", "immigration", "border", "rights",
        "abortion", "religion", "race", "culture", "education", "health",
        "police", "crime", "gender", "climate", "environment",
        "refugee", "refugees", "migrants", "welfare",
    }),
}


# â”€â”€â”€ Anchor words â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Specific enough to anchor a cluster on their own when combined with a
# context match.  These are countries, institutions, or event types that
# represent a discrete news story rather than a recurring background topic.
_ANCHOR_WORDS: frozenset = frozenset({
    # Countries / regions at the center of specific news events
    "iran", "ukraine", "russia", "china", "israel", "gaza", "taiwan",
    "korea", "pakistan", "syria", "iraq", "venezuela", "cuba",
    "hamas", "hezbollah", "kremlin", "nato", "zelensky",
    # High-specificity event types (rare enough to be distinctive)
    "ceasefire", "referendum", "impeachment", "indictment",
    "invasion", "assassination", "coup", "hostage",
})


# â”€â”€â”€ Source loading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _load_fp_sources() -> List[Dict]:
    with open(_FP_SOURCES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# â”€â”€â”€ Event word extraction â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _event_words(title: str) -> frozenset:
    """
    Extract event-specific words: all meaningful words (>= 4 chars, not
    stop words) minus high-salience entities that appear in too many
    headlines to be useful for event-identity clustering.
    """
    return frozenset(extract_words(title) - _HIGH_SALIENCE)


def _classify_context(words: frozenset) -> str:
    """
    Assign a narrative context domain to a set of event words.
    Returns the domain with the most keyword matches, or "general".
    """
    best_domain = "general"
    best_score = 0
    for domain, kws in _CONTEXT_KEYWORDS.items():
        score = len(words & kws)
        if score > best_score:
            best_score = score
            best_domain = domain
    return best_domain


# â”€â”€â”€ Merge decision â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _should_merge(
    ew_a: frozenset, ctx_a: str,
    ew_b: frozenset, ctx_b: str,
) -> bool:
    """
    Decide whether two headlines represent the same event / narrative.

    Rules (in order):
    1. If either headline has no event words after stripping high-salience
       entities, never merge â€” we have no event-level evidence.
    2. 2+ shared event words â†’ merge.  This is strong content similarity
       regardless of context (e.g. "iran nuclear" appears in both).
    3. 1 shared anchor word + same context domain â†’ merge.
       e.g. both mention "iran" and both classify as "military".
    4. Everything else â†’ do not merge.

    What this prevents:
    - "trump" alone linking E. Jean Carroll + Iran strikes + DOJ probe.
    - Two stories in different domains (legal vs military) merging on a
      single shared word like "iran" (Iran sanctions â‰  Iran strikes).
    """
    if not ew_a or not ew_b:
        return False

    shared = ew_a & ew_b

    # Strong signal: 2+ shared event words
    if len(shared) >= 2:
        return True

    # Moderate signal: 1 anchor word + same context domain
    if len(shared) == 1 and (shared & _ANCHOR_WORDS) and ctx_a == ctx_b:
        return True

    return False


# â”€â”€â”€ Clustering â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _union_find_cluster(headlines: List[Dict]) -> List[List[Dict]]:
    """
    Groups headlines by event identity using Union-Find.

    Stage 12: uses _should_merge() (event-word similarity, high-salience
    blocking) instead of raw ANY-word overlap.  A single shared entity
    such as "trump" or "biden" no longer triggers a merge.
    """
    n = len(headlines)
    if n == 0:
        return []

    # Pre-compute event words and context for each headline once
    ews  = [_event_words(h["title"]) for h in headlines]
    ctxs = [_classify_context(ew) for ew in ews]

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        parent[find(x)] = find(y)

    for i in range(n):
        for j in range(i + 1, n):
            if _should_merge(ews[i], ctxs[i], ews[j], ctxs[j]):
                union(i, j)

    groups: Dict[int, List[int]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)

    return [[headlines[idx] for idx in idxs] for idxs in groups.values()]


# â”€â”€â”€ Per-source deduplication â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _deduplicate_group(group: List[Dict]) -> List[Dict]:
    """
    Enforce per-source representation: at most 1 article per outlet.

    Sort order before selecting:
      1. Tier-1 wire services first (AP / BBC â€” most authoritative).
      2. Orientation variety (center â†’ left â†’ right) so the displayed
         headlines reflect the full editorial spectrum.

    This prevents 5 NYT articles from dominating a single cluster card
    while other outlets' perspectives are invisible.
    """
    _ORI_ORDER = {"center": 0, "left": 1, "right": 2, "watchlist": 3}
    sorted_grp = sorted(
        group,
        key=lambda h: (
            h.get("reliability_tier", 4),
            _ORI_ORDER.get(h.get("orientation", "center"), 2),
        ),
    )
    seen: set = set()
    result: List[Dict] = []
    for h in sorted_grp:
        if h["source_name"] not in seen:
            seen.add(h["source_name"])
            result.append(h)
    return result


# â”€â”€â”€ Scoring â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _score_consensus(group: List[Dict]) -> float:
    """
    Composite consensus score (0.0 â€“ 1.0).
    Expects the already-deduplicated group (1 article per source).
    """
    sources     = {h["source_name"] for h in group}
    left        = any(h["orientation"] == "left"   for h in group)
    center      = any(h["orientation"] == "center" for h in group)
    right       = any(h["orientation"] == "right"  for h in group)
    tier1_count = sum(1 for h in group if h.get("reliability_tier", 4) == 1)

    score = 0.0
    score += min(len(sources) / 10.0, 1.0) * 0.40   # source breadth
    if left and center and right:
        score += 0.30
    elif (left and center) or (center and right):
        score += 0.15
    elif left and right:
        score += 0.05
    if tier1_count >= 3:
        score += 0.20
    elif tier1_count >= 1:
        score += 0.10
    return round(min(score, 1.0), 4)


def _consensus_tier(score: float) -> str:
    if score >= 0.70:
        return "confirmed"
    if score >= 0.45:
        return "elevated"
    if score >= 0.20:
        return "monitored"
    return "noise"


# â”€â”€â”€ Topic label â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _get_topic_label(group: List[Dict]) -> str:
    """
    Derive a 3-word topic label from the most frequent event-specific words.

    Stage 12: uses _event_words() (high-salience stripped) so labels like
    "trump iran strikes" become "iran strikes nuclear" â€” the actual event,
    not just the entity who mentioned it.

    Ranking: frequency desc â†’ anchor-word bonus â†’ word length (longer =
    more specific).
    """
    freq: Dict[str, int] = defaultdict(int)
    for h in group:
        for w in _event_words(h["title"]):
            freq[w] += 1

    if not freq:
        # Fallback: all significant words when event-word set is empty
        for h in group:
            for w in extract_words(h["title"]):
                freq[w] += 1

    ranked = sorted(
        freq.items(),
        key=lambda x: (-x[1], -(1 if x[0] in _ANCHOR_WORDS else 0), -len(x[0])),
    )
    return " ".join(w for w, _ in ranked[:3])


# â”€â”€â”€ Main entry point â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def run_front_page_consensus() -> Dict[str, Any]:
    """
    Execute a full front-page consensus scan and persist results.
    Returns a summary dict:
      {scan_id, headlines_collected, raw_clusters, stored, elapsed_seconds}
    """
    start   = time.time()
    scan_id = datetime.now().strftime("%Y%m%d%H%M%S")

    print("")
    print("=" * 60)
    print(" AEGIS â€” STAGE 12: FRONT PAGE EDITORIAL CONSENSUS SCAN")
    print("=" * 60)
    print(f" scan_id: {scan_id}")
    print("")

    sources   = _load_fp_sources()
    collector = FrontPageCollector(sources=sources, limit_per_source=10)
    db        = Database()

    all_headlines = collector.fetch()
    print(f"[CONSENSUS] {len(all_headlines)} headlines collected across {len(sources)} sources")

    clusters = _union_find_cluster(all_headlines)
    print(f"[CONSENSUS] {len(clusters)} raw clusters (event-identity Union-Find)")

    scored_rows: List[Dict] = []

    for group in clusters:
        if len(group) < 2:
            continue  # singleton â€” cannot represent consensus

        # Deduplicate: 1 article per source, tier-1 first
        deduped = _deduplicate_group(group)
        if len(deduped) < 2:
            continue  # all articles were from the same outlet

        score = _score_consensus(deduped)
        tier  = _consensus_tier(score)
        if tier == "noise":
            continue

        topic        = _get_topic_label(group)   # full group for frequency
        sources_set  = {h["source_name"] for h in deduped}
        left_count   = sum(1 for h in deduped if h["orientation"] == "left")
        center_count = sum(1 for h in deduped if h["orientation"] == "center")
        right_count  = sum(1 for h in deduped if h["orientation"] == "right")
        tier1_count  = sum(1 for h in deduped if h.get("reliability_tier", 4) == 1)

        # Display headlines: from deduped set (1 per source, tier-1 first)
        headlines_out = [
            {
                "title":       h["title"],
                "source_name": h["source_name"],
                "orientation": h["orientation"],
                "url":         h["url"],
            }
            for h in deduped[:8]
        ]

        # Top keywords from event words (for future filtering)
        all_words: Dict[str, int] = defaultdict(int)
        for h in group:
            for w in _event_words(h["title"]):
                all_words[w] += 1
        top_keywords = [w for w, _ in sorted(all_words.items(), key=lambda x: -x[1])[:10]]

        scored_rows.append({
            "scan_id":         scan_id,
            "topic":           topic,
            "keywords":        json.dumps(top_keywords),
            "headlines":       json.dumps(headlines_out),
            "source_count":    len(sources_set),
            "left_count":      left_count,
            "center_count":    center_count,
            "right_count":     right_count,
            "tier1_count":     tier1_count,
            "consensus_score": score,
            "consensus_tier":  tier,
        })

    scored_rows.sort(key=lambda x: -x["consensus_score"])
    top = scored_rows[:10]

    for row in top:
        db.insert_consensus(row)

    elapsed = round(time.time() - start, 1)
    print(f"[CONSENSUS] Stored {len(top)} clusters  (scan_id={scan_id})")
    print(f"[CONSENSUS] Finished in {elapsed}s")
    print("")

    return {
        "scan_id":             scan_id,
        "headlines_collected": len(all_headlines),
        "raw_clusters":        len(clusters),
        "stored":              len(top),
        "elapsed_seconds":     elapsed,
    }



# ==========================================
# AEGIS
# File: tasks/run_collectors.py
# Phase: 5A (Smart Intake Prioritization)
# Version: 003
# ==========================================

import json
import time
from collections import defaultdict

from models import RawPost
from sources.rss import RSSCollector
from backend.app.core.pipeline import SignalPipeline
from backend.app.db.database import Database


MAX_POSTS_TO_PROCESS = 60   # See note at bottom of file before raising this.
MAX_RUNTIME_SECONDS  = 240

# Per-category processing quota: max items processed from a single feed source.
# Geopolitical and investigative sources earn more slots than tech/sports/science.
# This prevents 6 tech feeds from crowding out front-page geopolitical coverage.
_CATEGORY_QUOTA: dict[str, int] = {
    "geopolitical":  3,
    "investigative": 3,
    "censorship":    2,
    "ai_watch":      2,
    "general":       2,
    "politics":      2,
    "economy":       2,
    "local":         2,
    "public_signal": 1,
    "technology":    1,
    "science":       1,
    "sports":        1,
}
_DEFAULT_QUOTA = 1


# ============================================================
# PRE-AI INTAKE PRIORITIZATION
# ============================================================
# WHY THIS EXISTS
# ---------------
# With 51 configured feeds and a MAX_POSTS_TO_PROCESS cap of 40,
# the old round-robin consumed a single LLM call per item — meaning
# the system randomly processed roughly <1 item per feed regardless
# of whether it was Al Jazeera covering a Gaza airstrike or AP Sports
# covering a college basketball trade.
#
# This function scores each raw post using ONLY deterministic string
# matching — no API calls, no LLM, no latency.  It runs in < 1ms per
# post.  By sorting all collected posts by this score before the
# round-robin (or before keyword-match slicing), the 40 LLM slots are
# spent on the highest-signal content instead of whatever came first.
#
# DESIGN RULES
# ------------
#  • Pure Python, no imports beyond builtins.
#  • Works on any object with .title / .body / .category / .source_role
#    attributes (falls back to empty string safely).
#  • Never raises — any failure returns 0.0 so the post is still eligible.
#  • Scores are relative (higher = more SWAT-relevant), not calibrated.
# ============================================================

# Tier 1 — highest SWAT relevance (weight 3.0 / hit, capped at 4 hits)
_T1_CONFLICT = [
    "war", "airstrike", "air strike", "missile", "bombing", "ceasefire",
    "cease-fire", "occupation", "siege", "invasion", "hostages", "rafah",
    "gaza", "israel", "iran", "lebanon", "palestine", "hamas", "hezbollah",
    "idf", "irgc", "nato", "ukraine", "russia", "nuclear", "troops",
    "military offensive", "ground invasion", "escalation",
    "central command", "pentagon", "joint chiefs", "strait of hormuz",
    "kuwait", "military strike", "air campaign", "naval blockade",
]

# Tier 1 — constitutional / governance collapse signals (weight 2.5)
_T1_CONSTITUTIONAL = [
    "constitution", "constitutional", "first amendment", "second amendment",
    "supreme court", "civil liberties", "martial law", "state of emergency",
    "executive order", "impeachment", "coup", "authoritarian",
    "election integrity", "voter suppression", "gerrymandering",
    "due process", "bill of rights", "fourth amendment", "fifth amendment",
    "sixth amendment", "habeas corpus", "civil rights violation",
    "democratic backsliding", "power grab",
]

# Tier 1 — censorship / free speech / platform suppression (weight 2.5)
_T1_CENSORSHIP = [
    "censorship", "censored", "deplatformed", "deplatforming",
    "shadowban", "shadow ban", "shadow-ban", "banned", "content removal",
    "content moderation", "takedown", "removed post", "twitter files",
    "facebook files", "suppressed", "throttled", "blocked account",
    "silenced", "eff", "fire lawsuit", "free speech", "platform ban",
    "account suspended", "demonetized", "fact-check label",
]

# Tier 1 — AI manipulation / disinformation / synthetic media (weight 2.5)
_T1_AI_MANIP = [
    "deepfake", "deep fake", "synthetic media", "ai generated content",
    "ai-generated", "disinformation", "misinformation", "propaganda",
    "astroturfing", "bot network", "coordinated inauthentic",
    "information warfare", "influence operation", "fabricated",
    "manufactured consent", "psyop", "narrative control",
    "coordinated campaign", "fake account network",
]

# Tier 1 — surveillance / digital control (weight 2.0)
_T1_SURVEILLANCE = [
    "surveillance", "mass surveillance", "digital id", "national id",
    "social credit", "facial recognition", "biometric", "nsa", "cia",
    "fbi surveillance", "wiretap", "backdoor", "encryption backdoor",
    "government tracking", "location data", "signal app", "stalkerware",
    "stingray", "palantir", "clearview",
]

# Tier 1 — lobbying / corruption / foreign influence (weight 2.5)
_T1_CORRUPTION = [
    "aipac", "lobbying", "lobbyist", "campaign finance", "dark money",
    "super pac", "foreign influence", "foreign agent", "fara",
    "bribery", "corruption", "insider trading", "ethics violation",
    "conflict of interest", "whistleblower", "document reveals",
    "investigation reveals", "propublica", "crew report",
    "money laundering", "self-dealing", "quid pro quo",
]

# Tier 2 — local Ohio / Kentucky focus (weight 2.0)
_T2_LOCAL = [
    "ohio", "kentucky", "cincinnati", "clermont", "amelia", "amelia ohio",
    "union township", "columbus ohio", "dayton ohio", "louisville",
    "covington kentucky", "northern kentucky", "hamilton county",
    "clermont county", "warren county", "ohio statehouse",
    "ohio governor", "ohio senate", "ohio house",
]

# Tier 2 — major tech power shifts (weight 1.5)
_T2_TECH = [
    "antitrust", "monopoly", "big tech", "openai", "anthropic",
    "google deepmind", "microsoft ai", "acquisition", "merger",
    "senate hearing", "ftc", "doj", "breakup", "market dominance",
    "data harvesting", "ai regulation", "algorithmic bias",
]

# Tier 2 — economic instability signals (weight 1.5)
_T2_ECONOMIC = [
    "recession", "crash", "collapse", "bank failure", "market crash",
    "inflation spike", "deflation", "federal reserve", "debt ceiling",
    "sovereign default", "dollar collapse", "gdp contraction",
    "mass layoffs", "unemployment surge", "bankruptcy", "financial crisis",
    "bond yield", "credit crunch",
]

# Tier 2 — infrastructure / critical systems disruption (weight 2.0)
_T2_INFRA = [
    "power grid", "blackout", "infrastructure attack", "cyberattack",
    "pipeline attack", "water supply", "dam failure", "bridge collapse",
    "supply chain disruption", "port shutdown", "critical infrastructure",
    "sabotage", "grid attack", "ransomware", "cisa",
]

# Source role bonuses — mirrors pipeline.py _SOURCE_ROLE_WEIGHTS
_ROLE_BONUS: dict[str, float] = {
    "geopolitical":    4.0,
    "censorship_watch": 3.0,
    "ai_watch":        2.5,
    "investigative":   2.0,
    "independent":     1.0,
    "baseline":        0.5,
    "public":          0.0,
}

# Category bonuses
_CATEGORY_BONUS: dict[str, float] = {
    "geopolitical":  3.0,
    "censorship":    2.5,
    "ai_watch":      2.0,
    "investigative": 2.5,
    "local":         1.5,
}

# Tier 1 — major health / biological crises (weight 2.5 / hit)
_T1_HEALTH_CRISIS = [
    "ebola", "pandemic", "epidemic", "outbreak", "public health emergency",
    "who declares", "disease outbreak", "viral outbreak", "biological threat",
    "health emergency", "mass quarantine", "contagion", "pandemic response",
    "cdc emergency", "health crisis",
]

# Downrank: noise / low-signal content (penalty per hit)
_DOWNRANK_NOISE = [
    "celebrity", "gossip", "kardashian", "taylor swift", "beyoncé", "beyonce",
    "met gala", "red carpet", "oscars ceremony", "grammy awards", "emmys",
    "box office", "movie review", "album review", "concert tour",
    "reality tv", "reality show", "the bachelor", "love island",
    "dancing with the stars", "american idol",
]
_DOWNRANK_SPORTS = [
    "nfl draft", "nba trade", "mlb trade", "nhl trade", "fifa ranking",
    "premier league", "super bowl prop", "world series preview",
    "fantasy sports", "fantasy football", "draft pick", "signed with",
    "traded to", "roster move", "injury report",
]
_DOWNRANK_OUTRAGE = [
    "totally destroys", "absolutely obliterates", "rips apart",
    "shuts down", "claps back", "goes viral for", "triggered",
    "snowflake", "libtard", "owned by", "torches",
]


def _hits(keywords: list[str], text: str) -> int:
    """Count how many keyword phrases appear in text. Simple substring match."""
    return sum(1 for kw in keywords if kw in text)


def pre_score_raw_post(post) -> float:
    """
    Deterministic pre-AI priority score for a raw RSS post.

    Higher score = process this first.  Returns 0.0 on any error so the
    post remains eligible but sorts to the end of the queue.

    Called before ANY LLM interaction — must be fast and allocation-light.
    """
    try:
        title       = (getattr(post, "title",       "") or "").lower()
        body        = (getattr(post, "body",         "") or "").lower()
        category    = (getattr(post, "category",     "") or "").lower()
        source_role = (getattr(post, "source_role",  "") or "").lower()
        text        = f"{title} {body[:400]}"  # body truncated — only lead matters

        score = 0.0

        # --- BOOST ---
        score += min(_hits(_T1_CONFLICT,       text), 4) * 3.0
        score += min(_hits(_T1_CONSTITUTIONAL, text), 4) * 2.5
        score += min(_hits(_T1_CENSORSHIP,     text), 4) * 2.5
        score += min(_hits(_T1_AI_MANIP,       text), 4) * 2.5
        score += min(_hits(_T1_SURVEILLANCE,   text), 4) * 2.0
        score += min(_hits(_T1_CORRUPTION,     text), 4) * 2.5
        score += min(_hits(_T1_HEALTH_CRISIS,  text), 4) * 2.5
        score += min(_hits(_T2_LOCAL,          text), 3) * 2.0
        score += min(_hits(_T2_TECH,           text), 3) * 1.5
        score += min(_hits(_T2_ECONOMIC,       text), 3) * 1.5
        score += min(_hits(_T2_INFRA,          text), 3) * 2.0

        score += _ROLE_BONUS.get(source_role, 0.0)
        score += _CATEGORY_BONUS.get(category, 0.0)

        # --- PENALTY ---
        penalty  = min(_hits(_DOWNRANK_NOISE,   text), 5) * 2.0
        penalty += min(_hits(_DOWNRANK_SPORTS,  text), 4) * 2.0
        penalty += min(_hits(_DOWNRANK_OUTRAGE, text), 3) * 1.5

        if category in ("sports", "entertainment"):
            penalty += 5.0

        score -= penalty
        return max(score, 0.0)   # floor at 0 — never negative

    except Exception:
        return 0.0  # safe fallback: post is still processed, just sorted last


def safe_print(*args):
    try:
        print(*args)
    except UnicodeEncodeError:
        cleaned = [str(arg).encode("ascii", "ignore").decode() for arg in args]
        print(*cleaned)


def run_all_collectors():
    start_time = time.time()

    safe_print("")
    safe_print("==============================")
    safe_print(" AEGIS — PHASE 1A SCAN")
    safe_print("==============================")
    safe_print("")

    with open("config/rss_sources.json", "r", encoding="utf-8") as f:
        rss_feeds = json.load(f)

    collector = RSSCollector(feeds=rss_feeds, limit=25)
    pipeline = SignalPipeline()
    db = Database()

    summary = {
        "collected": 0,
        "processed": 0,
        "stored": 0,
        "filtered": 0,
        "failed": 0,
        "by_source": {},
    }

    posts = collector.fetch()
    summary["collected"] = len(posts)

    # Pre-AI prioritization: sort ALL collected posts by deterministic heuristic
    # score before bucketing.  The round-robin then picks the highest-scoring
    # remaining item from whichever source is next in rotation, so the 40 LLM
    # slots are spent on SWAT-relevant content rather than whatever arrived first.
    posts.sort(key=pre_score_raw_post, reverse=True)

    safe_print(f"[COLLECTED] {len(posts)} posts")

    buckets = defaultdict(list)

    for post in posts:
        source_name = getattr(post, "subreddit", "unknown") or "unknown"
        buckets[source_name].append(post)

    active_sources = list(buckets.keys())
    index = 0
    source_processed: dict = {}  # tracks items processed per source for quota enforcement

    while active_sources:
        if summary["processed"] >= MAX_POSTS_TO_PROCESS:
            safe_print("[STOP] Max posts processed")
            break

        if time.time() - start_time > MAX_RUNTIME_SECONDS:
            safe_print("[STOP] Max runtime reached")
            break

        source_name = active_sources[index]
        bucket = buckets[source_name]

        if not bucket:
            active_sources.pop(index)

            if not active_sources:
                break

            index %= len(active_sources)
            continue

        # Quota check: remove this source from rotation once it has contributed
        # its per-category maximum.  This frees slots for other high-priority
        # sources instead of giving equal time to tech/sports feeds.
        _peek_cat = (getattr(bucket[0], "category", "general") or "general").lower()
        _source_quota = _CATEGORY_QUOTA.get(_peek_cat, _DEFAULT_QUOTA)
        if source_processed.get(source_name, 0) >= _source_quota:
            active_sources.pop(index)
            if not active_sources:
                break
            index %= len(active_sources)
            continue

        post = bucket.pop(0)
        source_processed[source_name] = source_processed.get(source_name, 0) + 1

        raw = RawPost(
            source=getattr(post, "source", "rss"),
            subreddit=getattr(post, "subreddit", ""),
            title=getattr(post, "title", ""),
            body=getattr(post, "body", ""),
            comments=getattr(post, "comments", []) or [],
            upvotes=getattr(post, "upvotes", 0) or 0,
            url=getattr(post, "url", ""),
            external_id=getattr(post, "external_id", getattr(post, "url", "")),
            category=getattr(post, "category", None),
            source_type=getattr(post, "source_type", None),
            source_role=getattr(post, "source_role", None),
            source_orientation=getattr(post, "source_orientation", None),
            editorial_role=getattr(post, "editorial_role", None),
            reliability_tier=getattr(post, "reliability_tier", None),
        )

        try:
            item = pipeline.process_item(raw)
            saved = db.insert_signal(item.model_dump())
            summary["processed"] += 1

            if item.filtered:
                summary["filtered"] += 1
                status = "FILTERED"
            else:
                summary["stored"] += 1
                status = "STORED"

            summary["by_source"][raw.subreddit] = (
                summary["by_source"].get(raw.subreddit, 0) + 1
            )

            safe_print(
                f"[{status}] ({raw.subreddit}) {raw.title[:70]}..."
            )

        except Exception as e:
            summary["failed"] += 1
            safe_print(f"[FAILED] ({raw.subreddit}) {raw.title[:70]}...")
            safe_print(f"Error: {e}")

        index = (index + 1) % len(active_sources)

    safe_print("")
    safe_print("==============================")
    safe_print(" PHASE 1A SUMMARY")
    safe_print("==============================")
    safe_print(f"Collected:  {summary['collected']}")
    safe_print(f"Processed:  {summary['processed']}")
    safe_print(f"Stored:     {summary['stored']}")
    safe_print(f"Filtered:   {summary['filtered']}")
    safe_print(f"Failed:     {summary['failed']}")
    safe_print("")
    safe_print("By source:")
    for source, count in sorted(summary["by_source"].items()):
        safe_print(f"  {source}: {count}")
    safe_print("")
    safe_print("[DONE]")
    safe_print("")

    return summary


def run_keyword_scan(query: str):
    """Fetch all configured RSS feeds and process only entries whose title/body
    contain at least one of the query terms. Skips duplicates already in DB."""
    start_time = time.time()

    terms = [t.strip().lower() for t in query.replace(",", " ").split() if len(t.strip()) >= 2]
    if not terms:
        return {"query": query, "error": "No valid search terms"}

    safe_print("")
    safe_print("==============================")
    safe_print(" AEGIS — KEYWORD SCAN")
    safe_print("==============================")
    safe_print(f" Query : {query}")
    safe_print(f" Terms : {terms}")
    safe_print("")

    with open("config/rss_sources.json", "r", encoding="utf-8") as f:
        rss_feeds = json.load(f)

    # Higher per-feed limit to catch more potential matches
    collector = RSSCollector(feeds=rss_feeds, limit=50)
    pipeline = SignalPipeline()
    db = Database()

    all_posts = collector.fetch()

    def entry_matches(post):
        haystack = f"{post.title} {post.body} {post.subreddit}".lower()
        return any(term in haystack for term in terms)

    matching = [p for p in all_posts if entry_matches(p)]

    # Pre-AI prioritization: within the keyword-matched set, sort by heuristic
    # score so the most SWAT-relevant matches consume the LLM slots first.
    matching.sort(key=pre_score_raw_post, reverse=True)

    summary = {
        "query": query,
        "terms": terms,
        "collected": len(all_posts),
        "matched": len(matching),
        "processed": 0,
        "stored": 0,
        "filtered": 0,
        "failed": 0,
    }

    safe_print(f"[KEYWORD SCAN] {len(matching)} / {len(all_posts)} entries match query")

    for post in matching[:MAX_POSTS_TO_PROCESS]:
        if time.time() - start_time > MAX_RUNTIME_SECONDS:
            safe_print("[STOP] Max runtime reached")
            break

        raw = RawPost(
            source=getattr(post, "source", "rss"),
            subreddit=getattr(post, "subreddit", ""),
            title=getattr(post, "title", ""),
            body=getattr(post, "body", ""),
            comments=[],
            upvotes=0,
            url=getattr(post, "url", ""),
            external_id=getattr(post, "external_id", getattr(post, "url", "")),
            category=getattr(post, "category", None),
            source_type=getattr(post, "source_type", None),
            source_role=getattr(post, "source_role", None),
        )

        try:
            item = pipeline.process_item(raw)
            db.insert_signal(item.model_dump())
            summary["processed"] += 1

            if item.filtered:
                summary["filtered"] += 1
                status = "FILTERED"
            else:
                summary["stored"] += 1
                status = "STORED"

            safe_print(f"[{status}] {raw.title[:70]}...")

        except Exception as e:
            summary["failed"] += 1
            safe_print(f"[FAILED] {raw.title[:70]}: {e}")

    safe_print("")
    safe_print("==============================")
    safe_print(" KEYWORD SCAN SUMMARY")
    safe_print("==============================")
    safe_print(f"Query:      {query}")
    safe_print(f"Collected:  {summary['collected']}")
    safe_print(f"Matched:    {summary['matched']}")
    safe_print(f"Processed:  {summary['processed']}")
    safe_print(f"Stored:     {summary['stored']}")
    safe_print(f"Filtered:   {summary['filtered']}")
    safe_print(f"Failed:     {summary['failed']}")
    safe_print("")
    safe_print("[DONE]")
    safe_print("")

    return summary


# ============================================================
# MAX_POSTS_TO_PROCESS — WHEN TO RAISE THIS
# ============================================================
# Current value: 40
#
# With pre-score ordering now in place, the 40-slot budget is no longer
# random — it preferentially consumes high-SWAT-relevance items.  That
# said, 40 is still conservative given 51 feeds.
#
# RAISE TO 75–100 when:
#   • qwen2.5:7b processes items in < 8s each (i.e., hardware is fast enough
#     that MAX_RUNTIME_SECONDS is the real constraint, not item count)
#   • You want broader daily coverage across all 51 sources
#   • You are running scheduled / overnight scans rather than on-demand
#
# LEAVE AT 40 OR LOWER when:
#   • Running on-demand from the UI and want < 5 min scan time
#   • System RAM / GPU is constrained (each Ollama call holds the model)
#   • Testing — smaller budget surfaces prioritization behavior faster
#
# MAX_RUNTIME_SECONDS (180) acts as a hard safety net regardless.
# ============================================================


if __name__ == "__main__":
    run_all_collectors()
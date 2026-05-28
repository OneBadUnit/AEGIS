# ==========================================
# SWAT SIGNAL DESK / AEGIS
# File: backend/app/core/pipeline.py
# Phase: 2A (Intelligence Layer — Scoring Pass)
# Version: 004
# ==========================================

import json

from models import RawPost, SignalItem
from ai.analyzer import analyze_item

# ------------------------------------
# Source credibility weights — Stage 10 Source Intelligence Model
# ------------------------------------
# Primary weighting uses reliability_tier × editorial_role when both fields
# are present (Stage 10 classified sources).  Falls back to the legacy
# source_role lookup for any source not yet classified.
#
# Tier multipliers: Tier 1 = wire/broadcast baseline; Tier 4 = watchlist/social
_TIER_WEIGHTS: dict[int, float] = {
    1: 1.15,   # Wire services, major broadcast — AP, BBC, Reuters
    2: 1.00,   # Established reporting — NPR, Guardian, Al Jazeera, ProPublica
    3: 0.75,   # Partisan/analysis/advocacy — Reason, Intercept, Reclaim the Net
    4: 0.45,   # Watchlist/social/low-confidence — Reddit, RT, fringe
}

# Editorial role multipliers: how the type of output affects confidence
_EDITORIAL_ROLE_WEIGHTS: dict[str, float] = {
    "facts":    1.10,  # Primary fact/wire-style reporting
    "mixed":    1.00,  # Mixed reporting + analysis (baseline)
    "analysis": 0.90,  # Commentary, analysis, opinion
    "narrative": 0.75, # Narrative/framing/advocacy/social pulse
}

# Legacy fallback — used when reliability_tier is absent (pre-Stage 10 sources
# or sources added without classification).
_SOURCE_ROLE_WEIGHTS = {
    "baseline":         1.00,  # AP, Reuters, BBC — verified wire services
    "independent":      0.85,  # TechCrunch, Wired, The Verge — solid but not wire
    "public":           0.55,  # Reddit — community signal, lower inherent credibility
    "geopolitical":     1.15,  # dedicated foreign-policy / conflict reporting
    "censorship_watch": 1.10,  # censorship monitoring outlets
    "ai_watch":         1.00,  # AI and disinformation tracking
}


def _compute_source_weight(raw_post: RawPost) -> float:
    """
    Compute source credibility weight using the Stage 10 Source Intelligence Model.

    Uses reliability_tier × editorial_role when classification is present.
    Falls back to legacy source_role lookup for unclassified sources.
    Result is clamped to [0.35, 1.25].
    """
    tier = getattr(raw_post, "reliability_tier", None)
    ed_role = (getattr(raw_post, "editorial_role", "") or "").lower().strip()
    op_role = (getattr(raw_post, "source_role", "") or "").lower().strip()

    if tier and tier in _TIER_WEIGHTS:
        tier_w = _TIER_WEIGHTS[tier]
        role_w = _EDITORIAL_ROLE_WEIGHTS.get(ed_role, 1.00)
        return round(min(max(tier_w * role_w, 0.35), 1.25), 4)

    # Legacy fallback: use operational source_role
    return _SOURCE_ROLE_WEIGHTS.get(op_role, 0.70)

# ------------------------------------
# Keyword lists for domain-specific scoring
# Each keyword hit adds to the corresponding domain score (capped at 1.0 after 4 hits).
# Lists are intentionally conservative — specific phrases over broad single words —
# to reduce false positives on ordinary news.
# ------------------------------------
_CONSTITUTIONAL_KW = [
    "constitution", "constitutional", "amendment", "first amendment",
    "second amendment", "fourth amendment", "fifth amendment",
    "supreme court ruling", "civil liberties", "due process", "habeas corpus",
    "executive order", "unconstitutional", "judicial review",
    "free speech", "press freedom", "freedom of assembly",
    "search and seizure", "rule of law", "separation of powers",
    "impeachment", "bill of rights", "wiretap", "fisa court", "nsa surveillance",
    "rights erosion", "civil rights ruling", "court strikes down",
]

_CENSORSHIP_KW = [
    "censorship", "censored", "content removed", "deplatformed",
    "shadow ban", "shadowban", "restricted content", "content moderation",
    "takedown notice", "account suspended", "silenced", "suppressed",
    "media blackout", "press restriction", "journalist arrested",
    "news blocked", "information control", "digital censorship",
    "platform ban", "algorithmic suppression",
]

_WAR_KW = [
    "declaration of war", "military strike", "armed conflict", "nato article 5",
    "troops deployed", "nuclear escalation", "missile attack", "military invasion",
    "military occupation", "wartime", "ceasefire collapse", "aerial bombing",
    "airstrike", "combat casualties", "weapons shipment", "artillery barrage",
    "naval blockade", "ground offensive", "front line", "mobilization",
    "military alliance", "arms deal", "no-fly zone", "war crimes",
]

# Low-significance content: entertainment, celebrity, shallow culture.
# These penalize the significance score by up to 40% when present.
_LOW_SIGNIFICANCE_KW = [
    "celebrity drama", "celebrity gossip",
    "breakup", "divorce drama", "dating rumor",
    "kardashian", "taylor swift album",
    "box office", "grammy award", "oscar ceremony",
    "reality show", "tiktok trend",
    "red carpet", "fashion week", "pop star",
    "leaked photo", "fan outrage",
]


def _keyword_score(text: str, keywords: list) -> float:
    """
    Returns a 0.0–1.0 score based on keyword presence in text.
    Caps at 1.0 after 4+ hits to prevent any single domain from
    dominating the composite significance score.
    """
    if not text:
        return 0.0
    t = text.lower()
    hits = sum(1 for kw in keywords if kw in t)
    return min(hits / 4.0, 1.0)


def score_item(analysis, raw_post: RawPost) -> dict:
    """
    Compute all AEGIS significance scores deterministically from AI analysis
    output and source metadata.

    Combines:
    - AI's raw significance estimate (normalized 1–10 → 0.0–1.0)
    - Domain-specific keyword scoring (constitutional, censorship, war)
    - Manipulation / narrative risk from AI flags
    - Source role credibility weight as a final multiplier

    Does NOT make any LLM calls. Fully local and deterministic.
    """
    # Build combined text corpus for keyword matching
    text = " ".join([
        analysis.topic   or "",
        analysis.summary or "",
        analysis.framing or "",
        analysis.claims  or "",
    ])

    # --- Source credibility weight ---
    # Stage 10: use tier×editorial_role composite when classification is present.
    source_weight = _compute_source_weight(raw_post)

    # --- Domain keyword scores (0.0–1.0) ---
    constitutional_score = _keyword_score(text, _CONSTITUTIONAL_KW)
    censorship_score     = _keyword_score(text, _CENSORSHIP_KW)
    war_score            = _keyword_score(text, _WAR_KW)

    # --- Narrative / manipulation score ---
    # Combines AI's manipulation_risk label with the count of detected flags.
    _risk_base = {"low": 0.05, "medium": 0.45, "high": 0.85}
    risk_base  = _risk_base.get(analysis.manipulation_risk, 0.05)
    flag_boost = min(len(analysis.narrative_flags) * 0.12, 0.30)
    narrative_score = min(risk_base + flag_boost, 1.0)

    # --- Low-significance penalty (0.0–1.0) ---
    # Reduces significance_score for celebrity / entertainment content.
    low_sig_hit = _keyword_score(text, _LOW_SIGNIFICANCE_KW)

    # --- AI significance normalized (1–10 → 0.0–1.0) ---
    # This is the primary backbone driving significance_score.
    ai_sig = (max(1, min(10, analysis.significance_raw)) - 1) / 9.0

    # --- Public interest score ---
    # Measures broad civic relevance: constitutional + censorship + war + AI estimate.
    public_interest_score = min(
        ai_sig               * 0.40 +
        constitutional_score * 0.25 +
        censorship_score     * 0.20 +
        war_score            * 0.15,
        1.0,
    )

    # --- Master significance score ---
    # AI significance is the backbone (45%).
    # Domain keyword scores add specific boosts (45% combined).
    # Narrative/manipulation awareness adds texture (10%).
    # Low-significance content is penalized by up to 40%.
    # Source weight multiplies the final result.
    raw_sig = (
        ai_sig               * 0.45 +
        constitutional_score * 0.20 +
        war_score            * 0.15 +
        censorship_score     * 0.10 +
        narrative_score      * 0.10
    )
    penalized          = raw_sig * (1.0 - low_sig_hit * 0.40)
    significance_score = round(min(penalized * source_weight, 1.0), 4)

    # trend_score is reserved for Phase 6 (social API integration).
    # It requires Reddit upvote velocity, X trend data, etc.
    # Hardcoded to 0.0 to prevent false ranking by an unimplemented metric.
    trend_score = 0.0

    return {
        "signal_type":           analysis.signal_type,
        "significance_score":    significance_score,
        "trend_score":           trend_score,
        "constitutional_score":  round(min(constitutional_score * source_weight, 1.0), 4),
        "censorship_score":      round(min(censorship_score     * source_weight, 1.0), 4),
        "war_score":             round(min(war_score            * source_weight, 1.0), 4),
        "narrative_score":       round(narrative_score, 4),
        "public_interest_score": round(min(public_interest_score * source_weight, 1.0), 4),
        "source_weight":         source_weight,
        "manipulation_risk":     analysis.manipulation_risk,
        "narrative_flags":       json.dumps(analysis.narrative_flags),
    }


class SignalPipeline:
    """
    AEGIS Phase 2A Pipeline:
    - Transform RawPost → SignalItem
    - Step 1: AI extraction (topic, summary, framing, claims, classification)
    - Step 2: Deterministic scoring pass (all significance scores)
    - Produces fully scored SignalItem ready for DB storage
    """

    def process_item(self, post: RawPost) -> SignalItem:
        text = f"""
Title:
{post.title}

Body:
{post.body}
""".strip()

        # Step 1: AI extraction — topic, summary, framing, claims + AEGIS classification
        analysis = analyze_item(text)

        # Step 2: Deterministic scoring — all significance scores from AI output + source metadata
        scores = score_item(analysis, post)

        return SignalItem(
            title=post.title,
            source=post.source,
            feed_name=post.subreddit,
            url=post.url,
            external_id=post.external_id,

            category=post.category,
            source_type=post.source_type,
            source_role=post.source_role,
            source_orientation=post.source_orientation,
            editorial_role=post.editorial_role,
            reliability_tier=post.reliability_tier,

            topic=analysis.topic,
            summary=analysis.summary,
            framing=analysis.framing,
            claims=analysis.claims,

            filtered=analysis.filtered,
            filter_reason=analysis.filter_reason,

            **scores,
        )
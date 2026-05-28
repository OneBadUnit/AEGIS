# ==========================================
# SWAT SIGNAL DESK
# File: models.py
# Phase: 1B (Keyword Search + Simple Clustering)
# Version: 003
# ==========================================
from typing import List, Optional
from pydantic import BaseModel, Field


class RawPost(BaseModel):
    source: str = ""
    subreddit: Optional[str] = None  # internal: feed/channel name
    title: str = ""
    body: str = ""
    comments: List[str] = Field(default_factory=list)
    upvotes: int = 0
    url: str = ""
    external_id: str = ""
    category: Optional[str] = None
    source_type: Optional[str] = None
    source_role: Optional[str] = None
    source_orientation: Optional[str] = None  # center | left | right | watchlist
    editorial_role: Optional[str] = None       # facts | analysis | mixed | narrative
    reliability_tier: Optional[int] = None     # 1 | 2 | 3 | 4


class SignalAnalysis(BaseModel):
    topic: str = ""
    summary: str = ""
    framing: str = ""
    claims: str = ""

    # AEGIS intelligence fields — populated by the AI analyzer
    signal_type: str = ""           # "verified_news" | "narrative_pulse" | "narrative_integrity"
    significance_raw: int = 0       # AI's raw importance estimate (1–10)
    manipulation_risk: str = "low"  # "low" | "medium" | "high"
    narrative_flags: List[str] = Field(default_factory=list)  # detected narrative anomaly flags

    filtered: bool = False
    filter_reason: str = ""


class SignalItem(BaseModel):
    id: Optional[int] = None

    title: str = ""
    source: str = ""
    feed_name: Optional[str] = None
    url: str = ""
    external_id: str = ""

    category: Optional[str] = None
    source_type: Optional[str] = None
    source_role: Optional[str] = None
    source_orientation: Optional[str] = None  # center | left | right | watchlist
    editorial_role: Optional[str] = None       # facts | analysis | mixed | narrative
    reliability_tier: Optional[int] = None     # 1 | 2 | 3 | 4

    topic: str = ""
    summary: str = ""
    framing: str = ""
    claims: str = ""

    # AEGIS intelligence classification
    signal_type: str = ""

    # AEGIS significance scores (0.0–1.0, computed by the pipeline scoring pass)
    significance_score: float = 0.0
    trend_score: float = 0.0          # reserved: requires social API data
    constitutional_score: float = 0.0
    censorship_score: float = 0.0
    war_score: float = 0.0
    narrative_score: float = 0.0
    public_interest_score: float = 0.0
    source_weight: float = 0.5

    # AEGIS manipulation indicators
    manipulation_risk: str = "low"
    narrative_flags: str = ""         # JSON-serialized List[str]

    filtered: bool = False
    filter_reason: str = ""

    created_at: Optional[str] = None
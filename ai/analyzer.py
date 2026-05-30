# ==========================================
# AEGIS
# File: ai/analyzer.py
# Phase: 1A (Rename + Reframe)
# Version: 003
# ==========================================

import json
import requests
from models import SignalAnalysis

MODEL = "qwen2.5:7b"
OLLAMA_URL = "http://127.0.0.1:11434"


def clean(text):
    if not text:
        return ""
    return str(text).strip()


def extract_json(text):
    if not text:
        return {}

    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return {}

    try:
        return json.loads(text[start:end + 1])
    except Exception:
        return {}


def call_llm(prompt):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1
        }
    }

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        print("[LLM ERROR]", e)
        return ""


def build_prompt(text):
    return f"""
You are AEGIS — a constitutional-watchdog signal analyzer.

Your job: extract structured intelligence from news articles, posts, and feed items.

CORE PRINCIPLE:
Evaluate SIGNIFICANCE — whether something materially matters to society — not merely whether it is loud or trending.

SIGNAL TYPE DEFINITIONS:
- "verified_news": factual reporting from established outlets; events with on-record sourcing
- "narrative_pulse": public reaction, viral discussion, emotional trend, popular opinion spike
- "narrative_integrity": suspicious narrative patterns — possible coordination, suppression, or manipulation signals

SIGNIFICANCE SCALE (1–10):
10 = Constitutional crisis, wartime escalation, verified systemic corruption, catastrophic event
8–9 = Major rights ruling, significant geopolitical escalation, censorship infrastructure deployed
6–7 = Notable policy shift, verified institutional abuse, significant verified economic event
4–5 = Moderate public-interest story, developing investigation, notable trend with real consequences
2–3 = Normal news cycle, limited systemic impact
1   = Entertainment, celebrity, sports, shallow outrage, lifestyle, culture war noise

MANIPULATION RISK:
- "low"    : standard reporting, no coordination indicators
- "medium" : notable editorial slant, unusual framing patterns, possible agenda-setting
- "high"   : synchronized messaging, narrative suppression signs, coordinated framing, engagement anomalies

NARRATIVE FLAGS — list ONLY flags that are genuinely present (usually the list is empty):
- "synchronized_messaging"  : near-identical framing across unrelated outlets
- "topic_suppression"       : significant story appears buried or systematically downplayed
- "ai_generated_content"    : content lacks human editorial voice; likely AI-written
- "engagement_asymmetry"    : amplification disproportionate to verifiable factual content
- "story_abandonment"       : previously covered significant story suddenly absent from all outlets
- "bot_amplification"       : signs of coordinated inauthentic activity driving attention
- "coordinated_narrative"   : multiple outlets simultaneously advance the same specific framing

RULES:
- DO NOT assert conspiracies as fact
- DO NOT take political sides
- DO NOT fabricate information
- DO NOT filter based on controversy, politics, sensitivity, or emotional content
- Trending alone does NOT mean high significance
- Only flag narrative anomalies when genuinely detectable — not as speculation
- Only set filtered=true for spam, gibberish, broken entries, pure advertisements

Return ONLY valid JSON:
{{
  "topic": "",
  "summary": "",
  "framing": "",
  "claims": "",
  "signal_type": "",
  "significance_raw": 5,
  "manipulation_risk": "low",
  "narrative_flags": [],
  "filtered": false,
  "filter_reason": ""
}}

Field definitions:
- topic            : subject, entity, or event being discussed (1–2 sentences)
- summary          : neutral description of what this item reports (2–3 sentences)
- framing          : how this item presents the topic — tone, emphasis, loaded language, angle (1–2 sentences)
- claims           : specific factual claims, statistics, allegations stated in the item (comma-separated)
- signal_type      : one of "verified_news", "narrative_pulse", "narrative_integrity"
- significance_raw : integer 1–10 using the scale above
- manipulation_risk: "low", "medium", or "high"
- narrative_flags  : array of flags from the list above; empty array when none detected
- filtered         : true ONLY for spam, gibberish, broken entries, pure advertisements
- filter_reason    : brief reason only if filtered=true; otherwise empty string

Source text:
{text}
""".strip()


def analyze_item(text: str) -> SignalAnalysis:
    prompt = build_prompt(text)
    raw = call_llm(prompt)
    data = extract_json(raw)

    if not data:
        return SignalAnalysis(
            filtered=True,
            filter_reason="Invalid model response"
        )

    if data.get("filtered"):
        return SignalAnalysis(
            filtered=True,
            filter_reason=clean(data.get("filter_reason")) or "Filtered by analyzer"
        )

    topic   = clean(data.get("topic"))
    summary = clean(data.get("summary"))
    framing = clean(data.get("framing"))
    claims  = clean(data.get("claims"))

    if not topic and not summary:
        return SignalAnalysis(
            filtered=True,
            filter_reason="No extractable signal"
        )

    # Parse signal_type — reject unknown values with a safe fallback.
    signal_type = clean(data.get("signal_type", ""))
    if signal_type not in ("verified_news", "narrative_pulse", "narrative_integrity"):
        signal_type = "verified_news"

    # Parse significance_raw (1–10) — handle string-typed integers from some models.
    try:
        significance_raw = int(data.get("significance_raw", 5))
    except (TypeError, ValueError):
        significance_raw = 5
    significance_raw = max(1, min(10, significance_raw))

    # Parse manipulation_risk — reject unknown values with a safe fallback.
    manipulation_risk = clean(data.get("manipulation_risk", "low"))
    if manipulation_risk not in ("low", "medium", "high"):
        manipulation_risk = "low"

    # Parse narrative_flags — only accept strings from the known valid set.
    # This prevents prompt injection or hallucinated flag values from entering the DB.
    VALID_FLAGS = {
        "synchronized_messaging",
        "topic_suppression",
        "ai_generated_content",
        "engagement_asymmetry",
        "story_abandonment",
        "bot_amplification",
        "coordinated_narrative",
    }
    raw_flags = data.get("narrative_flags", [])
    if not isinstance(raw_flags, list):
        raw_flags = []
    narrative_flags = [f for f in raw_flags if isinstance(f, str) and f in VALID_FLAGS]

    return SignalAnalysis(
        topic=topic,
        summary=summary,
        framing=framing,
        claims=claims,
        signal_type=signal_type,
        significance_raw=significance_raw,
        manipulation_risk=manipulation_risk,
        narrative_flags=narrative_flags,
        filtered=False,
        filter_reason=""
    )
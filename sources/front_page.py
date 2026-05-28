# ==========================================
# SWAT SIGNAL DESK / AEGIS
# File: sources/front_page.py
# Phase: Stage 11 (Front Page Editorial Consensus Engine)
# ==========================================
#
# Fetches top-N RSS headlines from 15 curated front-page sources
# spanning left / center / right editorial orientations.
#
# Design rules:
#   - No LLM calls — this is pure RSS fetch + text extraction.
#   - Failures per source are silently skipped so one dead feed
#     never blocks the entire consensus scan.
#   - extract_words() mirrors the AEGIS JS stop-word filter so
#     the Python cluster algorithm and the JS cluster algorithm
#     agree on what constitutes a "significant" word.
# ==========================================

import re
from typing import Dict, List

import feedparser
import requests

# ─── Stop-word list ────────────────────────────────────────────────────
# Mirrors the AEGIS JS STOP_WORDS set plus news-specific noise.
# Words in this set are never treated as entity/topic markers.
_STOP_WORDS: frozenset = frozenset({
    # Standard English
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "but", "and", "or", "for",
    "in", "on", "at", "to", "of", "with", "by", "from", "that", "this",
    "it", "as", "not", "also", "about", "over", "after", "before", "under",
    "new", "says", "said", "report", "reports", "may", "could", "would",
    "should", "will", "one", "two", "three", "more", "less", "most", "least",
    "very", "just", "now", "then", "than", "when", "where", "who", "what",
    "how", "why", "which", "other", "some", "many", "any", "all", "up",
    "down", "out", "off", "ago", "per", "amid", "between", "through",
    "during", "into", "against", "while", "their", "they", "them", "its",
    "his", "her", "our", "your", "we", "he", "she", "news", "world",
    "people", "make", "made", "take", "taken", "need", "first", "last",
    "next", "back", "long", "high", "year", "week", "month", "day", "time",
    "both", "each", "such", "even", "like", "well", "still", "part",
    "find", "found", "come", "came", "goes", "going", "here", "there",
    "these", "those",
    # News-specific noise — frequent but non-entity words
    "official", "officials", "government", "federal", "state", "house",
    "white", "breaking", "update", "latest", "live", "watch", "read",
    "exclusive", "analysis", "opinion", "editorial", "according",
    "calls", "seeks", "plans", "ahead", "takes", "sets", "makes",
    "faces", "warns", "hits", "urges", "backs", "asks", "talks",
    "meets", "sends", "signs", "holds", "pushes", "puts", "cuts",
    "amid", "know", "look", "says", "show", "shows", "told", "kill",
    "dead", "died", "death", "says", "claim", "claims", "deny",
    "denies", "open", "close", "says", "week", "days", "hour", "hours",
    "vote", "votes", "voted", "bill", "bills", "deal", "deals",
    "talks", "meet", "meet", "says", "amid", "says", "amid",
})


def extract_words(title: str) -> set:
    """
    Extract significant words from a news headline.
    Returns a set of lowercase words that are:
      - at least 4 characters long
      - not in the stop-word list
    Mirrors the logic used by the AEGIS JS front-end clustering.
    """
    words = re.sub(r"[^a-z0-9\s]", " ", title.lower()).split()
    return {w for w in words if len(w) >= 4 and w not in _STOP_WORDS}


class FrontPageCollector:
    """
    Fetches top-N RSS headlines from each front-page source.
    Returns a flat list of headline dicts used by the consensus engine.
    """

    def __init__(self, sources: List[Dict], limit_per_source: int = 10):
        self.sources = sources
        self.limit_per_source = limit_per_source
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
                "Gecko/20100101 Firefox/125.0"
            ),
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        }

    def _fetch_feed(self, url: str) -> str:
        resp = requests.get(url, headers=self.headers, timeout=15)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")
        return resp.text

    def fetch(self) -> List[Dict]:
        """
        Fetch headlines from all configured sources.

        Returns a list of dicts:
          {title, url, source_name, orientation, reliability_tier}

        Per-source failures are logged and skipped; the rest continue.
        """
        results: List[Dict] = []

        for source in self.sources:
            url = (source.get("url") or "").strip()
            source_name = (source.get("name") or "unknown").strip()
            orientation = (source.get("orientation") or "center").strip()
            tier = int(source.get("reliability_tier") or 2)

            if not url:
                print(f"[FP SKIP] No URL for source: {source_name}")
                continue

            try:
                raw = self._fetch_feed(url)
                parsed = feedparser.parse(raw)
                count = 0

                for entry in parsed.entries:
                    if count >= self.limit_per_source:
                        break
                    title = (entry.get("title") or "").strip()
                    link = (entry.get("link") or "").strip()
                    if not title:
                        continue
                    results.append({
                        "title": title,
                        "url": link,
                        "source_name": source_name,
                        "orientation": orientation,
                        "reliability_tier": tier,
                    })
                    count += 1

                print(f"[FP] {source_name}: {count} headlines")

            except Exception as exc:
                print(f"[FP ERROR] {source_name}: {exc}")
                # Continue — one dead feed does not abort the scan

        print(f"[FP] Total collected: {len(results)} headlines from {len(self.sources)} sources")
        return results

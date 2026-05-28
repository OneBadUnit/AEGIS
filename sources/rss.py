# ==========================================
# SWAT SIGNAL DESK
# File: sources/rss.py
# Phase: 1B (Keyword Search + Simple Clustering)
# Version: 003
# ==========================================

from typing import List
from urllib.parse import urlparse, urlunparse
import requests
import feedparser

from models import RawPost
from sources.base import BaseCollector


class RSSCollector(BaseCollector):
    def __init__(self, feeds: List[dict], limit: int = 20):
        self.feeds = feeds
        self.limit = limit
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
                "Gecko/20100101 Firefox/125.0"
            ),
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        }

    def reddit_old_url(self, url: str) -> str:
        parsed = urlparse(url)
        if "reddit.com" not in parsed.netloc:
            return url

        return urlunparse((
            parsed.scheme or "https",
            "old.reddit.com",
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        ))

    def fetch_feed_text(self, url: str) -> str:
        urls_to_try = [url]

        old_url = self.reddit_old_url(url)
        if old_url != url:
            urls_to_try.append(old_url)

        last_error = None

        for candidate in urls_to_try:
            try:
                response = requests.get(
                    candidate,
                    headers=self.headers,
                    timeout=20,
                )

                if response.status_code == 200:
                    return response.text

                last_error = f"{response.status_code} {response.reason}"

            except Exception as e:
                last_error = str(e)

        raise RuntimeError(last_error or "Feed fetch failed")

    def is_sponsored_entry(self, title: str, summary: str, link: str) -> bool:
        combined = f"{title} {summary} {link}".lower()

        sponsored_signals = [
            "promoted",
            "sponsored",
            "advertisement",
            "advertiser",
            "ads.reddit",
            "redditinc.com/advertising",
            "base44.com",
            "sign up",
            "start building today",
        ]

        return any(signal in combined for signal in sponsored_signals)

    def fetch(self) -> List[RawPost]:
        posts: List[RawPost] = []

        print(f"[RSS] Loaded {len(self.feeds)} feeds")

        for feed in self.feeds:
            url = (feed.get("url") or "").strip()
            source_name = (feed.get("name") or "rss").strip()
            category = (feed.get("category") or "general").strip()
            source_type = (feed.get("source_type") or "news").strip()
            source_role = (feed.get("source_role") or "baseline").strip()
            source_orientation = (feed.get("source_orientation") or "center").strip()
            editorial_role = (feed.get("editorial_role") or "mixed").strip()
            reliability_tier_raw = feed.get("reliability_tier")
            reliability_tier = int(reliability_tier_raw) if reliability_tier_raw is not None else 2

            if not url:
                print(f"[RSS SKIP] Missing URL for feed: {source_name}")
                continue

            print(f"[RSS] Fetching {source_name}: {url}")

            try:
                raw_feed = self.fetch_feed_text(url)
                parsed = feedparser.parse(raw_feed)
            except Exception as e:
                print(f"[RSS ERROR] {source_name}: {e}")
                continue

            entries = parsed.entries or []
            print(f"[RSS] {source_name}: {len(entries)} entries found")

            feed_count = 0
            skipped_ads = 0

            for entry in entries:
                if feed_count >= self.limit:
                    break

                title = entry.get("title", "") or ""

                if entry.get("content"):
                    content_value = entry.get("content", [{}])[0].get("value", "")
                else:
                    content_value = ""

                summary = (
                    entry.get("summary", "")
                    or entry.get("description", "")
                    or content_value
                    or ""
                )

                link = entry.get("link", "") or ""
                entry_id = entry.get("id", "") or link or f"{source_name}:{title}"

                if self.is_sponsored_entry(title, summary, link):
                    skipped_ads += 1
                    continue

                posts.append(
                    RawPost(
                        source="rss",
                        subreddit=source_name,
                        title=title,
                        body=summary,
                        comments=[],
                        upvotes=0,
                        url=link,
                        external_id=entry_id,
                        category=category,
                        source_type=source_type,
                        source_role=source_role,
                        source_orientation=source_orientation,
                        editorial_role=editorial_role,
                        reliability_tier=reliability_tier,
                    )
                )

                feed_count += 1

            if skipped_ads:
                print(f"[RSS] {source_name}: skipped {skipped_ads} sponsored/ad-like entries")

        print(f"[RSS] Total posts returned: {len(posts)}")
        return posts
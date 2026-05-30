# ==========================================
# AEGIS
# File: backend/app/db/database.py
# Phase: 1B (Keyword Search + Simple Clustering)
# Version: 004
# ==========================================

import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any

# ------------------------------------
# Intake deduplication helpers (Stage 9)
# ------------------------------------
_TITLE_STOP = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "in", "on", "at", "to", "of", "for", "and", "or", "but",
    "with", "by", "from", "that", "this", "it", "as", "not",
    "its", "has", "have", "had", "will", "would", "could", "should",
    "may", "might", "can", "do", "did", "does", "new", "says",
    "report", "reports", "over", "into", "how", "why", "what",
    "who", "when", "after", "before", "up", "out", "about",
})


def _normalize_title(title: str) -> str:
    """
    Reduces a title to a stable deduplication fingerprint.
    Strips punctuation, lowercases, drops stop words, keeps the first 10
    significant words. Near-identical titles from different outlets produce
    the same fingerprint; genuinely new related stories differ in their
    key words and pass through.
    """
    if not title:
        return ""
    text = re.sub(r"[^a-z0-9\s]", "", title.lower())
    words = [w for w in text.split() if len(w) >= 3 and w not in _TITLE_STOP]
    return " ".join(words[:10])


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "market_radar.db"


class Database:
    def __init__(self, path: Optional[str] = None):
        self.path = str(path or DB_PATH)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.ensure_tables()
        self.ensure_columns()

    def ensure_tables(self):
        with self.conn:
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT DEFAULT '',
                source TEXT DEFAULT '',
                feed_name TEXT,
                url TEXT UNIQUE,
                external_id TEXT UNIQUE,

                category TEXT DEFAULT '',
                source_type TEXT DEFAULT '',
                source_role TEXT DEFAULT '',

                topic TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                framing TEXT DEFAULT '',
                claims TEXT DEFAULT '',

                filtered INTEGER DEFAULT 0,
                filter_reason TEXT DEFAULT '',
                is_deleted INTEGER DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            # Stage 11: Front Page Editorial Consensus table
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS front_page_consensus (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id          TEXT    NOT NULL,
                topic            TEXT    NOT NULL,
                keywords         TEXT    NOT NULL DEFAULT '[]',
                headlines        TEXT    NOT NULL DEFAULT '[]',
                source_count     INTEGER DEFAULT 0,
                left_count       INTEGER DEFAULT 0,
                center_count     INTEGER DEFAULT 0,
                right_count      INTEGER DEFAULT 0,
                tier1_count      INTEGER DEFAULT 0,
                consensus_score  REAL    DEFAULT 0.0,
                consensus_tier   TEXT    DEFAULT '',
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_fp_scan_id "
                "ON front_page_consensus(scan_id)"
            )

    def ensure_columns(self):
        existing = {
            row["name"]
            for row in self.conn.execute("PRAGMA table_info(signals)").fetchall()
        }

        with self.conn:
            if "is_deleted" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN is_deleted INTEGER DEFAULT 0"
                )
            if "claims" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN claims TEXT DEFAULT ''"
                )
            if "category" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN category TEXT DEFAULT ''"
                )
            if "source_type" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN source_type TEXT DEFAULT ''"
                )
            if "source_role" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN source_role TEXT DEFAULT ''"
                )
            # AEGIS intelligence columns — added in Phase 2A.
            # All use safe defaults so existing DB rows are unaffected.
            if "signal_type" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN signal_type TEXT DEFAULT ''"
                )
            if "significance_score" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN significance_score REAL DEFAULT 0.0"
                )
            if "trend_score" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN trend_score REAL DEFAULT 0.0"
                )
            if "constitutional_score" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN constitutional_score REAL DEFAULT 0.0"
                )
            if "censorship_score" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN censorship_score REAL DEFAULT 0.0"
                )
            if "war_score" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN war_score REAL DEFAULT 0.0"
                )
            if "narrative_score" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN narrative_score REAL DEFAULT 0.0"
                )
            if "public_interest_score" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN public_interest_score REAL DEFAULT 0.0"
                )
            if "source_weight" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN source_weight REAL DEFAULT 0.5"
                )
            if "manipulation_risk" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN manipulation_risk TEXT DEFAULT 'low'"
                )
            if "narrative_flags" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN narrative_flags TEXT DEFAULT ''"
                )
            if "tracked" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN tracked INTEGER DEFAULT 0"
                )
                self.conn.execute("UPDATE signals SET tracked = 1")
            if "title_norm" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN title_norm TEXT DEFAULT ''"
                )
                # Backfill existing rows so the dedup index is immediately useful.
                rows = self.conn.execute("SELECT id, title FROM signals").fetchall()
                for row in rows:
                    norm = _normalize_title(row["title"] or "")
                    if norm:
                        self.conn.execute(
                            "UPDATE signals SET title_norm = ? WHERE id = ?",
                            (norm, row["id"]),
                        )
            # Fast lookup index for title-based deduplication (idempotent DDL).
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_signals_title_norm ON signals(title_norm)"
            )
            # Stage 10: Source Intelligence Model — editorial metadata
            if "source_orientation" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN source_orientation TEXT DEFAULT ''"
                )
            if "editorial_role" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN editorial_role TEXT DEFAULT ''"
                )
            if "reliability_tier" not in existing:
                self.conn.execute(
                    "ALTER TABLE signals ADD COLUMN reliability_tier INTEGER DEFAULT 0"
                )

    def insert_signal(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = item.get("url", "")
        external_id = item.get("external_id", "")

        # Exact dedup: URL and external_id
        existing = self.get_by_url(url) if url else None
        if not existing and external_id:
            existing = self.get_by_external_id(external_id)
        if existing:
            return existing

        # Stage 9: Intake memory — skip if a near-duplicate title is already in
        # the Library (tracked=1) or was deleted by the user (is_deleted=1).
        # Prevents the same story from cycling back into Live Feed after it has
        # been saved or dismissed. Genuinely new stories with different key words
        # produce a different fingerprint and pass through normally.
        title_norm = _normalize_title(item.get("title", ""))
        if title_norm:
            blocked = self.conn.execute(
                """
                SELECT id FROM signals
                WHERE title_norm = ?
                  AND (tracked = 1 OR is_deleted = 1)
                LIMIT 1
                """,
                (title_norm,),
            ).fetchone()
            if blocked:
                return None

        with self.conn:
            self.conn.execute("""
            INSERT OR IGNORE INTO signals (
                title,
                source,
                feed_name,
                url,
                external_id,
                category,
                source_type,
                source_role,
                source_orientation,
                editorial_role,
                reliability_tier,
                topic,
                summary,
                framing,
                claims,
                signal_type,
                significance_score,
                trend_score,
                constitutional_score,
                censorship_score,
                war_score,
                narrative_score,
                public_interest_score,
                source_weight,
                manipulation_risk,
                narrative_flags,
                filtered,
                filter_reason,
                title_norm,
                is_deleted
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                item.get("title", ""),
                item.get("source", ""),
                item.get("feed_name"),
                url,
                external_id,
                item.get("category", ""),
                item.get("source_type", ""),
                item.get("source_role", ""),
                item.get("source_orientation", ""),
                item.get("editorial_role", ""),
                item.get("reliability_tier") or 0,
                item.get("topic", ""),
                item.get("summary", ""),
                item.get("framing", ""),
                item.get("claims", ""),
                item.get("signal_type", ""),
                item.get("significance_score", 0.0),
                item.get("trend_score", 0.0),
                item.get("constitutional_score", 0.0),
                item.get("censorship_score", 0.0),
                item.get("war_score", 0.0),
                item.get("narrative_score", 0.0),
                item.get("public_interest_score", 0.0),
                item.get("source_weight", 0.5),
                item.get("manipulation_risk", "low"),
                item.get("narrative_flags", ""),
                1 if item.get("filtered") else 0,
                item.get("filter_reason", ""),
                title_norm,
            ))

        if url:
            return self.get_by_url(url)

        if external_id:
            return self.get_by_external_id(external_id)

        return None

    def get_recent(
        self,
        limit: int = 50,
        include_filtered: bool = False,
        tracked_only: bool = False,
        live_only: bool = False,
    ) -> List[Dict[str, Any]]:
        conditions = ["is_deleted = 0"]
        if not include_filtered:
            conditions.append("filtered = 0")
        if tracked_only:
            conditions.append("tracked = 1")
        if live_only:
            conditions.append("tracked = 0")
        where = " AND ".join(conditions)
        query = f"""
            SELECT *
            FROM signals
            WHERE {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """
        rows = self.conn.execute(query, (limit,)).fetchall()
        return [self.row_to_dict(row) for row in rows]

    def track_signal(self, signal_id: int) -> bool:
        with self.conn:
            cur = self.conn.execute(
                "UPDATE signals SET tracked = 1 WHERE id = ? AND is_deleted = 0",
                (signal_id,),
            )
        return cur.rowcount > 0

    def delete(self, signal_id: int) -> bool:
        with self.conn:
            cur = self.conn.execute(
                """
                UPDATE signals
                SET is_deleted = 1
                WHERE id = ?
                """,
                (signal_id,),
            )

        return cur.rowcount > 0

    def get_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        if not url:
            return None

        row = self.conn.execute(
            "SELECT * FROM signals WHERE url = ?",
            (url,),
        ).fetchone()

        return self.row_to_dict(row) if row else None

    def get_by_external_id(self, external_id: str) -> Optional[Dict[str, Any]]:
        if not external_id:
            return None

        row = self.conn.execute(
            "SELECT * FROM signals WHERE external_id = ?",
            (external_id,),
        ).fetchone()

        return self.row_to_dict(row) if row else None

    def row_to_dict(self, row) -> Dict[str, Any]:
        item = dict(row)
        item["filtered"] = bool(item.get("filtered", 0))
        item["is_deleted"] = bool(item.get("is_deleted", 0))
        return item

    # -------------------------------------------------------------------------
    # Stage 11: Front Page Consensus
    # -------------------------------------------------------------------------

    def insert_consensus(self, row: Dict[str, Any]) -> None:
        """Persist one consensus cluster row from a front-page scan."""
        with self.conn:
            self.conn.execute("""
            INSERT INTO front_page_consensus (
                scan_id, topic, keywords, headlines,
                source_count, left_count, center_count, right_count,
                tier1_count, consensus_score, consensus_tier
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["scan_id"],
                row["topic"],
                row.get("keywords", "[]"),
                row.get("headlines", "[]"),
                row.get("source_count", 0),
                row.get("left_count", 0),
                row.get("center_count", 0),
                row.get("right_count", 0),
                row.get("tier1_count", 0),
                row.get("consensus_score", 0.0),
                row.get("consensus_tier", ""),
            ))

    def get_latest_consensus(self) -> Dict[str, Any]:
        """Return consensus clusters from the most recent scan with metadata."""
        anchor = self.conn.execute(
            "SELECT scan_id, created_at FROM front_page_consensus "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not anchor:
            return {"clusters": [], "scanned_at": None, "scan_id": None}
        scan_id    = anchor["scan_id"]
        scanned_at = anchor["created_at"]
        rows = self.conn.execute(
            "SELECT * FROM front_page_consensus "
            "WHERE scan_id = ? ORDER BY consensus_score DESC",
            (scan_id,),
        ).fetchall()
        return {
            "clusters":   [dict(r) for r in rows],
            "scanned_at": scanned_at,
            "scan_id":    scan_id,
        }

    def get_consensus_archive(self) -> List[Dict[str, Any]]:
        """Return list of all distinct consensus scans, newest first."""
        rows = self.conn.execute("""
            SELECT scan_id,
                   MIN(created_at) AS created_at,
                   COUNT(*)        AS cluster_count
            FROM front_page_consensus
            GROUP BY scan_id
            ORDER BY MIN(created_at) DESC
        """).fetchall()
        return [dict(r) for r in rows]

    def get_consensus_by_scan_id(self, scan_id: str) -> Dict[str, Any]:
        """Return consensus clusters for a specific historical scan_id."""
        rows = self.conn.execute(
            "SELECT * FROM front_page_consensus "
            "WHERE scan_id = ? ORDER BY consensus_score DESC",
            (scan_id,),
        ).fetchall()
        if not rows:
            return {"clusters": [], "scanned_at": None, "scan_id": scan_id}
        return {
            "clusters":   [dict(r) for r in rows],
            "scanned_at": rows[0]["created_at"],
            "scan_id":    scan_id,
        }
// ==========================================
// SWAT SIGNAL DESK / AEGIS
// File: frontend/src/pages/RadarDashboard.jsx
// Phase: 1C (UX Correction — Scan / Sort Separation)
// Version: 005
// ==========================================

import { useEffect, useMemo, useState } from "react";
import {
  deleteSignal,
  fetchConsensus,
  fetchConsensusArchive,
  fetchConsensusScanStatus,
  fetchConsensusSnapshot,
  fetchRecent,
  fetchScanStatus,
  fetchSearchStatus,
  runConsensusScan,
  runScan,
  runSearchScan,
  trackReport,
} from "../lib/api";
import SignalCard from "../components/SignalCard";

// ------------------------------------
// Quick Scan presets
// Broad keyword sets used for targeted feed scans.
// Clicking a preset ADDS to the database; it does NOT filter the view.
// ------------------------------------
const PRESETS = [
  {
    label: "US Politics",
    terms: [
      "congress", "senate", "house representatives", "president", "democrat",
      "republican", "white house", "supreme court", "legislation", "trump",
      "biden", "harris", "political", "administration", "washington",
    ],
  },
  {
    label: "Economy",
    terms: [
      "economy", "inflation", "gdp", "recession", "federal reserve",
      "interest rate", "tariff", "unemployment", "jobs report", "stock market",
      "trade deficit", "budget", "debt ceiling", "oil prices", "wall street",
    ],
  },
  {
    label: "Tech",
    terms: [
      "artificial intelligence", "openai", "google", "microsoft", "apple",
      "nvidia", "cyber", "hack", "data breach", "software", "startup",
      "silicon valley", "regulation", "antitrust", "big tech",
    ],
  },
  {
    label: "Entertainment",
    terms: [
      "entertainment", "movie", "film", "music", "celebrity", "oscar",
      "grammy", "netflix", "hollywood", "album", "streaming", "television",
      "actor", "singer", "box office",
    ],
  },
  {
    label: "World/Conflict",
    terms: [
      "war", "conflict", "military", "nato", "ukraine", "russia", "israel",
      "hamas", "iran", "taiwan", "sanctions", "missile", "troops",
      "ceasefire", "attack",
    ],
  },
  {
    label: "Science/Space",
    terms: [
      "science", "space", "nasa", "climate", "research", "vaccine",
      "health", "cancer", "physics", "astronomy", "mars", "rocket",
      "launch", "discovery", "study",
    ],
  },
  {
    label: "Sports",
    terms: [
      "nfl", "nba", "mlb", "nhl", "soccer", "football", "basketball",
      "baseball", "championship", "playoffs", "world cup", "olympics",
      "athlete", "coach", "tournament",
    ],
  },
];

// ------------------------------------
// Clustering helpers
// ------------------------------------
const STOP_WORDS = new Set([
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
  "these", "those", "been", "from", "also", "with", "that",
]);

function getSignalWords(signal) {
  const text = `${signal.topic || ""} ${signal.title || ""} ${signal.summary || ""}`.toLowerCase();
  return new Set(
    text
      .replace(/[^a-z0-9\s]/g, " ")
      .split(/\s+/)
      .filter((w) => w.length >= 4 && !STOP_WORDS.has(w))
  );
}

function clusterSignals(signals) {
  if (!signals.length) return [];

  const wordSets = signals.map((s) => getSignalWords(s));
  const parent = signals.map((_, i) => i);

  function find(x) {
    while (parent[x] !== x) {
      parent[x] = parent[parent[x]];
      x = parent[x];
    }
    return x;
  }

  function union(x, y) {
    parent[find(x)] = find(y);
  }

  for (let i = 0; i < signals.length; i++) {
    for (let j = i + 1; j < signals.length; j++) {
      // Reduce threshold to 1 shared word when both signals are high-significance.
      // Root cause fix: geopolitical stories ("Iran strikes Kuwait" / "Central Command
      // responds to Iran") share only one distinctive geographic term but are the
      // same story. The old threshold of 2 prevented these from ever clustering.
      const bothHighSig =
        (signals[i].significance_score || 0) >= 0.55 &&
        (signals[j].significance_score || 0) >= 0.55;
      const threshold = bothHighSig ? 1 : 2;
      let overlap = 0;
      for (const w of wordSets[i]) {
        if (wordSets[j].has(w)) {
          overlap++;
          if (overlap >= threshold) break;
        }
      }
      if (overlap >= threshold) union(i, j);
    }
  }

  const groups = new Map();
  for (let i = 0; i < signals.length; i++) {
    const root = find(i);
    if (!groups.has(root)) groups.set(root, []);
    groups.get(root).push(signals[i]);
  }

  return Array.from(groups.values())
    .sort((a, b) => b.length - a.length)
    .map((group) => {
      if (group.length === 1) return { label: null, signals: group };

      const freq = new Map();
      for (const s of group) {
        for (const w of getSignalWords(s)) {
          freq.set(w, (freq.get(w) || 0) + 1);
        }
      }
      const topWords = Array.from(freq.entries())
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([w]) => w);

      return { label: topWords.join(" · "), signals: group };
    });
}

// ------------------------------------
// Cluster Worthiness Scoring (Stage 8)
// ------------------------------------

const FRONT_PAGE_PATTERNS = [
  // Constitutional / governmental
  "scotus", "supreme court", "constitutional ruling", "impeachment", "martial law",
  "election fraud", "surveillance expansion", "mass censorship", "lobbying scandal",
  "whistleblower", "classified leak", "indictment", "government shutdown",
  "debt default", "white house", "congress", "senate", "federal reserve",
  "debt ceiling", "trump", "executive order",
  // Military / conflict
  "war escalation", "military strike", "missile attack", "ceasefire", "coup",
  "assassination", "chemical weapon", "nuclear", "troops", "foreign policy",
  "nato", "cyber attack", "infrastructure attack", "market crash",
  "economic collapse", "airstrike", "air strike", "ground offensive",
  "military invasion", "naval blockade", "central command", "pentagon",
  "joint chiefs", "nato article", "strait of hormuz", "oil embargo", "oil shock",
  // Key geopolitical actors
  "iran", "israel", "ukraine", "russia", "taiwan", "north korea",
  "hezbollah", "hamas", "irgc", "idf", "kuwait",
  // Health emergencies
  "outbreak", "epidemic", "public health emergency", "ebola", "pandemic",
  "who declares",
  // Accountability
  "no-bid contract", "defense fraud",
];

const SECTION_PATTERNS = [
  "legislation", "federal agency", "regulation", "political realignment",
  "election", "campaign", "ballot", "fbi ", "cia ", "nsa ", "doj ",
  "investigation", "verdict", "trial", "climate", "energy policy",
  "oil prices", "sanctions", "trade war", "tariff", "protest",
  "civil rights", "human rights", "immigration", "border",
  "artificial intelligence", "openai", "surveillance tech",
  "healthcare", "opioid", "fentanyl", "public health",
  "antitrust", "merger", "acquisition", "federal",
  // Economic
  "oil production", "opec", "energy crisis", "central bank",
  "interest rates", "treasury", "market volatility", "recession fears",
  "stock market", "gdp",
  // Defense / contracting
  "defense contractor", "government contract", "procurement fraud",
  "military contract", "no-bid",
  // Health
  "disease outbreak", "cdc warning", "health emergency", "fda approval",
  "drug recall",
  // Diplomacy
  "diplomatic talks", "peace negotiations", "ceasefire talks",
  "treaty", "sanctions relief",
  // Domestic
  "hurricane", "earthquake", "natural disaster", "mass shooting",
  "gun violence", "school shooting",
];

const BACK_PAGE_PATTERNS = [
  "oura ring", "fitness tracker", "smartwatch", "wearable tech",
  "product launch", "product review", "new iphone", "pixel phone",
  "netflix", "streaming", "box office", "grammy", "oscar",
  "golden globe", "celebrity", "lifestyle", "recipe", "workout",
  "nfl draft", "nba ", "mlb season", "nhl ", "soccer tournament",
  "gadget review", "deal alert", "limited edition",
  "laptop review", "chip benchmark", "phone review", "tablet review",
  "app update", "software update", "firmware update",
  "gaming news", "esports", "video game review",
  "crypto price", "bitcoin price", "nft ",
  "fashion show", "beauty product", "cosmetics",
];

const TIER_LABELS = {
  front_page: "FRONT PAGE",
  major: "MAJOR",
  section: "SECTION",
  back_page: "BACK PAGE",
  noise: "NOISE",
};

function getClusterTier(score) {
  if (score >= 0.80) return "front_page";
  if (score >= 0.60) return "major";
  if (score >= 0.40) return "section";
  if (score >= 0.20) return "back_page";
  return "noise";
}

function scoreCluster(cluster) {
  const signals = cluster.signals;
  const count = signals.length;
  const combinedText = signals
    .map((s) => `${s.title || ""} ${s.topic || ""} ${s.summary || ""}`)
    .join(" ")
    .toLowerCase();
  const labelText = (cluster.label || "").toLowerCase();
  const searchText = `${combinedText} ${labelText}`;

  const maxSig = Math.max(...signals.map((s) => s.significance_score || 0));
  const avgSig = signals.reduce((acc, s) => acc + (s.significance_score || 0), 0) / count;
  const uniqueSources = new Set(signals.map((s) => s.feed_name || s.source || "")).size;

  let score = 0;
  score += maxSig * 0.40;  // raised from 0.35 — maxSig is the editorial backbone
  score += avgSig * 0.20;
  if (count >= 5) score += 0.15;
  else if (count >= 3) score += 0.10;
  else if (count >= 2) score += 0.05;
  score += Math.min(uniqueSources / 5, 1) * 0.10;

  let boost = 0;
  let penalty = 0;
  let reason = "";

  // Root cause fix: accumulate front-page keyword hits instead of breaking
  // on the first match.  An Iran cluster with "iran" + "military" + "missile"
  // previously only got +0.35 (one match).  Now it accumulates up to +0.50.
  let fpHits = 0;
  for (const kw of FRONT_PAGE_PATTERNS) {
    if (searchText.includes(kw)) {
      fpHits++;
      if (!reason) reason = "High-importance topic";
    }
  }
  if (fpHits > 0) {
    boost = Math.min(fpHits * 0.18, 0.50);
  } else {
    // Section boost: separate accumulation, lower ceiling
    let secHits = 0;
    for (const kw of SECTION_PATTERNS) {
      if (searchText.includes(kw)) {
        secHits++;
        if (!reason) reason = "National / policy relevance";
      }
    }
    boost = Math.min(secHits * 0.08, 0.20);
  }

  for (const kw of BACK_PAGE_PATTERNS) {
    if (searchText.includes(kw)) {
      penalty = Math.max(penalty, 0.25);
      if (!reason) reason = "Consumer or entertainment content";
      break;
    }
  }

  score = Math.max(0, Math.min(1.0, score + boost - penalty));

  // --- Source Intelligence: Corroboration + Reliability Caps (Stage 10) ---
  //
  // Corroboration bonus: awarded when sources span multiple editorial orientations
  // or when Tier 1 (wire service) sources are present in the cluster.
  //
  // Design rules:
  //   - left+center+right all present: +0.20  (full editorial consensus)
  //   - center + one of left/right: +0.10      (partial cross-spectrum)
  //   - left+right without center: no bonus   (contested framing, not corroboration)
  //   - 2+ Tier 1 sources: +0.20               (multiple wire services confirm)
  //   - 1 Tier 1 source: +0.10                 (single wire anchor)
  //
  // Reliability caps: watchlist/tier-4 sources cannot front-page a story alone.
  //   - All sources Tier 4 (watchlist/social): cap at 0.59 (never FRONT_PAGE)
  //   - All sources Tier 3+ (no Tier 1/2): cap at 0.79    (never FRONT_PAGE)

  const orientations = new Set(
    signals.map((s) => s.source_orientation).filter(Boolean)
  );
  const tiers = signals.map((s) => s.reliability_tier || 4);
  const tier1Count = tiers.filter((t) => t === 1).length;
  const allTier4 = tiers.every((t) => t >= 4);
  const allLowReliability = tiers.every((t) => t >= 3);

  let corrBonus = 0;
  if (
    orientations.has("left") &&
    orientations.has("center") &&
    orientations.has("right")
  ) {
    corrBonus += 0.20;
    if (!reason) reason = "Cross-spectrum corroboration";
  } else if (
    orientations.has("center") &&
    (orientations.has("left") || orientations.has("right"))
  ) {
    corrBonus += 0.10;
  }

  if (tier1Count >= 2) corrBonus += 0.20;
  else if (tier1Count === 1) corrBonus += 0.10;

  score = Math.min(1.0, score + corrBonus);

  // Apply reliability caps after all bonuses
  if (allTier4) {
    score = Math.min(score, 0.59);  // watchlist-only: never FRONT_PAGE
  } else if (allLowReliability) {
    score = Math.min(score, 0.79);  // Tier 3+4 only: never FRONT_PAGE
  }

  const tier = getClusterTier(score);

  if (!reason) {
    if (tier === "front_page") reason = "Multiple high-significance sources";
    else if (tier === "major") reason = "Strong cross-source coverage";
    else if (tier === "section") reason = "Moderate regional or topic interest";
    else if (tier === "back_page") reason = "Limited editorial significance";
    else reason = "Low significance";
  }

  return { cluster_importance: score, cluster_tier: tier, cluster_reason: reason };
}

function shouldCompressCluster(scored) {
  return (
    (scored.cluster_tier === "back_page" || scored.cluster_tier === "noise") &&
    scored.signals.length >= 3
  );
}

// ------------------------------------
// Stage 11: Front Page Consensus Card
// ------------------------------------

const CONSENSUS_TIER_LABELS = {
  confirmed: "CONFIRMED",
  elevated:  "ELEVATED",
  monitored: "MONITORED",
};

function ConsensusCard({ cluster }) {
  const [expanded, setExpanded] = useState(false);
  const headlines = (() => {
    try { return JSON.parse(cluster.headlines || "[]"); } catch { return []; }
  })();

  return (
    <div className={`consensus-card consensus-tier-${cluster.consensus_tier}`}>
      <div className="consensus-card-header">
        <div className="consensus-card-left">
          <span className="consensus-tier-badge">
            {CONSENSUS_TIER_LABELS[cluster.consensus_tier] || (cluster.consensus_tier || "").toUpperCase()}
          </span>
          <span className="consensus-topic">{cluster.topic}</span>
        </div>
        <div className="consensus-card-right">
          <span className="consensus-source-count">
            {cluster.source_count} source{cluster.source_count !== 1 ? "s" : ""}
          </span>
          {headlines.length > 0 && (
            <button className="cluster-expand-btn" onClick={() => setExpanded((p) => !p)}>
              {expanded ? "Less" : "Headlines"}
            </button>
          )}
        </div>
      </div>
      <div className="consensus-orientation-bar">
        {cluster.left_count > 0 && (
          <span className="orient-pill orient-left">LEFT ×{cluster.left_count}</span>
        )}
        {cluster.center_count > 0 && (
          <span className="orient-pill orient-center">CENTER ×{cluster.center_count}</span>
        )}
        {cluster.right_count > 0 && (
          <span className="orient-pill orient-right">RIGHT ×{cluster.right_count}</span>
        )}
        {cluster.tier1_count > 0 && (
          <span className="orient-pill orient-wire">WIRE ×{cluster.tier1_count}</span>
        )}
        <span className="consensus-score-pill">
          {Math.round((cluster.consensus_score || 0) * 100)}%
        </span>
      </div>
      {expanded && headlines.length > 0 && (
        <div className="consensus-headlines-list">
          {headlines.slice(0, 6).map((h, idx) => (
            <div key={idx} className="consensus-headline-row">
              <span className={`orient-dot orient-dot-${h.orientation}`} />
              {h.url ? (
                <a
                  href={h.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="consensus-headline-text"
                >
                  {h.title}
                </a>
              ) : (
                <span className="consensus-headline-text">{h.title}</span>
              )}
              <span className="consensus-headline-source">{h.source_name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ------------------------------------
// Component
// ------------------------------------
export default function RadarDashboard() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [keywordScanning, setKeywordScanning] = useState(false);
  const [error, setError] = useState("");
  const [scanMessage, setScanMessage] = useState("");
  const [keywordMessage, setKeywordMessage] = useState("");
  const [searchQuery, setSearchQuery] = useState("");   // feed-scan input
  const [sortQuery, setSortQuery] = useState("");        // local filter (never scans)
  const [lastQuickScan, setLastQuickScan] = useState(null); // label of last preset run
  // AEGIS: sort mode and filtered-item visibility
  const [sortMode, setSortMode] = useState("significance"); // "significance" | "recency"
  const [showFiltered, setShowFiltered] = useState(false);  // filtered = noise/low-quality items
  // Delete confirmation: stores the item.id awaiting in-card confirmation.
  // Avoids window.confirm(), which browsers can suppress or permanently silence.
  const [pendingDeleteId, setPendingDeleteId] = useState(null);
  // Bulk selection: Set of item ids currently checked by the user.
  const [selectedIds, setSelectedIds] = useState(new Set());
  // When true, the bulk action bar shows a confirm prompt instead of the action buttons.
  const [bulkDeletePending, setBulkDeletePending] = useState(false);
  // Active view: "live" = untracked feed triage, "library" = saved report archive
  const [activeView, setActiveView] = useState("library");
  // Tracks which compressed (back_page / noise) clusters have been manually expanded
  const [expandedClusters, setExpandedClusters] = useState(new Set());
  // Controls whether the low-significance "Unclustered Reports" footer is expanded
  const [unclusteredExpanded, setUnclusteredExpanded] = useState(false);
  // Stage 11: Front Page Editorial Consensus
  const [consensusData, setConsensusData] = useState([]);
  const [consensusScanning, setConsensusScanning] = useState(false);
  const [consensusMessage, setConsensusMessage] = useState("");
  const [consensusScannedAt, setConsensusScannedAt] = useState(null);
  // Stage 13: Consensus Archive
  const [consensusArchive, setConsensusArchive] = useState([]);
  const [showArchive, setShowArchive] = useState(false);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [selectedScanId, setSelectedScanId] = useState(null); // null = current latest

  useEffect(() => {
    loadData(false, "library");
    checkScanStatus(true);
    loadConsensus();
  }, []);

  useEffect(() => {
    if (!scanning) return;
    const interval = setInterval(() => checkScanStatus(), 2500);
    return () => clearInterval(interval);
  }, [scanning]);

  useEffect(() => {
    if (!keywordScanning) return;
    const interval = setInterval(() => checkKeywordScanStatus(), 2500);
    return () => clearInterval(interval);
  }, [keywordScanning]);

  useEffect(() => {
    if (!consensusScanning) return;
    const interval = setInterval(() => checkConsensusScanStatus(), 2500);
    return () => clearInterval(interval);
  }, [consensusScanning]);

  // AEGIS: includeFiltered controls whether noise/filtered signals are fetched.
  // Defaults to false. Callers that have changed showFiltered must pass the new value.
  // Clears bulk selection on every reload so stale ids don't linger.
  async function loadData(includeFiltered = false, view = activeView) {
    setLoading(true);
    setError("");
    try {
      const trackedOnly = view === "library";
      const liveOnly = view === "live";
      const result = await fetchRecent(100, includeFiltered, trackedOnly, liveOnly);
      setItems(result);
      setSelectedIds(new Set());
      setBulkDeletePending(false);
    } catch (err) {
      setError(err.message || "Failed to load data.");
    } finally {
      setLoading(false);
    }
  }

  async function switchView(newView) {
    setActiveView(newView);
    setSortQuery("");
    setLastQuickScan(null);
    setScanMessage("");
    setKeywordMessage("");
    await loadData(showFiltered, newView);
  }

  async function checkScanStatus(silent = false) {
    try {
      const result = await fetchScanStatus();
      const scan = result.scan || {};

      if (scan.running) {
        setScanning(true);
        setScanMessage("Refreshing reports...");
        return;
      }

      setScanning(false);

      if (scan.summary) {
        const { stored = 0, filtered = 0, failed = 0 } = scan.summary;
        const parts = [];
        if (stored > 0) parts.push(`${stored} reports added`);
        if (filtered > 0) parts.push(`${filtered} filtered`);
        if (failed > 0) parts.push(`${failed} failed`);
        setScanMessage(`Refresh complete${parts.length ? ` — ${parts.join(", ")}` : ""}.`);
        await loadData();
        return;
      }

      if (scan.error) {
        setError(scan.error);
        setScanMessage("Refresh failed.");
        return;
      }

      setScanMessage("");
      if (!silent) await loadData();
    } catch (err) {
      setScanning(false);
      if (!silent) setError(err.message || "Scan status error.");
    }
  }

  async function handleRunScan() {
    setError("");
    setScanMessage("Refreshing reports...");
    setScanning(true);
    try {
      await runScan();
      await checkScanStatus();
    } catch (err) {
      setScanning(false);
      setError(err.message || "Scan failed.");
      setScanMessage("");
    }
  }

  async function checkKeywordScanStatus(silent = false) {
    try {
      const result = await fetchSearchStatus();
      const scan = result.scan || {};

      if (scan.running) {
        setKeywordScanning(true);
        const qLabel = scan.query ? ` "${scan.query}"` : "";
        setKeywordMessage(`Searching feeds${qLabel}...`);
        return;
      }

      setKeywordScanning(false);

      if (scan.summary) {
        const { matched = 0, stored = 0 } = scan.summary;
        setKeywordMessage(`Search complete — ${matched} found, ${stored} saved.`);
        await loadData();
        return;
      }

      if (scan.error) {
        setError(scan.error);
        setKeywordMessage("Topic search failed.");
        return;
      }

      setKeywordMessage("");
      if (!silent) await loadData();
    } catch (err) {
      setKeywordScanning(false);
      if (!silent) setError(err.message || "Keyword scan status error.");
    }
  }

  async function handleSearchScan(queryOverride) {
    const q = (queryOverride !== undefined ? queryOverride : searchQuery).trim();
    if (!q) return;
    setError("");
    setKeywordMessage(`Starting topic search...`);
    setKeywordScanning(true);
    try {
      await runSearchScan(q);
      await checkKeywordScanStatus();
    } catch (err) {
      setKeywordScanning(false);
      setError(err.message || "Keyword scan failed.");
      setKeywordMessage("");
    }
  }

  // Delete flow — uses in-card confirm state instead of window.confirm().
  // window.confirm() can be permanently suppressed by browsers; this approach is reliable.
  function handleDelete(item) {
    if (!item.id) return;
    setPendingDeleteId(item.id);
  }

  async function handleConfirmDelete() {
    if (!pendingDeleteId) return;
    const idToDelete = pendingDeleteId;
    setPendingDeleteId(null);
    try {
      await deleteSignal(idToDelete);
      setItems((current) => current.filter((e) => e.id !== idToDelete));
      setSelectedIds((prev) => {
        if (!prev.has(idToDelete)) return prev;
        const next = new Set(prev);
        next.delete(idToDelete);
        return next;
      });
    } catch (err) {
      setError(err.message || "Delete failed.");
    }
  }

  async function handleTrackReport(item) {
    if (!item.id) return;
    try {
      await trackReport(item.id);
      // In live view, remove from feed once saved to library
      if (activeView === "live") {
        setItems((current) => current.filter((e) => e.id !== item.id));
      }
    } catch (err) {
      setError(err.message || "Failed to save report.");
    }
  }

  function handleCancelDelete() {
    setPendingDeleteId(null);
  }

  // ------------------------------------
  // Bulk selection handlers
  // ------------------------------------
  function handleToggleSelected(id) {
    if (!id) return;
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function handleSelectAll() {
    setSelectedIds(new Set(filteredItems.map((item) => item.id).filter(Boolean)));
  }

  function handleSelectNone() {
    setSelectedIds(new Set());
    setBulkDeletePending(false);
  }

  function handleBulkDelete() {
    if (selectedIds.size === 0) return;
    setBulkDeletePending(true);
  }

  async function handleBulkDeleteConfirm() {
    const ids = Array.from(selectedIds);
    setBulkDeletePending(false);
    setSelectedIds(new Set());
    const failed = [];
    for (const id of ids) {
      try {
        await deleteSignal(id);
      } catch {
        failed.push(id);
      }
    }
    const deletedIds = new Set(ids.filter((id) => !failed.includes(id)));
    setItems((current) => current.filter((e) => !deletedIds.has(e.id)));
    if (failed.length > 0) {
      setError(`${failed.length} report(s) could not be deleted.`);
    }
  }

  function handleBulkDeleteCancel() {
    setBulkDeletePending(false);
  }

  function toggleClusterExpand(i) {
    setExpandedClusters((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  }

  function handlePresetClick(preset) {
    // Quick Scan: runs a targeted feed scan and marks the last-used preset.
    // Does NOT apply a local filter — all stored signals remain visible.
    setLastQuickScan(preset.label);
    handleSearchScan(preset.terms.join(" "));
  }

  function handleSearchChange(e) {
    setSearchQuery(e.target.value);
  }

  async function showAllSignals() {
    setSortQuery("");
    setSearchQuery("");
    setLastQuickScan(null);
    setScanMessage("");
    setKeywordMessage("");
    await loadData(showFiltered);
  }

  // AEGIS: Toggle visibility of filtered (noise) signals.
  // Reloads data from the API with the updated setting.
  async function handleToggleFiltered() {
    const next = !showFiltered;
    setShowFiltered(next);
    await loadData(next);
  }

  // Stage 11: Front Page Consensus handlers
  async function loadConsensus() {
    try {
      const result = await fetchConsensus();
      setConsensusData(result.clusters || []);
      if (result.scanned_at) setConsensusScannedAt(result.scanned_at);
      setSelectedScanId(null);
    } catch {
      // Silently ignore — no consensus data yet is a valid empty state
    }
  }

  async function checkConsensusScanStatus() {
    try {
      const result = await fetchConsensusScanStatus();
      const scan = result.scan || {};
      if (scan.running) {
        setConsensusScanning(true);
        setConsensusMessage("Scanning front pages...");
        return;
      }
      setConsensusScanning(false);
      if (scan.summary) {
        const { stored = 0 } = scan.summary;
        setConsensusMessage(
          `Front page scan complete — ${stored} consensus topic${stored !== 1 ? "s" : ""} found.`
        );
        await loadConsensus();
        // Refresh archive list silently so the new entry appears
        if (showArchive) {
          const archResult = await fetchConsensusArchive();
          setConsensusArchive(archResult.snapshots || []);
        }
        return;
      }
      if (scan.error) {
        setConsensusMessage(`Front page scan error: ${scan.error}`);
        return;
      }
      setConsensusMessage("");
    } catch {
      setConsensusScanning(false);
    }
  }

  async function handleConsensusScan() {
    setConsensusMessage("Starting front page scan...");
    setConsensusScanning(true);
    try {
      await runConsensusScan();
      await checkConsensusScanStatus();
    } catch {
      setConsensusScanning(false);
      setConsensusMessage("Front page scan failed to start.");
    }
  }

  // Stage 13: Archive handlers
  async function handleToggleArchive() {
    const next = !showArchive;
    setShowArchive(next);
    if (next) {
      setArchiveLoading(true);
      try {
        const result = await fetchConsensusArchive();
        setConsensusArchive(result.snapshots || []);
      } catch {
        // ignore
      } finally {
        setArchiveLoading(false);
      }
    }
  }

  async function handleLoadSnapshot(scanId) {
    try {
      const result = await fetchConsensusSnapshot(scanId);
      setConsensusData(result.clusters || []);
      if (result.scanned_at) setConsensusScannedAt(result.scanned_at);
      setSelectedScanId(scanId);
    } catch {
      // ignore
    }
  }

  function handleViewCurrentScan() {
    loadConsensus();
  }

  // Stage 13: Bulk Save to Library (Live Feed only)
  async function handleBulkSave() {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    const failed = [];
    for (const id of ids) {
      try {
        await trackReport(id);
      } catch {
        failed.push(id);
      }
    }
    const savedIds = new Set(ids.filter((id) => !failed.includes(id)));
    setItems((current) => current.filter((e) => !savedIds.has(e.id)));
    setSelectedIds(new Set());
    if (failed.length > 0) {
      setError(`${failed.length} report(s) could not be saved to Library.`);
    }
  }

  // ------------------------------------
  // Local filter (sortQuery only — never tied to feed scans)
  // ------------------------------------
  const filteredItems = useMemo(() => {
    // Step 1: Apply local text filter (never triggers a feed scan)
    let result = items;
    if (sortQuery.trim()) {
      const q = sortQuery.trim().toLowerCase();
      result = result.filter((item) => {
        const haystack = [
          item.title,
          item.topic,
          item.summary,
          item.framing,
          item.claims,
          item.source,
          item.feed_name,
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(q);
      });
    }

    // Step 2: Apply sort — significance DESC (AEGIS default) or recency (API order)
    if (sortMode === "significance") {
      return [...result].sort(
        (a, b) => (b.significance_score || 0) - (a.significance_score || 0)
      );
    }
    return result;
  }, [items, sortQuery, sortMode]);

  // ------------------------------------
  // Clustering
  // ------------------------------------
  const clusters = useMemo(
    () => clusterSignals(filteredItems),
    [filteredItems]
  );

  const scoredClusters = useMemo(
    () => clusters.map((c) => ({ ...c, ...scoreCluster(c) })),
    [clusters]
  );

  const anyScanning = scanning || keywordScanning;
  const isFiltered = !!sortQuery.trim();
  // Named clusters = multi-signal groups that formed a cluster label
  const namedClusters = scoredClusters.filter((c) => c.label !== null).length;
  // Main display list: every cluster/single-report with meaningful importance.
  // Single high-significance reports now appear here with their topic as label
  // instead of being buried in "Other Reports" — root cause fix for Stage 10.
  const mainClusterList = scoredClusters
    .filter((c) => c.cluster_importance >= 0.20)
    .sort((a, b) => b.cluster_importance - a.cluster_importance);
  // Unclustered: true noise only — low-significance items sorted by sig score
  const unclusteredSignals = scoredClusters
    .filter((c) => c.cluster_importance < 0.20)
    .flatMap((c) => c.signals)
    .sort((a, b) => (b.significance_score || 0) - (a.significance_score || 0));

  return (
    <div className="radar-dashboard">
      <header className="dashboard-header">
        <div className="header-brand">
          <h1 className="aegis-title">AEGIS</h1>
          <p className="aegis-subtitle">Artificial Event &amp; Global Intelligence System</p>
          <p className="team-label">SWAT Signal Desk</p>
        </div>
        <div className="header-actions">
          {anyScanning && <span className="live-indicator">LIVE</span>}
          <button className="run-scan-btn" onClick={handleRunScan} disabled={anyScanning}>
            {scanning ? "Scanning..." : "Refresh Reports"}
          </button>
        </div>
      </header>

      <div className="view-tabs">
        <button
          className={`view-tab${activeView === "live" ? " active" : ""}`}
          onClick={() => switchView("live")}
        >
          Live Feed
        </button>
        <button
          className={`view-tab${activeView === "library" ? " active" : ""}`}
          onClick={() => switchView("library")}
        >
          Report Library
        </button>
      </div>

      <div className="controls">
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search all feeds for a topic..."
            value={searchQuery}
            onChange={handleSearchChange}
            onKeyDown={(e) => { if (e.key === "Enter") handleSearchScan(); }}
            disabled={keywordScanning}
          />
          <button
            className="scan-btn"
            onClick={() => handleSearchScan()}
            disabled={anyScanning || !searchQuery.trim()}
            title="Search all configured feeds for this topic"
          >
            {keywordScanning ? "Scanning..." : "Search"}
          </button>
          {searchQuery && (
            <button className="clear-btn" onClick={() => setSearchQuery("")}>
              ✕
            </button>
          )}
        </div>
        <span className="row-label">Topic Presets</span>
        <div className="preset-buttons">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              className={`preset-btn${lastQuickScan === p.label ? " last-used" : ""}`}
              onClick={() => handlePresetClick(p)}
              disabled={anyScanning}
              title={`Scan feeds for: ${p.terms.slice(0, 4).join(", ")}...`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {scanMessage && <div className="loading-box">{scanMessage}</div>}
      {keywordMessage && <div className="loading-box keyword-msg">{keywordMessage}</div>}
      {error && <div className="error-box">{error}</div>}
      {loading && <div className="loading-box">Loading...</div>}

      {/* Stage 11/13: Front Page Editorial Consensus + Archive */}
      <div className="consensus-panel">
        <div className="consensus-panel-header">
          <div className="consensus-panel-header-left">
            <span className="consensus-panel-title">Front Page Consensus</span>
            {consensusScannedAt && (
              <span className="consensus-panel-timestamp">
                {selectedScanId ? "archive \u00b7 " : "scanned "}{consensusScannedAt}
              </span>
            )}
          </div>
          <div className="consensus-panel-header-right">
            {selectedScanId && (
              <button className="consensus-nav-btn" onClick={handleViewCurrentScan}>
                \u2190 Current
              </button>
            )}
            <button
              className={`consensus-archive-btn${showArchive ? " active" : ""}`}
              onClick={handleToggleArchive}
              title="View previous consensus scans"
            >
              {showArchive ? "Hide Archive" : "Archive"}
            </button>
            <button
              className="consensus-scan-btn"
              onClick={handleConsensusScan}
              disabled={consensusScanning}
            >
              {consensusScanning ? "Scanning..." : "Scan Front Pages"}
            </button>
          </div>
        </div>

        {showArchive && (
          <div className="consensus-archive-panel">
            <div className="consensus-archive-title">Previous Scans</div>
            {archiveLoading ? (
              <div className="consensus-archive-empty">Loading archive...</div>
            ) : consensusArchive.length === 0 ? (
              <div className="consensus-archive-empty">No previous scans saved yet.</div>
            ) : (
              <div className="consensus-archive-list">
                {consensusArchive.map((snap) => (
                  <button
                    key={snap.scan_id}
                    className={`consensus-archive-item${selectedScanId === snap.scan_id ? " active" : ""}`}
                    onClick={() => handleLoadSnapshot(snap.scan_id)}
                    title={`Load scan from ${snap.created_at}`}
                  >
                    <span className="archive-item-time">{snap.created_at}</span>
                    <span className="archive-item-count">
                      {snap.cluster_count} topic{snap.cluster_count !== 1 ? "s" : ""}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {consensusMessage && (
          <div className="loading-box consensus-msg">{consensusMessage}</div>
        )}
        {consensusData.length > 0 ? (
          <div className="consensus-grid">
            {consensusData.map((cluster, i) => (
              <ConsensusCard key={`${cluster.scan_id}-${i}`} cluster={cluster} />
            ))}
          </div>
        ) : (
          !consensusScanning && (
            <div className="consensus-empty">
              No front page consensus data. Click "Scan Front Pages" to analyze the editorial landscape across 15 major outlets.
            </div>
          )
        )}
      </div>

      {/* Sort / Filter section — local filter only, never triggers a scan */}
      <div className="sort-section">
        <span className="row-label">{activeView === "live" ? "Live Feed" : "Report Library"}</span>
        <div className="sort-bar">
          <input
            type="text"
            placeholder="Filter by title, topic, source, framing..."
            value={sortQuery}
            onChange={(e) => setSortQuery(e.target.value)}
          />
          {sortQuery && (
            <button className="clear-sort-btn" onClick={() => setSortQuery("")} title="Clear filter">
              ✕
            </button>
          )}
        </div>
        <div className="view-state">
          <span className={`state-label${isFiltered ? " is-filtered" : lastQuickScan ? " has-scan" : ""}`}>
            {isFiltered
              ? `Filtered: "${sortQuery.trim()}"`
              : lastQuickScan
              ? `Last search: ${lastQuickScan}`
              : activeView === "library" ? "Showing all saved reports" : "Showing live feed"}
          </span>
          {(isFiltered || lastQuickScan) && (
            <button className="show-all-btn" onClick={showAllSignals}>
              Show All Reports
            </button>
          )}
        </div>

        <div className="sort-controls-row">
          <span className="row-label">View</span>
          <div className="sort-mode-buttons">
            <button
              className={`sort-mode-btn${sortMode === "significance" ? " active" : ""}`}
              onClick={() => setSortMode("significance")}
              title="Sort by significance — most important signals first"
            >
              Most Important
            </button>
            <button
              className={`sort-mode-btn${sortMode === "recency" ? " active" : ""}`}
              onClick={() => setSortMode("recency")}
              title="Sort by most recently added"
            >
              Newest
            </button>
            <button
              className={`show-filtered-btn${showFiltered ? " active" : ""}`}
              onClick={handleToggleFiltered}
              disabled={loading}
              title={showFiltered ? "Hide AI-filtered/noise reports" : "Show AI-filtered/noise reports"}
            >
              Filtered Reports
            </button>
          </div>
        </div>
      </div>

      {!loading && filteredItems.length === 0 && (
        <div className="empty-box">
          {isFiltered ? `No reports match "${sortQuery.trim()}".` : activeView === "library" ? "No reports saved yet. Use Live Feed to save reports to the library." : "No live feed items. Refresh to pull new reports."}
        </div>
      )}

      {!loading && filteredItems.length > 0 && (
        <div className="results-summary">
          {filteredItems.length} report{filteredItems.length !== 1 ? "s" : ""}
          {isFiltered ? ` matching "${sortQuery.trim()}"` : ` tracked`}
          {mainClusterList.length > 0 && (
            <> &middot; {mainClusterList.length} cluster{mainClusterList.length !== 1 ? "s" : ""}</>
          )}
        </div>
      )}

      {/* Bulk selection action bar — visible whenever there are rendered signals */}
      {!loading && filteredItems.length > 0 && (
        <div className="bulk-action-bar">
          {bulkDeletePending ? (
            // In-app confirm prompt — no window.confirm() dependency.
            <>
              <span className="bulk-confirm-label">
                Delete {selectedIds.size} report{selectedIds.size !== 1 ? "s" : ""}? This cannot be undone.
              </span>
              <button
                type="button"
                className="bulk-confirm-btn"
                onClick={handleBulkDeleteConfirm}
              >
                Yes, Delete All
              </button>
              <button
                type="button"
                className="bulk-cancel-btn"
                onClick={handleBulkDeleteCancel}
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className="bulk-select-btn"
                onClick={handleSelectAll}
                title="Select all visible signals"
              >
                Select All
              </button>
              <button
                type="button"
                className="bulk-select-btn"
                onClick={handleSelectNone}
                disabled={selectedIds.size === 0}
                title="Clear selection"
              >
                Select None
              </button>
              <span className="bulk-count-label">
                {selectedIds.size > 0
                  ? `${selectedIds.size} selected`
                  : `${filteredItems.length} report${filteredItems.length !== 1 ? "s" : ""}`}
              </span>
              {activeView === "live" && (
                <button
                  type="button"
                  className="bulk-save-btn"
                  onClick={handleBulkSave}
                  disabled={selectedIds.size === 0}
                  title="Save selected reports to Report Library"
                >
                  Save to Library
                </button>
              )}
              <button
                type="button"
                className="bulk-delete-btn"
                onClick={handleBulkDelete}
                disabled={selectedIds.size === 0}
                title="Delete all selected signals"
              >
                Delete Selected
              </button>
            </>
          )}
        </div>
      )}

      <main className="dashboard-body">
        <section className="signal-list">
          {mainClusterList.map((cluster, i) => {
            const isSingleSource = cluster.label === null;
            const displayLabel = cluster.label
              || (cluster.signals[0]?.topic || cluster.signals[0]?.title || "Developing Story").slice(0, 90);
            const compressed = shouldCompressCluster(cluster);
            const isExpanded = expandedClusters.has(i);
            const visibleSignals = compressed && !isExpanded ? [cluster.signals[0]] : cluster.signals;
            return (
              <div key={i} className={`signal-cluster cluster-tier-${cluster.cluster_tier}`}>
                <div className={`cluster-heading tier-${cluster.cluster_tier}`}>
                  <div className="cluster-heading-left">
                    <span className="cluster-tier-badge">{TIER_LABELS[cluster.cluster_tier]}</span>
                    <span className="cluster-label">{displayLabel}</span>
                    {isSingleSource && (
                      <span className="single-source-tag">SINGLE SOURCE</span>
                    )}
                  </div>
                  <div className="cluster-heading-right">
                    {cluster.cluster_reason && (
                      <span className="cluster-reason">{cluster.cluster_reason}</span>
                    )}
                    <span className="cluster-count">
                      {cluster.signals.length} report{cluster.signals.length !== 1 ? "s" : ""}
                    </span>
                    {compressed && (
                      <button
                        className="cluster-expand-btn"
                        onClick={() => toggleClusterExpand(i)}
                      >
                        {isExpanded ? "Collapse" : "Show All"}
                      </button>
                    )}
                  </div>
                </div>
                {visibleSignals.map((item) => (
                  <SignalCard
                    key={item.id || item.url}
                    item={item}
                    compact={compressed && !isExpanded}
                    viewMode={activeView}
                    onDelete={() => handleDelete(item)}
                    isPendingDelete={pendingDeleteId === item.id}
                    onConfirmDelete={handleConfirmDelete}
                    onCancelDelete={handleCancelDelete}
                    isSelected={selectedIds.has(item.id)}
                    onToggleSelected={() => handleToggleSelected(item.id)}
                    onTrack={() => handleTrackReport(item)}
                  />
                ))}
              </div>
            );
          })}
          {unclusteredSignals.length > 0 && (
            <div className="signal-cluster unclustered-section">
              <div className="cluster-heading other-reports">
                <div className="cluster-heading-left">
                  <span className="cluster-label">Unclustered Reports</span>
                </div>
                <div className="cluster-heading-right">
                  <span className="cluster-count">{unclusteredSignals.length} report{unclusteredSignals.length !== 1 ? "s" : ""}</span>
                  <button
                    className="cluster-expand-btn"
                    onClick={() => setUnclusteredExpanded((p) => !p)}
                  >
                    {unclusteredExpanded ? "Collapse" : "Show"}
                  </button>
                </div>
              </div>
              {unclusteredExpanded && unclusteredSignals.map((item) => (
                <SignalCard
                  key={item.id || item.url}
                  item={item}
                  viewMode={activeView}
                  onDelete={() => handleDelete(item)}
                  isPendingDelete={pendingDeleteId === item.id}
                  onConfirmDelete={handleConfirmDelete}
                  onCancelDelete={handleCancelDelete}
                  isSelected={selectedIds.has(item.id)}
                  onToggleSelected={() => handleToggleSelected(item.id)}
                  onTrack={() => handleTrackReport(item)}
                />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

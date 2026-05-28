// ==========================================
// SWAT SIGNAL DESK
// File: frontend/src/lib/api.js
// Phase: 1B (Keyword Search + Simple Clustering)
// Version: 003
// ==========================================

const BASE_URL = "http://127.0.0.1:8002/api/radar";

async function requestJson(url, options = {}) {
  const res = await fetch(url, options);

  if (!res.ok) {
    let detail = "Request failed";

    try {
      const errorData = await res.json();
      detail = errorData.detail || detail;
    } catch {
      // Ignore non-JSON error bodies.
    }

    throw new Error(detail);
  }

  return res.json();
}

export async function fetchRecent(limit = 100, includeFiltered = false, trackedOnly = false, liveOnly = false) {
  const safeLimit = Math.max(1, Math.min(Number(limit) || 100, 200));
  const url = `${BASE_URL}/recent?limit=${safeLimit}&include_filtered=${includeFiltered}&tracked_only=${trackedOnly}&live_only=${liveOnly}`;
  const data = await requestJson(url);
  return data.data || [];
}

export async function runScan() {
  return requestJson(`${BASE_URL}/run`, {
    method: "POST",
  });
}

export async function fetchScanStatus() {
  return requestJson(`${BASE_URL}/scan-status`);
}

export async function deleteSignal(id) {
  return requestJson(`${BASE_URL}/${id}`, {
    method: "DELETE",
  });
}

export async function runSearchScan(query) {
  return requestJson(`${BASE_URL}/search-run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
}

export async function fetchSearchStatus() {
  return requestJson(`${BASE_URL}/search-status`);
}

export async function trackReport(id) {
  return requestJson(`${BASE_URL}/${id}/track`, { method: "PATCH" });
}

// Stage 11: Front Page Editorial Consensus
export async function runConsensusScan() {
  return requestJson(`${BASE_URL}/consensus-scan`, { method: "POST" });
}

export async function fetchConsensusScanStatus() {
  return requestJson(`${BASE_URL}/consensus-status`);
}

export async function fetchConsensus() {
  return requestJson(`${BASE_URL}/consensus`);
}

// Stage 13: Consensus Archive
export async function fetchConsensusArchive() {
  return requestJson(`${BASE_URL}/consensus/archive`);
}

export async function fetchConsensusSnapshot(scanId) {
  return requestJson(`${BASE_URL}/consensus/snapshot/${encodeURIComponent(scanId)}`);
}
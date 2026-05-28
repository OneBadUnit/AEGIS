# ==========================================
# SWAT SIGNAL DESK
# File: backend/app/api/routes/radar.py
# Phase: 1B (Keyword Search + Simple Clustering)
# Version: 003
# ==========================================

import threading
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.app.db.database import Database
from tasks.run_collectors import run_all_collectors, run_keyword_scan
from tasks.front_page_consensus import run_front_page_consensus


router = APIRouter()
db = Database()


# ------------------------------------
# General scan state
# ------------------------------------
scan_lock = threading.Lock()
scan_state = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "summary": None,
    "error": None,
}


def _run_scan_background():
    with scan_lock:
        scan_state["running"] = True
        scan_state["started_at"] = datetime.now().isoformat(timespec="seconds")
        scan_state["finished_at"] = None
        scan_state["summary"] = None
        scan_state["error"] = None

    try:
        summary = run_all_collectors()

        with scan_lock:
            scan_state["summary"] = summary
            scan_state["error"] = None

    except Exception as e:
        with scan_lock:
            scan_state["summary"] = None
            scan_state["error"] = str(e)

    finally:
        with scan_lock:
            scan_state["running"] = False
            scan_state["finished_at"] = datetime.now().isoformat(timespec="seconds")


# ------------------------------------
# Keyword scan state
# ------------------------------------
search_scan_lock = threading.Lock()
search_scan_state = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "query": None,
    "summary": None,
    "error": None,
}


class SearchRunRequest(BaseModel):
    query: str


def _run_search_scan_background(query: str):
    with search_scan_lock:
        search_scan_state["running"] = True
        search_scan_state["started_at"] = datetime.now().isoformat(timespec="seconds")
        search_scan_state["query"] = query
        search_scan_state["finished_at"] = None
        search_scan_state["summary"] = None
        search_scan_state["error"] = None

    try:
        summary = run_keyword_scan(query)
        with search_scan_lock:
            search_scan_state["summary"] = summary
            search_scan_state["error"] = None

    except Exception as e:
        with search_scan_lock:
            search_scan_state["summary"] = None
            search_scan_state["error"] = str(e)

    finally:
        with search_scan_lock:
            search_scan_state["running"] = False
            search_scan_state["finished_at"] = datetime.now().isoformat(timespec="seconds")


@router.get("/recent")
def get_recent(
    limit: int = Query(default=100, ge=1, le=200),
    include_filtered: bool = Query(default=False),
    tracked_only: bool = Query(default=False),
    live_only: bool = Query(default=False),
):
    try:
        data = db.get_recent(
            limit,
            include_filtered=include_filtered,
            tracked_only=tracked_only,
            live_only=live_only,
        )
        return {"status": "ok", "count": len(data), "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run")
def run_scan():
    with scan_lock:
        if scan_state["running"]:
            return {
                "status": "already_running",
                "message": "Scan is already running.",
                "scan": dict(scan_state),
            }

    thread = threading.Thread(target=_run_scan_background, daemon=True)
    thread.start()

    return {
        "status": "started",
        "message": "Phase 1A scan started.",
    }


@router.get("/scan-status")
def get_scan_status():
    with scan_lock:
        return {
            "status": "ok",
            "scan": dict(scan_state),
        }


@router.post("/search-run")
def run_search_scan(req: SearchRunRequest):
    query = (req.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    with search_scan_lock:
        if search_scan_state["running"]:
            return {
                "status": "already_running",
                "message": "Keyword scan already running.",
                "scan": dict(search_scan_state),
            }

    thread = threading.Thread(
        target=_run_search_scan_background,
        args=(query,),
        daemon=True,
    )
    thread.start()

    return {"status": "started", "message": f"Keyword scan started for: {query}"}


@router.get("/search-status")
def get_search_status():
    with search_scan_lock:
        return {"status": "ok", "scan": dict(search_scan_state)}


# ------------------------------------
# Stage 11: Front Page Consensus scan state
# ------------------------------------
consensus_scan_lock = threading.Lock()
consensus_scan_state = {
    "running":     False,
    "started_at":  None,
    "finished_at": None,
    "summary":     None,
    "error":       None,
}


def _run_consensus_background():
    with consensus_scan_lock:
        consensus_scan_state["running"]     = True
        consensus_scan_state["started_at"]  = datetime.now().isoformat(timespec="seconds")
        consensus_scan_state["finished_at"] = None
        consensus_scan_state["summary"]     = None
        consensus_scan_state["error"]       = None
    try:
        summary = run_front_page_consensus()
        with consensus_scan_lock:
            consensus_scan_state["summary"] = summary
            consensus_scan_state["error"]   = None
    except Exception as exc:
        with consensus_scan_lock:
            consensus_scan_state["summary"] = None
            consensus_scan_state["error"]   = str(exc)
    finally:
        with consensus_scan_lock:
            consensus_scan_state["running"]     = False
            consensus_scan_state["finished_at"] = datetime.now().isoformat(timespec="seconds")


@router.post("/consensus-scan")
def run_consensus_scan():
    with consensus_scan_lock:
        if consensus_scan_state["running"]:
            return {
                "status":  "already_running",
                "message": "Front page consensus scan is already running.",
                "scan":    dict(consensus_scan_state),
            }
    thread = threading.Thread(target=_run_consensus_background, daemon=True)
    thread.start()
    return {"status": "started", "message": "Front page consensus scan started."}


@router.get("/consensus-status")
def get_consensus_status():
    with consensus_scan_lock:
        return {"status": "ok", "scan": dict(consensus_scan_state)}


@router.get("/consensus")
def get_consensus():
    try:
        result = db.get_latest_consensus()
        return {"status": "ok", **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# Stage 13: Consensus Archive
@router.get("/consensus/archive")
def get_consensus_archive():
    try:
        snapshots = db.get_consensus_archive()
        return {"status": "ok", "snapshots": snapshots}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/consensus/snapshot/{scan_id}")
def get_consensus_snapshot(scan_id: str):
    try:
        result = db.get_consensus_by_scan_id(scan_id)
        return {"status": "ok", **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/{signal_id}/track")
def track_signal(signal_id: int):
    try:
        success = db.track_signal(signal_id)
        if not success:
            raise HTTPException(status_code=404, detail="Report not found.")
        return {"status": "ok", "tracked": True, "id": signal_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{signal_id}")
def delete_signal(signal_id: int):
    try:
        deleted = db.delete(signal_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Signal not found.")

        return {"status": "ok", "deleted": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
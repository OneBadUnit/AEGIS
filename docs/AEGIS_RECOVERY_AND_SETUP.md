# AEGIS — Recovery & Setup Reference
## SWAT Signal Desk / ARC NEXUS LLC
### System Recovery, First-Time Setup, and Restart Procedures

**Version:** 1.0  
**Date:** May 29, 2026  
**Purpose:** Step-by-step procedures for setting up AEGIS on a new machine or recovering a broken installation. Not a user guide — this is a technical recovery reference for developers and AI agents.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [First-Time Setup](#2-first-time-setup)
3. [Normal Startup](#3-normal-startup)
4. [Normal Shutdown](#4-normal-shutdown)
5. [Recovery Procedures](#5-recovery-procedures)
6. [Port Configuration](#6-port-configuration)
7. [Known Failure Modes](#7-known-failure-modes)

---

## 1. Prerequisites

The following must be installed before AEGIS will run:

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend build and dev server |
| npm | bundled with Node | Frontend dependency management |
| Ollama | latest | Local LLM inference |
| `qwen2.5:7b` model | via Ollama | AI analysis of news signals |

**Install Ollama and the model:**
```
ollama pull qwen2.5:7b
```

Ollama must be running (as a background service or via `ollama serve`) before any scan will produce AI-scored results. If Ollama is not running, scans will complete but all significance scores will default to `0.0`.

---

## 2. First-Time Setup

### 2.1 Clone or Copy the Project

Place the project at a path without spaces, e.g.:
```
D:\ARC NEXUS LLC\AEGIS\
```

The project root is the working directory for all runtime calls. `main.py` must be run from this directory.

### 2.2 Install Python Dependencies

```
cd "D:\ARC NEXUS LLC\AEGIS"
pip install fastapi uvicorn feedparser requests pydantic
```

> **Note:** `requirements.txt` is currently empty (TODO: populate). Install the above packages manually until it is populated.

### 2.3 Install Frontend Dependencies

```
cd "D:\ARC NEXUS LLC\AEGIS\frontend"
npm install
```

This installs React, Vite, and `@vitejs/plugin-react` from `package.json`.

### 2.4 Verify the Database

The SQLite database (`market_radar.db`) is created automatically on first backend startup. It lives in the project root. Do not commit it to git — it contains runtime data only.

If the database is missing or corrupted, delete `market_radar.db` and restart the backend. The schema will be recreated from scratch. All previously stored signals will be lost.

---

## 3. Normal Startup

### Option A — Launcher Script (Recommended)

Double-click `Launch Market Radar.vbs` from the project root.

This script:
1. Starts the backend (`python main.py`) in a new terminal window
2. Waits 4 seconds for the backend to bind port 8002
3. Starts the frontend (`npm run dev`) in a new terminal window
4. Waits 5 seconds for Vite to initialize
5. Opens `http://127.0.0.1:5175` in the default browser

### Option B — Manual Startup

**Terminal 1 — Backend:**
```
cd "D:\ARC NEXUS LLC\AEGIS"
python main.py
```

**Terminal 2 — Frontend:**
```
cd "D:\ARC NEXUS LLC\AEGIS\frontend"
npm run dev
```

Open browser to `http://127.0.0.1:5175`.

### Service Addresses

| Service | Address |
|---------|---------|
| Backend API | `http://127.0.0.1:8002` |
| Frontend | `http://127.0.0.1:5175` |
| Ollama | `http://127.0.0.1:11434` |
| Health check | `http://127.0.0.1:8002/health` |

---

## 4. Normal Shutdown

### Option A — Stop Script

Run `Stop Market Radar.bat` from the project root. This kills the processes bound to port 8002 (backend) and port 5175 (frontend) without touching other Python processes.

### Option B — Kill All Python

Run `Kill_Python.bat`. This force-kills **all** `python.exe` processes on the machine. Use only if `Stop Market Radar.bat` fails or ports remain bound.

### Option C — Manual

In each terminal, press `Ctrl+C`.

---

## 5. Recovery Procedures

### 5.1 Port Already in Use

If the backend fails to start with "address already in use" on port 8002:

```
netstat -ano | findstr :8002
taskkill /PID <PID> /F
```

Repeat for port 5175 if the frontend fails.

Alternatively, run `Stop Market Radar.bat` then restart.

### 5.2 Database Schema Out of Date

AEGIS uses `ensure_columns()` in `database.py` to apply schema migrations automatically at startup. If new columns are missing from an existing database, they will be added on the next backend start — no manual migration required.

If schema is severely corrupted: back up `market_radar.db`, delete it, and restart the backend. The schema recreates from scratch. Signal data will be lost.

### 5.3 Ollama Not Running

Scans will still run but all AI fields (`topic`, `summary`, `significance_score`, etc.) will be empty or `0.0`. No crash occurs — items are skipped gracefully.

To start Ollama:
```
ollama serve
```

Then restart the scan.

### 5.4 Frontend Shows Blank / Cannot Reach API

1. Confirm the backend is running: `http://127.0.0.1:8002/health` should return `{"status": "ok"}`
2. Confirm the frontend is on port 5175 — CORS is hardcoded to that port in `backend/app/app.py`
3. If ports differ, see Section 6

### 5.5 Scan Hangs or Never Completes

The scan has a hard cap of `MAX_RUNTIME_SECONDS = 240` (4 minutes). If it does not finish:
- Check Ollama is responding: each LLM call has a 60-second timeout
- Check internet connectivity for RSS fetching
- The scan state can be polled at `GET /api/radar/scan-status`

---

## 6. Port Configuration

All port values are hardcoded. Changing a port requires updating multiple files:

| Port | File(s) to Update |
|------|------------------|
| Backend `8002` | `main.py` (uvicorn bind), `backend/app/app.py` (CORS allow-origins), `frontend/src/lib/api.js` (BASE_URL) |
| Frontend `5175` | `frontend/vite.config.js` (server.port), `frontend/package.json` (dev script), `backend/app/app.py` (CORS allow-origins) |
| Ollama `11434` | `ai/analyzer.py` (OLLAMA_URL) |

The `.bak-port-change` backup files in the project root document a previous port migration. Review them if changing ports.

---

## 7. Known Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| All significance scores are `0.0` | Ollama not running | Start Ollama, re-run scan |
| `404` on all API calls from UI | Port mismatch between frontend and backend | Check BASE_URL in `api.js` vs backend port |
| Frontend loads but buttons do nothing | CORS misconfiguration | Verify frontend port matches CORS origins in `app.py` |
| Duplicate stories reappearing | `is_deleted` rows were hard-deleted from DB | Do not delete rows; restore from backup |
| Scan completes with 0 items | RSS feeds unreachable or all items deduplicated | Check network; check if `title_norm` is over-matching |
| `address already in use` on startup | Previous process still bound to port | Run `Stop Market Radar.bat` or kill by PID |
| Frontend npm install fails | Node/npm not installed or wrong version | Install Node.js 18+ |

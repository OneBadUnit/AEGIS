# AEGIS — User Install Guide
## SWAT Signal Desk / ARC NEXUS LLC
### End-User Installation Guide for Windows

**Version:** 1.0  
**Date:** May 29, 2026  
**Audience:** Analyst installing AEGIS on a Windows machine for the first time.  
**Scope:** Fresh install only. For recovery procedures, see `AEGIS_RECOVERY_AND_SETUP.md`.

---

## Table of Contents

1. [What You Are Installing](#1-what-you-are-installing)
2. [System Requirements](#2-system-requirements)
3. [Step 1 — Install Python](#3-step-1--install-python)
4. [Step 2 — Install Node.js](#4-step-2--install-nodejs)
5. [Step 3 — Install Ollama and Download the Model](#5-step-3--install-ollama-and-download-the-model)
6. [Step 4 — Install AEGIS](#6-step-4--install-aegis)
7. [Step 5 — Install Python Dependencies](#7-step-5--install-python-dependencies)
8. [Step 6 — Install Frontend Dependencies](#8-step-6--install-frontend-dependencies)
9. [Step 7 — Launch AEGIS](#9-step-7--launch-aegis)
10. [Verify the Installation](#10-verify-the-installation)
11. [Uninstall](#11-uninstall)

---

## 1. What You Are Installing

**AEGIS (Artificial Event & Global Intelligence System)** is a self-hosted, local-first news intelligence platform. It collects news from 50+ curated RSS feeds, analyzes each article using a locally-running AI model, scores it for constitutional significance, war escalation, censorship signals, and narrative manipulation, and surfaces the highest-significance items in a browser-based analyst dashboard.

Everything runs on your machine. No data is sent to cloud services. Internet is required only for fetching RSS feeds.

---

## 2. System Requirements

| Requirement | Minimum |
|-------------|---------|
| OS | Windows 10 or Windows 11 (64-bit) |
| RAM | 8 GB (16 GB recommended for comfortable Ollama performance) |
| Disk | 10 GB free (model download ~4 GB + application data) |
| Internet | Required for RSS feed fetching |
| Python | 3.11 or higher |
| Node.js | 18 or higher |
| Ollama | Latest release |

---

## 3. Step 1 — Install Python

1. Go to [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Download the latest Python 3.11+ installer for Windows
3. Run the installer
4. **Check the box "Add Python to PATH"** before clicking Install

Verify in a terminal:
```
python --version
```
Expected output: `Python 3.11.x` or higher.

---

## 4. Step 2 — Install Node.js

1. Go to [https://nodejs.org/](https://nodejs.org/)
2. Download the **LTS** release (18.x or higher)
3. Run the installer with default settings

Verify in a terminal:
```
node --version
npm --version
```

---

## 5. Step 3 — Install Ollama and Download the Model

Ollama runs the AI model locally. AEGIS requires it to score news articles.

1. Go to [https://ollama.com/download](https://ollama.com/download)
2. Download and run the Windows installer
3. After installation, open a terminal and pull the required model:

```
ollama pull qwen2.5:7b
```

This downloads approximately 4 GB. Wait for it to complete.

Verify Ollama is running:
```
ollama list
```
You should see `qwen2.5:7b` in the output.

> Ollama must be running whenever you use AEGIS. It starts automatically as a background service on Windows after installation.

---

## 6. Step 4 — Install AEGIS

Copy or extract the AEGIS project folder to your machine. The recommended location is:

```
D:\ARC NEXUS LLC\AEGIS\
```

Avoid paths with special characters. The project folder should contain `main.py` at the root.

---

## 7. Step 5 — Install Python Dependencies

Open a terminal, navigate to the AEGIS project root, and install the required packages:

```
cd "D:\ARC NEXUS LLC\AEGIS"
pip install fastapi uvicorn feedparser requests pydantic
```

> **Note:** `requirements.txt` is currently unpopulated (TODO). Install the packages listed above manually.

---

## 8. Step 6 — Install Frontend Dependencies

```
cd "D:\ARC NEXUS LLC\AEGIS\frontend"
npm install
```

This installs React and the Vite development server. It may take 1–2 minutes. A `node_modules` folder will be created inside `frontend/`.

---

## 9. Step 7 — Launch AEGIS

Double-click `Launch Market Radar.vbs` in the AEGIS project root.

This script will:
1. Open a terminal window and start the backend server
2. Wait 4 seconds
3. Open a terminal window and start the frontend
4. Wait 5 seconds
5. Open your default browser to `http://127.0.0.1:5175`

Both terminal windows must remain open while AEGIS is running.

---

## 10. Verify the Installation

After the browser opens:

1. The SWAT Signal Desk dashboard should load
2. Navigate to `http://127.0.0.1:8002/health` — it should return `{"status": "ok"}`
3. Click **Refresh Reports** in the dashboard to run your first scan
4. The scan takes up to 4 minutes (60 articles × ~4 seconds per AI call)
5. When complete, scored signals will appear in the Live Feed

If the dashboard loads but signals show `0.0` significance scores, Ollama is not running. See `AEGIS_RECOVERY_AND_SETUP.md`.

---

## 11. Uninstall

To remove AEGIS:

1. Run `Stop Market Radar.bat` to stop running processes
2. Delete the AEGIS project folder
3. Delete `market_radar.db` if you want to remove all stored data (it is created in the project root)
4. Optionally uninstall Ollama, Python, and Node.js through Windows Settings → Apps

Ollama model files are stored separately from the project (TODO: document Ollama data path on Windows).

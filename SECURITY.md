# 🔒 Security Policy

## Overview

JunctionGuard AI is committed to responsible data handling, user privacy, and application security. This document details how data is collected, stored, processed, and protected within the platform.

---

## Supported Versions

| Version | Supported |
|---|---|
| Latest (main branch) | ✅ Yes |
| Older branches | ❌ No — please upgrade |

---

## 🗄️ Data Handling

### 1. Junction & Risk Data

- Junction records (name, GPS coordinates, risk scores, contributing factors) are stored in a **local SQLite database** (`junctions.db`) on the server.
- Risk scores are computed algorithmically from public datasets and vision analytics — **no personally identifiable information (PII) is stored** in junction records.
- Historical accident data is sourced from the **Kaggle India Road Accidents dataset** (publicly available, anonymized, aggregate-level).

### 2. Citizen Hazard Reports

- Citizens may voluntarily submit hazard reports including:
  - Junction name / location
  - Issue type and description
  - (Optional) Reporter name
  - (Optional) Photo or video evidence
- **Reporter names are optional** and not linked to any account or authentication system.
- Uploaded media files (photos/videos) are stored in the `data/citizen_reports/` directory on the server filesystem and are **not publicly exposed via URL** by default.
- Report metadata is persisted in SQLite and optionally synced to **Supabase** (see Section 4).

### 3. Geolocation Data

- **Browser GPS** (HTML5 Geolocation API): Used only when the user explicitly clicks the "Locate Me" button and grants browser permission. Coordinates are used solely to snap to the nearest junction and are **not stored persistently**.
- **IP-based geolocation**: Used as a fallback. The user's IP address is sent to a third-party geolocation API (ipapi.co or equivalent) for approximate city-level location. The IP address itself is **not stored** by JunctionGuard AI.
- GPS coordinates captured from the browser are passed via **URL query parameters** (cleared immediately after use) and **Streamlit session state** (in-memory only, cleared on session end).

### 4. Cloud Database (Supabase)

- JunctionGuard AI optionally syncs data to **Supabase** (a hosted PostgreSQL service) for real-time multi-user access.
- Supabase connection credentials (`SUPABASE_URL`, `SUPABASE_KEY`) are stored in **environment variables only** (`.env` file, never committed to version control).
- The `.env` file is listed in `.gitignore` to prevent accidental credential exposure.
- Supabase enforces **Row Level Security (RLS)** on all tables.
- Data in transit to/from Supabase is encrypted via **TLS/HTTPS**.

### 5. Video & Vision Analytics

- Video files uploaded for CCTV analysis are stored temporarily in `data/output/` and `data/sample_videos/`.
- YOLOv8 detection is performed **server-side** — video frames are never sent to external APIs.
- Detection outputs (JSON/CSV) contain only aggregate vehicle counts and bounding box metadata — **no biometric or facial data** is collected or stored.
- The YOLOv8 model is configured to detect only vehicles and pedestrians (COCO classes 0, 2, 3, 5, 7) — **no facial recognition** is performed or possible with this configuration.

---

## 🔐 Security Controls

| Control | Implementation |
|---|---|
| **Secret management** | Environment variables via `.env` (git-ignored) |
| **Database access** | SQLite file-level access; Supabase RLS policies |
| **Data in transit** | TLS/HTTPS enforced for all Supabase and external API calls |
| **No authentication (current)** | Platform is a hackathon demo — add auth before production use |
| **Media file access** | Served via Streamlit session, not publicly indexed |
| **No PII in logs** | Application logs contain junction IDs and technical metadata only |
| **Input validation** | Pydantic models validate all incoming data shapes |
| **Dependency pinning** | `requirements.txt` pins minimum versions to avoid supply-chain issues |

---

## ⚠️ Known Limitations (Hackathon Scope)

> The following limitations exist because JunctionGuard AI is a hackathon prototype. These **must be addressed before any production deployment**:

1. **No user authentication or authorization** — the dashboard is publicly accessible.
2. **No rate limiting** on citizen report submissions.
3. **No input sanitization** beyond Pydantic schema validation.
4. **SQLite is not suitable for multi-user production** — migrate to PostgreSQL (Supabase) for production.
5. **Uploaded media files** are not virus-scanned before storage.
6. **CSRF protection** is not explicitly configured (Streamlit provides some built-in protection).

---

## 🐛 Reporting a Vulnerability

If you discover a security vulnerability in JunctionGuard AI, please follow responsible disclosure:

### Do NOT open a public GitHub Issue for security vulnerabilities.

Instead:

1. **Email the team privately** at: `security@junctionguard.ai` *(replace with your actual contact)*
2. Include:
   - A clear description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Any suggested mitigations (optional)
3. We will acknowledge your report within **48 hours** and provide a timeline for resolution.
4. Once patched, we will credit you in the release notes (unless you prefer anonymity).

---

## 🌐 Third-Party Services

| Service | Purpose | Data Shared |
|---|---|---|
| **Supabase** | Cloud database sync | Junction & report records |
| **Esri ArcGIS** | Map tiles (Satellite, Dark) | Tile requests only (no user data) |
| **OpenStreetMap Nominatim** | Reverse/forward geocoding | GPS coordinates (no PII) |
| **IP Geolocation API** | Location fallback | User IP address (transient) |
| **Render** | Cloud hosting | Application files & environment |
| **Ultralytics YOLO** | Model weights (local) | None — inference is local |

---

## 📋 Data Retention

| Data Type | Retention Policy |
|---|---|
| Junction risk scores | Indefinite (core platform data) |
| Citizen reports | Indefinite unless user requests deletion |
| Vision detection outputs | Session-scoped; cleared on restart |
| GPS coordinates (session) | In-memory only; cleared on session end |
| Application logs | Not persisted beyond Render's log retention |

---

## 📬 Contact

For security-related questions, please contact the project maintainers via GitHub or the OMNIKON Hackathon portal.

---

*Last updated: August 2026*

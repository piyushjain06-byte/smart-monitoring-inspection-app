Phase 9 — AI (Risk Engine + Anomaly Detection) — Completed Tasks
==================================================================

Summary
-------
This document lists what was implemented for Phase 9 (Part 22-25 of the
plan: Attendance data -> Anomaly detection -> Risk score -> Alert) and how
to run it locally.

New app: `apps/analytics`
--------------------------
- `RiskSnapshot` — one row per institute per risk-engine run: 0-100 score,
  LOW/MEDIUM/HIGH severity, the factor breakdown that produced it, the raw
  feature values, and the Isolation Forest anomaly flag/score. Gives you
  the "Historical trends" the plan's AI Risk Report (Part 33) wants.
- `AIAlert` — one row per triggered factor (Part 25): attendance mismatch,
  CCTV offline, failed inspection, unusual attendance, repeated issues.
  Has OPEN / ACKNOWLEDGED / RESOLVED status.
- `apps/analytics/services/features.py` — collects real signals per
  institute from data that already exists: staff attendance rate (last 30
  days, from `AttendanceRecord`), CCTV uptime ratio (from `Camera.status`,
  Phase 7), latest submitted inspection score, inspection frequency, and
  recent high-severity alert count. Any signal with no data yet returns
  `None` and is simply skipped by the risk engine — nothing is guessed.
- `apps/analytics/services/anomaly.py` — Scikit-learn `IsolationForest`
  (Part 23) run across all active institutes' feature vectors. Needs at
  least 5 institutes with data to say anything meaningful; below that it
  returns "not anomalous" for everyone rather than fabricate a result.
- `apps/analytics/services/risk_engine.py` — the rule-based score from
  Part 24, run literally as written:
    Attendance mismatch +25 · CCTV offline +20 · Failed inspection +30 ·
    Unusual attendance +15 (from the anomaly model) · Repeated issues +10
    -> capped at 100 -> 0-30 LOW / 31-60 MEDIUM / 61-100 HIGH
  `run_risk_engine()` saves a `RiskSnapshot` per institute and opens an
  `AIAlert` for each newly-triggered factor (won't duplicate an already-OPEN
  alert of the same type on re-run).

API endpoints
-------------
- `POST /api/analytics/run/` — runs the risk engine. Body: `{"institute": <id>}`
  optional, omit to score every active institute in the requester's scope.
  Returns per-institute score/severity/factors + counts. Official-only.
- `GET /api/analytics/risk/` — most recent `RiskSnapshot` per institute
  (scoped by state/district like `InstituteViewSet`).
- `GET /api/analytics/risk/institute/<id>/live/` — computes a fresh
  breakdown for one institute on demand, without needing a saved snapshot
  (so the institute detail page works even before anyone's clicked "Run AI
  Analysis").
- `GET /api/analytics/alerts/?institute=&status=&severity=` — list alerts.
  `POST /api/analytics/alerts/<id>/acknowledge/` and `.../resolve/`.

CLI
---
`python manage.py run_risk_analysis [--institute <id>] [--no-alerts]` — same
engine, for a cron job or manual run until Celery/Redis (commented out in
requirements.txt) is wired up.

Existing code updated
----------------------
- `apps/registry/views.py` — `DashboardSummaryView` now reports real
  `high_risk_institutes` / `open_ai_alerts` counts instead of the Phase 3
  placeholder comment ("no fabricated AI risk scores — Phase 9 not built
  yet"). Both read 0 until the risk engine has run at least once.
- `apps/registry/serializers.py` — `InstituteSerializer` exposes
  `latest_risk_severity` / `latest_risk_score` from the latest `RiskSnapshot`.
- `config/settings.py` / `config/urls.py` / `requirements.txt` — app
  registered, `scikit-learn` + `numpy` added.

Frontend
--------
- `src/components/AIAlertsPanel.jsx` (new) — lists open alerts, replaces
  the "AI-based risk scoring... aren't wired in yet" placeholder text that
  used to sit in `Dashboard.jsx`.
- `src/pages/Dashboard.jsx` — "Run AI Analysis" button next to "Surprise
  Inspection", High Risk / Open AI Alerts stat cards, AI alerts panel.
- `src/components/ProjectMap.jsx` — marker colour now uses AI risk severity
  (LOW/MEDIUM/HIGH) once a risk score exists for an institute, falling back
  to the Phase 3 inspection-status colour otherwise.
- `src/pages/InstituteDetail.jsx` — new "AI risk assessment" panel showing
  the score, severity, and each triggered factor with its point value.

Deliberately not built in this phase
-------------------------------------
- YOLO / OpenCV person-counting (Part 29) and the resulting "reported vs.
  detected" attendance comparison. This needs model weights and a live
  camera feed being actively read, which Phase 7's CCTV was intentionally
  kept minimal for ("This is where you should not waste your time"), and
  building a fake headcount would be exactly the kind of fabricated AI
  number this codebase has avoided since Phase 3. The risk engine uses real
  CCTV *uptime* (Phase 7, already built) as its CCTV signal instead of a
  fabricated headcount. Wiring in real YOLO counts later is additive: it's
  one more entry in `collect_features()` and `_factors_for()`, nothing here
  needs to change shape.
- Channels/WebSockets push for new alerts (still poll-on-load, same as
  everything else pre-Phase-4.5).
- Celery-scheduled recurring runs (still a manual button / management command).

How to run it
--------------
```bash
source venv/Scripts/activate
pip install -r requirements.txt        # adds scikit-learn + numpy
python manage.py makemigrations analytics   # should say "no changes detected"
python manage.py migrate
python manage.py runserver
```
Then, with some institutes/staff/attendance/cameras already in the DB
(via `/admin/` or earlier phases' data), either:
- click **Run AI Analysis** on the government dashboard, or
- `python manage.py run_risk_analysis`

Note on the bundled migration
------------------------------
`apps/analytics/migrations/0001_initial.py` was hand-written to match what
`makemigrations` would generate (no network access to run Django itself
where this was written). Run `makemigrations analytics` yourself after
pulling this in — expect "No changes detected", or at most a trivial
follow-up migration if an index name doesn't match exactly.

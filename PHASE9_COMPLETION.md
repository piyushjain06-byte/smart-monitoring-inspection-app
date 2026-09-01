Phase 9 — AI (Risk Engine + Anomaly Detection) — Completed Tasks
==================================================================

Summary
-------
This document lists what was implemented for Phase 9 (Part 22-25 of the
plan: Attendance data -> Anomaly detection -> Risk score -> Alert), plus
later additions to Phase 9 covering Part 33 (AI Risk Report + historical
trends), and how to run it all locally.

New app: `apps/analytics`
--------------------------
- `RiskSnapshot` — one row per institute per risk-engine run: 0-100 score,
  LOW/MEDIUM/HIGH severity, the factor breakdown that produced it, the raw
  feature values, and the Isolation Forest anomaly flag/score. Every run
  saves a **new** row rather than overwriting the last one, which is what
  makes the historical trend feature (below) possible.
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
- `GET /api/analytics/risk/institute/<id>/pdf/` — **(added post-Phase-3
  work)** downloadable AI Risk Report (Part 33). Renders
  `templates/analytics/risk_report.html` — institute info, score/severity
  badge, triggered factors table, and the underlying signal values — through
  WeasyPrint, mirroring the pattern already used for inspection report PDFs
  in `apps/inspections/views.py`. Falls back to returning plain HTML if
  WeasyPrint (GTK3 runtime) isn't available on the machine, instead of
  erroring — the frontend detects this via the response's `Content-Type`
  and opens it in a new tab rather than downloading a broken file.
- `GET /api/analytics/risk/institute/<id>/history/?limit=20` — **(added
  post-Phase-3 work)** Part 33's "historical trends". Returns up to `limit`
  (default 20, max 100) of the institute's most recent `RiskSnapshot` rows,
  oldest first, for charting score-over-time.
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
- `src/pages/InstituteDetail.jsx` — "AI risk assessment" panel showing the
  score, severity, and each triggered factor with its point value. **Now
  also includes** a "Download PDF" button (calls `.../pdf/` above) and a
  "Risk score trend" panel below it (calls `.../history/` and renders the
  new `RiskTrendChart` component).
- `src/components/RiskTrendChart.jsx` **(new)** — dependency-free inline-SVG
  line chart plotting `RiskSnapshot.score` over time, dots colour-coded by
  severity. No charting library was added (`recharts`/`chart.js` aren't in
  `frontend/package.json`) — this is hand-rolled SVG. Shown once an
  institute has 2+ saved snapshots; otherwise a "not enough history yet"
  message is shown instead.
- `templates/analytics/risk_report.html` **(new)** — the HTML template
  rendered into the PDF report above. Lives alongside
  `templates/inspections/report.html`, same WeasyPrint pattern.

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
- Celery-scheduled recurring runs (still a manual button / management
  command) — this also means the "historical trend" chart only gains new
  points when someone manually clicks "Run AI Analysis" or runs the CLI;
  there's no background job populating it automatically yet. Once
  Celery/Redis (Phase 4.7) is wired up, a periodic beat schedule calling
  `run_risk_engine()` daily/weekly would make the trend genuinely useful
  without manual intervention.

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

To see the PDF report and trend chart: go to the government dashboard →
**Institutes & Projects** → open any institute → scroll to **"AI risk
assessment"** (Download PDF button in its header) and **"Risk score
trend"** below it. The trend needs at least 2 saved `RiskSnapshot` rows for
that institute to render — click "Run AI Analysis" a couple of times to
generate them if you're just testing locally.

Note on WeasyPrint on Windows
-------------------------------
WeasyPrint needs the GTK3 runtime (system libraries pip can't install) to
actually produce a PDF on Windows. If it's missing, `.../pdf/` still works
but returns plain HTML instead of a PDF, and the frontend opens that HTML
in a new tab rather than downloading a broken `.pdf` file. Install the GTK3
runtime for Windows (search "GTK3 runtime Windows installer") and restart
your terminal/venv to get real PDF output.

Note on the bundled migration
------------------------------
`apps/analytics/migrations/0001_initial.py` was hand-written to match what
`makemigrations` would generate (no network access to run Django itself
where this was written). Run `makemigrations analytics` yourself after
pulling this in — expect "No changes detected", or at most a trivial
follow-up migration if an index name doesn't match exactly.
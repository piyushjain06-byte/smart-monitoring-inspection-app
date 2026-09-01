# Smart Real-Time Monitoring & Inspection Platform (SIH #26095)

**Current mode: plain Python + SQLite, no Docker.** This gets you running in
minutes on Windows without touching BIOS/virtualization settings. The
`docker-later/` folder has the Postgres+Redis+Celery setup for when you want
it — nothing here needs it yet.

## Where things stand

All of the "essential stack" from the plan is built and working:
Django + DRF + SQLite (Postgres-ready) + React + Leaflet, plus the
"add after core works" tier (OpenCV CCTV, Scikit-learn AI risk engine).

| Phase | What it covers | Status | Details |
|---|---|---|---|
| 0–1 | Django setup, accounts/registry models, geo helper | ✅ Done | this README |
| 2 | Inspection module (checklists, assignments, evidence, PDF export) | ✅ Done | `PHASE2_COMPLETION.md` |
| 3 | React government dashboard, JWT auth, auto-assignment engine | ✅ Done | `PHASE3_COMPLETION.md` |
| 7 | CCTV — OpenCV webcam streaming, camera status | ✅ Done | see `apps/cctv/` |
| — | Attendance module (check-in/out, daily records, summary) | ✅ Done | see `apps/attendance/` |
| 9 | AI risk engine + anomaly detection + AI Risk Report PDF + trend chart | ✅ Done | `PHASE9_COMPLETION.md` |

**Apps in this repo:** `apps/accounts` (custom User + RBAC), `apps/registry`
(Scheme/NGO/Institute/Project/Staff/Beneficiary), `apps/inspections`
(checklists, assignments, reports, evidence), `apps/cctv` (OpenCV webcam
streaming), `apps/attendance` (staff attendance), `apps/analytics`
(AI risk engine, anomaly detection, alerts, PDF report, trend chart),
`apps/core` (shared geo helper + permission classes).

## What's genuinely left (per the plan)

Everything below is intentionally **not** built yet — each needs
infrastructure this project has deliberately deferred (mainly Redis), or is
explicitly flagged in the plan as an "advanced/demo enhancement" you don't
need for the core to work:

- **Django Channels + Redis** — real-time WebSocket push to the dashboard
  (right now everything is poll-on-load). `config/asgi.py` and
  `config/settings.py` have commented-out blocks ready for this.
- **Celery + Redis + django-celery-beat** — scheduled/automatic risk-engine
  runs (right now "Run AI Analysis" is a manual button, and the new risk
  trend chart only gains a data point when someone clicks it). See
  `config/celery.py` (present but inactive).
- **PostGIS** — swap `Institute.latitude`/`longitude` plain floats for a
  real `PointField`. `apps/core/geo.py` was written so this is a drop-in
  swap later, not a rewrite.
- **YOLO person-counting on CCTV** (plan's Part 29) — deliberately skipped;
  see the note in `PHASE9_COMPLETION.md` on why a fabricated headcount
  wasn't built.
- **WebRTC / RTSP / MediaMTX** — real IP camera streaming (currently local
  webcam-only demo via OpenCV device index).
- **Cloud deployment.**

## Good next tasks that DON'T need Redis/Docker

If you're picking this up and want something concrete to build without
touching the infra above, these fit the current stack as-is:

1. **CSV/Excel export** of institutes, attendance records, and inspection
   history — useful for offline government reporting, just a
   `Content-Type: text/csv` response, no new dependencies.
2. **NGO Admin / Project Incharge portal** — `Role.NGO_ADMIN` and
   `Role.PROJECT_INCHARGE` exist on the `User` model
   (`apps/accounts/models.py`) but have no dedicated views/pages yet. Only
   `OFFICIAL_ROLES` (dashboard) and `FIELD_ROLES` (inspector portal) have a
   frontend today — see `apps/core/permissions.py` and
   `frontend/src/constants/roles.js`.
3. **Role-scoping audit** — double check the `is_official()` fallback (any
   `is_staff`/`is_superuser` account counts as official regardless of
   `role`) still behaves the way you want as more real users get created via
   `/admin/`.
4. **"Stale trend" nudge** — since there's no Celery yet, consider a small
   UI hint on the institute detail page suggesting "last analyzed N days
   ago, click to refresh" so officials know the risk score/trend might be
   out of date, without needing a scheduler.

## Prerequisites

- **Python 3.11 or 3.12** installed. Check with:
  ```bash
  python --version
  ```
  If that fails, download from https://www.python.org/downloads/ — during
  install, tick **"Add python.exe to PATH"**.

## First-time setup

From inside the `Smart-Monitoring-App` folder, in Git Bash:

```bash
# 1. Create a virtual environment (an isolated Python install just for this project)
python -m venv venv

# 2. Activate it (Git Bash on Windows)
source venv/Scripts/activate

# You should now see (venv) at the start of your terminal prompt.

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the environment file
cp .env.example .env

# 5. Create the database tables (SQLite — this just creates a db.sqlite3 file, no server)
python manage.py migrate

# 6. Create your first superuser (your SUPER_ADMIN / DoSJE HQ login)
python manage.py createsuperuser

# 7. Run the server
python manage.py runserver
```

## Verify it works

1. Open **http://127.0.0.1:8000/admin/** — log in with the superuser you just created.
2. Confirm you can see `Users`, `Schemes`, `NGOs`, `Institutes`, `Projects`,
   `Staff`, `Beneficiaries` all manageable there.
3. Create one `Scheme`, one `NGO`, then one `Institute` — for latitude/longitude,
   go to Google Maps, right-click any point, and the top of the menu shows the
   coordinates (e.g. `19.0760, 72.8777`) — copy those into the two fields.
4. While logged into `/admin/`, open a new tab to
   **http://127.0.0.1:8000/api/accounts/me/** — you should see your profile as JSON.
5. Open **http://127.0.0.1:8000/api/registry/institutes/** — you should see the
   Institute you created, with its lat/lng, as JSON. This confirms the whole
   chain (model → DB → serializer → API) works end-to-end.
6. **Important:** on the `Users` admin page, open your own superuser account
   and set **Role** (under "Platform Role & Scope") to
   `DoSJE HQ Super Admin`. Django's `is_staff`/`is_superuser` flags already
   let you into the official dashboard either way, but leaving `role` at its
   default (`Beneficiary`) means the sidebar/label will look wrong even
   though access works — worth fixing on every new account you create.

## Also run the frontend

```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173/** and log in with the same superuser (or any
staff account). `frontend/.env` points at `http://127.0.0.1:8000/api` —
change `VITE_API_BASE_URL` there if your backend runs elsewhere.

If `/institutes` shows "No institutes registered yet.", that's expected on a
fresh DB — go create a Scheme → NGO → Institute in `/admin/` first (step 3
above); nothing else on the dashboard has data to show until at least one
Institute exists.

## Every time you come back to work on this

```bash
source venv/Scripts/activate    # re-activate the virtual environment
python manage.py runserver
```

```bash
cd frontend
npm run dev
```

## Everyday commands

```bash
python manage.py makemigrations   # after changing any models.py
python manage.py migrate
python manage.py shell            # Django shell for quick testing
python manage.py createsuperuser  # if you need another admin login
python manage.py run_risk_analysis   # CLI equivalent of "Run AI Analysis" button
```

## Troubleshooting

- **AI Risk Report PDF opens as a broken/HTML file instead of a real PDF:**
  WeasyPrint needs the GTK3 runtime on Windows, which `pip install` alone
  doesn't provide. The backend detects this and falls back to plain HTML
  (frontend opens it in a new tab instead of erroring), so the feature still
  "works" either way — but for a real `.pdf`, install the GTK3 runtime for
  Windows and restart your terminal/venv. See `PHASE9_COMPLETION.md` for
  details.
- **Risk score trend chart says "not enough history yet":** it needs 2+
  saved `RiskSnapshot` rows for that institute — click "Run AI Analysis" on
  the dashboard a couple of times to generate them.
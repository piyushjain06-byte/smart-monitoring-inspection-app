Phase 3 — React Government Dashboard — Completed Tasks
=======================================================

Summary
-------
This document lists what was implemented for Phase 3 (React dashboard) and
how to run it locally alongside the existing Django backend.

Backend additions (needed to support the frontend)
---------------------------------------------------
- JWT auth via `djangorestframework-simplejwt`:
  - `POST /api/auth/login/` — returns `{access, refresh}`
  - `POST /api/auth/refresh/` — exchanges a refresh token for a new access token
  - Access tokens last 8 hours (field officers may be offline most of the day),
    refresh tokens last 7 days. Old Token/Session auth still works (used by
    `templates/inspections/submit.html`), so nothing already built broke.
- `GET /api/registry/dashboard-summary/` — institute/project/inspection counts
  for the dashboard's stat cards, scoped by the requesting user's
  state/district the same way `InstituteViewSet` already was.
- `Institute` serializer now includes `latest_inspection_status`
  (`PENDING` / `OVERDUE` / `SUBMITTED` / `NO_INSPECTION`) — used to colour
  map markers. This is **not** an AI risk score — that's Phase 9, not built
  yet — it's just "does this institute have an inspection on record".
- `GET /api/registry/projects/?institute=<id>` — filter projects by institute.
- `GET /api/inspections/assignments/?institute=<id>` — official-facing,
  read-only inspection history (separate from the inspector's own
  `reports/assignments/` endpoint).

Frontend (new `frontend/` folder — React + Vite + Tailwind)
-------------------------------------------------------------
- `src/context/AuthContext.jsx` — login/logout, holds the current user
- `src/api/client.js` — axios instance that attaches the JWT and
  auto-refreshes it once on a 401 before forcing re-login
- `src/pages/Login.jsx` — sign-in screen
- `src/pages/Dashboard.jsx` — stat cards + Leaflet map of all institutes
  (colour-coded by inspection status) + an inspection-status breakdown panel
- `src/pages/Institutes.jsx` — sortable table of all institutes
- `src/pages/InstituteDetail.jsx` — one institute's projects + inspection
  history
- `src/components/ProjectMap.jsx` — Leaflet + OpenStreetMap, no API key
  needed (matches the plan's "Leaflet + OpenStreetMap" choice)

Deliberately not built in this phase (matches the plan's phase order)
-----------------------------------------------------------------------
- Auto-assignment algorithm (assignments are still made from `/admin/`)
- AI/risk scoring, CCTV, WebRTC, attendance analytics, Channels/Celery
- The inspector-facing responsive UI still lives at `templates/inspections/submit.html`
  (server-rendered) — porting it into this same React app is a good next
  phase once you're ready, so officials and inspectors share one login flow.

How to run it
--------------
Terminal 1 (backend, from the project root):
```bash
source venv/Scripts/activate
python manage.py migrate
python manage.py runserver
```

Terminal 2 (frontend):
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173/ and log in with your Django superuser or any
staff account. `frontend/.env` points at `http://127.0.0.1:8000/api` — change
`VITE_API_BASE_URL` there if your backend runs elsewhere.

Phase 3 completion note (backend additions)
--------------------------------------------
The following were added after this doc was first written, for the
auto-assignment engine (see the "Next up" note below):

- `POST /api/inspections/assignments/auto-assign/` — body
  `{"institute": <id>, "template": <id, optional>, "due_in_days": <int, optional>}`.
  Picks the best available Inspection Officer / PMU Team member by
  distance-to-institute + current workload (plan section 13), officials only
  (`is_staff`/`is_superuser`).
- `POST /api/inspections/assignments/surprise/` — plan section 14. Randomly
  picks an active institute (weighted towards never-inspected/overdue ones)
  and runs the same auto-assign logic against it.
- `apps/inspections/services.py` — the scoring/selection logic, kept
  intentionally simple per the plan ("start simple... later you can make
  this an optimization/AI system").
- `User.base_latitude` / `User.base_longitude` — an officer's home-base
  location, set from `/admin/`, used to estimate travel distance. Required
  for an officer to be considered; officers without a location are still
  eligible but heavily deprioritised rather than excluded, so nobody goes
  unassigned just because their location wasn't entered yet.
- The React dashboard now has an "Assign Inspection" button on the institute
  detail page and a "Surprise Inspection" button on the main dashboard, both
  showing the full candidate scoring breakdown (mirroring the plan's demo:
  "Inspector 23 → 4 km ... Inspector 23 selected").

Notes
-----
- `CORS_ALLOW_ALL_ORIGINS = DEBUG` in `config/settings.py` already allows the
  Vite dev server's origin in local dev — no extra config needed.
- Map markers only render for institutes with `latitude`/`longitude` set (do
  this from `/admin/` as before).

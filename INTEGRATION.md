# Functional-gaps patch — integration guide

I don't have your actual repo mounted in this environment (only the plan
PDF was under `/mnt/project/`), so these are full, ready-to-drop-in files —
not a git patch. Copy each file over the matching path in your project
root, overwriting the existing one. No new pip/npm packages, no new
migrations (Institute.incharge and NGO.admin_user already existed).

## What's in here, mapped to the four gaps

### 1. NGO_ADMIN / PROJECT_INCHARGE portal
- `apps/core/permissions.py` — **replace**. Adds `is_ngo_admin`,
  `is_project_incharge`, `is_ngo_portal_user`, `IsNGOOrIncharge`.
  `is_official()` / `IsOfficial` are unchanged.
- `apps/registry/portal_views.py` — **new file**. Read-only, scoped
  viewsets: NGO_ADMIN sees every institute under NGOs where
  `NGO.admin_user == them`; PROJECT_INCHARGE sees only institutes where
  `Institute.incharge == them`.
- `apps/registry/urls.py` — **replace**. Adds `/api/registry/portal/...`
  routes alongside the existing official ones.
- `frontend/src/constants/roles.js` — **replace**. Adds
  `NGO_PORTAL_ROLES` / `isNGOPortalUser`.
- `frontend/src/pages/RoleRedirect.jsx` — **replace**. Now routes
  NGO/incharge accounts to `/ngo-portal` instead of falling through to
  `/inspector`.
- `frontend/src/components/ProtectedRoute.jsx` — **replace**. Adds
  `NGOPortalRoute`.
- `frontend/src/components/NGOPortalLayout.jsx` — **new file**. Sidebar
  shell, same visual style as `InspectorLayout.jsx`.
- `frontend/src/pages/ngo/NGODashboard.jsx` — **new file**. Landing page:
  stat cards + list of the user's own institutes.
- `frontend/src/pages/ngo/NGOInstituteDetail.jsx` — **new file**.
  Read-only institute view (projects, staff, AI risk badge — no "Assign
  Inspection" button, no CCTV panel; this portal reports, it doesn't act).
- `frontend/src/App.jsx` — **replace**. Wires the `/ngo-portal` route
  group.

**Before this works for real users:** go to `/admin/`, open an NGO row and
set its `admin_user`, or open an Institute row and set its `incharge`, to
whichever User account should see it. Nothing else needs configuring.

### 2. CSV export (institutes, attendance, inspections)
- `apps/registry/views.py` — **replace**. Adds
  `GET /api/registry/institutes/export-csv/` (`InstituteViewSet` action).
- `apps/attendance/views.py` — **replace**. Adds
  `GET /api/attendance/records/export-csv/`.
- `apps/inspections/views.py` — **replace**. Adds
  `GET /api/inspections/assignments/export-csv/?institute=<id optional>`.
- `frontend/src/api/client.js` — **replace**. Adds a shared `downloadBlob()`
  helper (auth'd GET → blob → triggers a browser download).
- `frontend/src/pages/Institutes.jsx` — **replace**. "Export CSV" button.
- `frontend/src/pages/Attendance.jsx` — **replace**. "Export CSV" button.
- `frontend/src/pages/InstituteDetail.jsx` — **replace**. "Export CSV" next
  to "Inspection history" (also carries the stale-trend nudge — see below).

Each export respects the same scoping/filters the on-screen table already
uses (district/state scoping for officials, `?institute=` filters, etc.) —
it's not a raw dump of the whole table.

### 3. Stale-trend nudge
- `apps/analytics/views.py` — **replace**. The
  `institute/<id>/live/` endpoint now also returns `last_snapshot_at`
  (ISO timestamp of the most recent *saved* `RiskSnapshot`, or `null` if
  none exists yet) and `last_snapshot_age_days`. This is separate from the
  freshly-computed score in the same response — the live score is always
  current, this field tells you how old the last time someone actually
  clicked "Run AI Analysis" was.
- `frontend/src/pages/InstituteDetail.jsx` — same file as above. Shows a
  banner under "AI risk assessment": "Last analyzed today" (fine),
  "Last analyzed 9 days ago — this score may be out of date..." (≥7 days,
  amber), or "This institute has never been analyzed..." (no snapshot yet).

### 4. Role-scoping audit
- `apps/accounts/management/__init__.py`,
  `apps/accounts/management/commands/__init__.py`,
  `apps/accounts/management/commands/audit_roles.py` — **new files**.
  Run:
  ```bash
  python manage.py audit_roles
  ```
  This **reports only** — it never changes an account. It flags:
  - an `NGO_ADMIN`/`PROJECT_INCHARGE` account that also has
    `is_staff`/`is_superuser` set (would get routed to the *official*
    dashboard instead of the new portal, per `is_official()`'s intentional
    fallback — see the updated docstring in `apps/core/permissions.py`);
  - an `INSPECTION_OFFICER`/`PMU_TEAM` account with the same issue (would
    bypass the "only see my own assignments" restriction);
  - an official-role account that *isn't* staff (informational only — it
    still works via the API, it just can't log into `/admin/`).

  Run it any time after creating accounts in `/admin/`, per the README's
  own "worth fixing on every new account you create" note.

## Quick sanity check after copying files in

```bash
python manage.py check                 # no migrations needed, but confirms nothing's broken
python manage.py audit_roles            # should run cleanly even with 0 conflicts
python manage.py runserver
```
```bash
cd frontend && npm run dev
```
Then:
1. In `/admin/`, set an NGO's `admin_user` (or an Institute's `incharge`)
   to a test account whose `role` is `NGO_ADMIN` (or `PROJECT_INCHARGE`).
2. Log in as that account → should land on `/ngo-portal` automatically.
3. As an official, open `/institutes` or `/attendance` → "Export CSV"
   should download a real CSV.
4. Open any institute detail page → the AI risk panel now shows the
   "Last analyzed..." line above the factor list.

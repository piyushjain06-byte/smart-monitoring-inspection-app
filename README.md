# Smart Real-Time Monitoring & Inspection Platform (SIH #26095)

**Current mode: plain Python + SQLite, no Docker.** This gets you running in
minutes on Windows without touching BIOS/virtualization settings. The
`docker-later/` folder has the Postgres+Redis+Celery setup for when you want
it — nothing here needs it yet.

## What's included so far (Phase 0–1 — nothing more)

- `config/` — Django settings, root URLs (Channels/Celery wiring present but
  commented out until later phases)
- `apps/accounts/` — custom `User` model with role-based access control
- `apps/registry/` — Scheme / NGO / Institute / Project / Staff / Beneficiary
  models (Institute has plain latitude/longitude fields for now), full CRUD API
- `apps/core/` — a `geo.py` helper with a Haversine distance check, ready for
  Phase: geofence validation on inspections

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

## Every time you come back to work on this

```bash
source venv/Scripts/activate    # re-activate the virtual environment
python manage.py runserver
```

## Everyday commands

```bash
python manage.py makemigrations   # after changing any models.py
python manage.py migrate
python manage.py shell            # Django shell for quick testing
python manage.py createsuperuser  # if you need another admin login
```

## What's next

Phase 2 (inspection module) is done — see `PHASE2_COMPLETION.md`.
Phase 3 (React government dashboard) is done — see `PHASE3_COMPLETION.md` for
how to run the `frontend/` app alongside this backend.

Next up: attendance module + the AI risk engine — one piece at a time, same as before.

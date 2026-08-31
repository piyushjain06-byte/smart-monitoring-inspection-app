# Smart Real-Time Monitoring & Inspection Platform (SIH #26095)

Phase 0–1 scaffold: Django + DRF + PostGIS + Channels + Celery, fully containerized,
runs entirely on localhost via Docker Compose.

## What's included so far

- `config/` — Django project settings, Celery app, ASGI (Channels) setup, root URLs
- `apps/accounts/` — custom `User` model with role-based access control (Part 4.1)
- `apps/registry/` — Scheme / NGO / Institute / Project / Staff / Beneficiary models with
  geo-location (PostGIS `PointField`) + full CRUD API + GeoJSON output for map views (Part 4.2)
- `apps/core/` — shared helpers: geofence distance check, central websocket routing hub
- `docker-compose.yml` — Postgres+PostGIS, Redis, Django (Daphne/ASGI), Celery worker, Celery beat
  (MinIO / MediaMTX / Jitsi services are stubbed in as comments for Phase 4)

## Prerequisites

- Docker Desktop installed and running (that's genuinely the only thing you need locally —
  Python/Postgres/Redis all run inside containers, nothing to install on your host machine).

## First-time setup

```bash
# 1. Copy the environment template
cp .env.example .env

# 2. Build and start everything
docker compose up --build
```

Leave that terminal running. In a **second terminal**, once the containers are up:

```bash
# 3. Run migrations (creates all the database tables)
docker compose exec web python manage.py migrate

# 4. Create your first superuser (this becomes your SUPER_ADMIN / DoSJE HQ login)
docker compose exec web python manage.py createsuperuser
```

## Verify it works

1. Open **http://localhost:8000/admin/** — log in with the superuser you just created.
   You should see `Users`, `Schemes`, `NGOs`, `Institutes`, `Projects`, `Staff`, `Beneficiaries`
   all manageable right there — this is your instant CRUD UI for seeding demo data.
2. In `/admin/`, open a **User** you created, confirm the "Platform Role & Scope" section shows
   role/phone/state/district fields.
3. In `/admin/`, create one `Scheme`, one `NGO`, then one `Institute` — click on the map widget
   on the Institute's `location` field to drop a pin (e.g. somewhere in your city) and save.
4. While still logged into `/admin/` in your browser, open a new tab to
   **http://localhost:8000/api/accounts/me/** — you should see your own profile as JSON.
5. Open **http://localhost:8000/api/registry/institutes/** — you should see the Institute you
   created, returned as GeoJSON with the coordinates you picked. This confirms the full chain
   (model → PostGIS → serializer → API) is working end-to-end.

## Everyday commands

```bash
docker compose up              # start everything (add --build after changing requirements.txt)
docker compose down            # stop everything
docker compose exec web python manage.py makemigrations   # after changing any models.py
docker compose exec web python manage.py migrate
docker compose exec web python manage.py shell             # Django shell inside the container
docker compose logs -f web     # tail the Django server logs
```

## What's next (see the full implementation plan doc for all phases)

- **Phase 2**: Inspection module — dynamic checklist templates, web-based photo/GPS evidence
  capture, geofence validation, PDF report generation.
- **Phase 3**: Random Inspection Assignment Engine — weighted lottery + Celery periodic task +
  audit log.
- **Phase 4**: CCTV (MediaMTX) + Random VC (Jitsi) — uncomment the relevant blocks in
  `docker-compose.yml` when you get here.
- **Phase 5**: AI microservice (FastAPI) for anomaly/attendance analytics.
- **Phase 6**: Additional features — grievances, public transparency portal, fund tracking, etc.

Ask for any of these next and we'll build them the same way: models → admin → serializers →
views → urls → a README section telling you exactly how to verify it.

# Phase 4.5 + 4.7 — Real-time push (Channels) + Scheduled AI runs (Celery)

This closes the two Redis-dependent items the README listed as
"Deliberately not built": real-time WebSocket push to the dashboard, and
scheduled/automatic risk-engine runs. Both now work locally — you just need
a Redis server reachable at `REDIS_URL`.

## What's new

### Files (new)
- `config/routing.py` — root websocket URL table
- `apps/core/channels_auth.py` — JWT auth for WebSocket connections (same
  `?token=` pattern the CCTV MJPEG stream already uses)
- `apps/analytics/consumers.py` — `AIAlertConsumer`, broadcasts new alerts
  + "analysis completed" events to every connected official
- `apps/analytics/routing.py` — websocket route for the above
- `apps/analytics/tasks.py` — `run_risk_analysis_task`, the Celery
  equivalent of the "Run AI Analysis" button / `manage.py run_risk_analysis`
- `.env.example` / `frontend/.env.example` — new Redis/WebSocket vars
- `frontend/src/hooks/useAlertsSocket.js` — connects to the alerts feed,
  auto-reconnects, exposes `connected`

### Files (replaced)
- `requirements.txt` — adds `channels`, `channels-redis`, `daphne`,
  `celery`, `redis`
- `config/__init__.py` — re-enables the Celery app import
- `config/settings.py` — adds `channels` to `INSTALLED_APPS`,
  `ASGI_APPLICATION`, `CHANNEL_LAYERS`, and the `CELERY_*` /
  `CELERY_BEAT_SCHEDULE` block (runs the risk engine every 6 hours)
- `config/asgi.py` — now a real `ProtocolTypeRouter` (HTTP + WebSocket)
  instead of a plain passthrough
- `apps/analytics/services/risk_engine.py` — broadcasts each newly-created
  `AIAlert` over the websocket group (best-effort; never breaks the save
  if Redis is down)
- `frontend/src/api/client.js` — adds `WS_BASE_URL`
- `frontend/src/pages/Dashboard.jsx` — subscribes to the live feed
  alongside the existing poll-on-load
- `frontend/src/components/AIAlertsPanel.jsx` — small "Live"/"Offline" dot

## How it fits with what already existed

Nothing about the existing REST API changed shape. `POST /api/analytics/run/`
still works exactly as before; it's just that now *both* that manual click
*and* the new scheduled Celery task funnel through the same
`run_risk_engine()` in `apps/analytics/services/risk_engine.py`, and either
path now also pushes over the websocket. If Redis isn't running, every one
of these degrades gracefully back to Phase 9's original behaviour
(poll-on-load, manual button) — nothing throws, nothing 500s.

## Setup

```bash
source venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env   # if you don't already have one — REDIS_URL defaults
                        # to redis://localhost:6379/0
```

### Get Redis running (pick one)
- Install Redis directly (WSL: `sudo apt install redis-server && redis-server`)
- Or just the `redis` service from the existing compose file, without
  touching Postgres/the rest of docker-later/:
  ```bash
  docker compose -f docker-later/docker-compose.yml up redis
  ```

### Run three processes instead of one (separate terminals)

```bash
# 1. ASGI server (replaces `manage.py runserver` — serves HTTP + WebSocket)
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# 2. Celery worker (executes the task when beat fires it, or if you trigger it manually)
celery -A config worker -l info

# 3. Celery beat (the scheduler — fires run_risk_analysis_task every 6 hours,
#    see CELERY_BEAT_SCHEDULE in config/settings.py)
celery -A config beat -l info
```

```bash
cd frontend
npm run dev
```

Open the dashboard, open a second browser tab as another official, and
click **Run AI Analysis** in one tab — the AI alerts panel in the *other*
tab updates immediately (no refresh), and both tabs' "AI alerts" header
shows a green **Live** dot once connected.

To see the scheduled path without waiting 6 hours, trigger it by hand:
```bash
python manage.py shell -c "from apps.analytics.tasks import run_risk_analysis_task; run_risk_analysis_task.delay()"
```

## Running without Redis

Everything still works — `manage.py runserver` + no Celery processes is
completely fine. You lose:
- the live "Live" dot (shows "Offline", socket just never connects)
- new alerts appearing without a page refresh
- the automatic every-6-hours risk-engine run

...but the manual "Run AI Analysis" button, CSV exports, CCTV, inspections,
everything else from Phases 0–9 is unaffected.

## What's still deliberately not built

- **PostGIS** — this is an infrastructure swap (a running Postgres+GDAL
  stack), not a code change. `apps/core/geo.py` and the commented
  `DATABASES` block in `config/settings.py` are already written so this is
  a drop-in swap once Postgres is available — see `docker-later/`.
- **YOLO person-counting on CCTV (Part 29)** and **WebRTC/RTSP/MediaMTX**
  real camera streaming — both explicitly out of scope per the plan's own
  "don't waste your time here" framing; see `PHASE9_COMPLETION.md`'s note
  on why a fabricated headcount wasn't built.
- **Cloud deployment.**

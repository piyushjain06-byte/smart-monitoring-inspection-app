Phase 2 — Inspection Module — Completed Tasks
============================================

Summary
-------
This document lists what was implemented for Phase 2 (Inspection Module) and how to exercise it locally.

Implemented
-----------
- Models: `InspectionTemplate`, `InspectionField`, `InspectionAssignment`, `InspectionReport`, `Evidence` (existing).
- API endpoints:
  - `GET /api/inspections/templates/` — list active templates.
  - `GET /api/inspections/reports/assignments/` — list pending assignments for logged-in officer.
  - `POST /api/inspections/reports/` — submit an inspection (multipart form with `evidence` files).
  - `GET /api/inspections/reports/{id}/pdf/` — export report as PDF (requires WeasyPrint/system libs).
- Admin: registration for templates, assignments, and evidence (use Django admin to create data).
- Frontend: `templates/inspections/submit.html` — mobile-friendly submission page using Geolocation API and `<input type="file" capture>`.
- PDF template: `templates/inspections/report.html` — includes embedded evidence images for photos.
- Tests: unit tests for geo helpers and an end-to-end submission test (`apps/core/tests/test_geo.py`, `apps/inspections/tests/test_submission.py`).

UX & Mobile
----------
- Submission page includes image previews and an upload progress bar for large files (`templates/inspections/submit.html`).

Production media
----------------
- Optional S3 support via `django-storages`/`boto3`. Configure `USE_S3=True` and the AWS env vars in `.env` to enable production storage. When disabled, the app uses local `MEDIA_ROOT` (default for development).

API Auth for mobile
-------------------
- Added token authentication support (`rest_framework.authtoken`). Mobile clients can obtain a token at `POST /api-token-auth/` with `username` and `password` and then send `Authorization: Token <token>` on subsequent API requests.

How to run tests
----------------
From the project root, activate the virtualenv and run:

```bash
python manage.py test
```

Notes
-----
- WeasyPrint is optional on Windows; if not installed the PDF endpoint returns HTML. Install system GTK/Cairo libs if you require PDFs.
- Media files are saved under `MEDIA_ROOT` (see `config/settings.py`).

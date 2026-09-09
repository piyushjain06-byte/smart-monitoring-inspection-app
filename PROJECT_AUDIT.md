# SIH 2026 Technical Audit

**Problem Statement:** 26095 - Smart Real-Time Monitoring & Inspection Mobile App  
**Audit scope:** Current workspace at audit time, including Django backend, React frontend, templates, migrations, tests, configuration, and project documentation.  
**Audit method:** Read-only source inspection and `python manage.py check`. No project source file was changed by this audit.  
**System check result:** Django reports `0` issues. This validates Django registration/model loading, but it does not execute every runtime path. Two stale relationship references described below can still fail when their paths run.

## Executive Summary

This is a strong functional prototype with meaningful implementation across the core monitoring loop:

- Custom users and role labels exist.
- Schemes, NGOs, institutes, projects, staff, and beneficiaries are modeled.
- NGO/institute application and Super Admin approval provisions registry records.
- Inspection templates, weighted assignment, surprise selection, checklists, geofencing, evidence upload, report rendering, CSV export, and PDF/HTML report output exist.
- CCTV has a real OpenCV local-webcam/MJPEG demonstration path and camera heartbeat status.
- Attendance records and summary analytics exist.
- Risk snapshots, rule-based risk factors, Isolation Forest anomaly detection, history, and optional Channels/Celery wiring exist.

It is not yet a complete production implementation of the SIH statement:

- CCTV is not a deployed IP-camera surveillance platform. The frontend also uses a public demo HLS stream as a fallback.
- Video conferencing is an unaudited Jitsi room trigger, not an integrated VC service with participant, consent, recording, attendance, or call audit data.
- Inspection has only `PENDING`, `SUBMITTED`, and `OVERDUE`; there is no accept/start/review/approve/reject/complete lifecycle.
- Evidence submission currently accepts only images even though the model advertises photo/video/document types.
- Attendance is manually marked by an authenticated caller and lacks strong ownership/role scoping.
- The flattened registry design removed `Institute.ngo` and `Project.institute`, but two runtime consumers still query those removed relations.
- “AI” is a real Isolation Forest model plus a deterministic rule engine; assignment is distance/workload scoring plus Python randomization, not machine learning.
- Live monitoring depends on Redis, Daphne/ASGI, Celery worker, and Celery beat processes being installed and running.

## 1. Complete Project Structure

The following is the source/project structure relevant to understanding and running the current implementation. Generated/dependency directories such as `venv/`, `.git/`, frontend `node_modules/`, `frontend/dist/`, Python caches, and `staticfiles/` are intentionally omitted from this structure.

```text
.
|-- manage.py
|-- db.sqlite3
|-- .env                         # local secret-bearing file; not source-safe
|-- .env.example
|-- .gitignore
|-- requirements.txt
|-- README.md
|-- ARCHITECTURE_FIX.md
|-- INTEGRATION.md
|-- INTEGRATION_V2.md
|-- ONBOARDING.md
|-- PHASE2_COMPLETION.md
|-- PHASE3_COMPLETION.md
|-- PHASE4_COMPLETION.md
|-- PHASE9_COMPLETION.md
|-- final implementaion and techstack plan.pdf
|-- project.tar.gz              # historical/generated archive
|-- apps/
|   |-- __init__.py
|   |-- accounts/
|   |   |-- admin.py, apps.py, models.py, serializers.py, urls.py, views.py
|   |   |-- management/commands/audit_roles.py
|   |   |-- migrations/0001_initial.py
|   |   |-- migrations/0002_user_base_latitude_user_base_longitude.py
|   |-- analytics/
|   |   |-- admin.py, apps.py, consumers.py, models.py, risk_engine.py
|   |   |-- routing.py, serializers.py, tasks.py, urls.py, views.py
|   |   |-- management/commands/audit_cctv_status.py
|   |   |-- management/commands/run_risk_analysis.py
|   |   |-- services/features.py, anomaly.py, risk_engine.py
|   |   |-- migrations/0001_initial.py, 0002_rename_analytics_r_institu_1c9d0a_idx_analytics_r_institu_90ce62_idx.py, 0003_alter_aialert_alert_type.py
|   |-- attendance/
|   |   |-- apps.py, models.py, serializers.py, tests.py, urls.py, views.py
|   |   |-- migrations/0001_initial.py, 0002_alter_attendancerecord_unique_together.py
|   |-- cctv/
|   |   |-- admin.py, apps.py, models.py, serializers.py, urls.py, views.py
|   |   |-- tests/test_camera_status.py
|   |   |-- migrations/0001_initial.py, 0002_camera_is_maintenance_and_more.py
|   |-- core/
|   |   |-- apps.py, channels_auth.py, geo.py, permissions.py
|   |   |-- tests/test_geo.py
|   |-- inspections/
|   |   |-- admin.py, apps.py, models.py, serializers.py, services.py, tasks.py, urls.py, views.py
|   |   |-- management/commands/auto_assign_inspections.py
|   |   |-- migrations/0001_initial.py, 0002_historicalinspectionassignment_scheduled_at_and_more.py, 0003_historicalinspectionreport_distance_from_site_meters_and_more.py, 0004_inspectiontemplate_institute.py
|   |   |-- tests/test_auto_assignment.py, tests/test_submission.py
|   |-- onboarding/
|   |   |-- admin.py, apps.py, models.py, serializers.py, services.py, urls.py, views.py
|   |   |-- migrations/0001_initial.py
|   |-- registry/
|       |-- admin.py, apps.py, models.py, portal_views.py, serializers.py, urls.py, views.py
|       |-- migrations/0001_initial.py, 0002_flatten_scheme_hierarchy.py
|-- config/
|   |-- __init__.py, asgi.py, celery.py, routing.py, settings.py, urls.py, wsgi.py
|-- templates/
|   |-- analytics/risk_report.html
|   |-- inspections/report.html, inspections/submit.html
|-- static/.gitkeep
|-- media/evidence/2026/09/03/*.jpg
|-- docker-later/
|   |-- docker-compose.yml, Dockerfile, README.md
|-- frontend/
    |-- index.html, package.json, package-lock.json
    |-- postcss.config.js, tailwind.config.js, vite.config.js
    |-- .env.example, .gitignore, .oxlintrc.json, README.md
    |-- public/favicon.svg, public/icons.svg
    |-- src/App.jsx, src/index.css, src/main.jsx
    |-- src/api/client.js
    |-- src/assets/hero.png, src/assets/vite.svg
    |-- src/components/AIAlertsPanel.jsx, CctvPanel.jsx, InspectorLayout.jsx, Layout.jsx, NGOPortalLayout.jsx, ProjectMap.jsx, ProtectedRoute.jsx, RiskTrendChart.jsx, StatCard.jsx
    |-- src/constants/roles.js
    |-- src/context/AuthContext.jsx
    |-- src/hooks/useAlertsSocket.js
    |-- src/pages/Attendance.jsx, Dashboard.jsx, InspectorAssignments.jsx, InstituteDetail.jsx, Institutes.jsx, Login.jsx, Register.jsx, ReportDetail.jsx, RoleRedirect.jsx, SubmitInspection.jsx
    |-- src/pages/admin/InspectionTemplates.jsx, Manage.jsx, SchemeApplications.jsx, TemplateDetail.jsx
    |-- src/pages/ngo/ApplyForScheme.jsx, MyApplications.jsx, NGODashboard.jsx, NGOInstituteDetail.jsx
```

## 2. Django Apps

### `apps.accounts`

Defines the custom `User` model and the `Role` enumeration. Supplies `GET /api/accounts/me/`, serializers, admin integration, and the `audit_roles` management command.

### `apps.registry`

The operational registry: `Scheme`, `NGO`, `Institute`, `Project`, `Staff`, and `Beneficiary`. It provides official CRUD, state/district scoping, dashboard summary, CSV export, and read-only NGO/Project Incharge portal views.

### `apps.onboarding`

Implements public applicant registration, scheme catalogue browsing, scheme applications, Super Admin review, and transactional provisioning of registry records after approval.

### `apps.inspections`

Owns checklist templates/fields, assignments, surprise selection, assignment scoring, geofenced report submission, evidence files, report serialization, PDF/HTML output, CSV export, and Celery/management-command assignment triggers.

### `apps.cctv`

Owns camera configuration, computed online/offline status, manual ping, OpenCV capture, JWT query-token authentication, and server-side MJPEG streaming.

### `apps.attendance`

Owns daily staff attendance records, check-in/check-out actions, summary counts, and CSV export.

### `apps.analytics`

Collects operational features, runs the rule-based risk engine and scikit-learn `IsolationForest`, stores `RiskSnapshot` and `AIAlert`, exposes live/history/report endpoints, and optionally broadcasts updates through Channels.

### `apps.core`

Shared role permissions, Haversine geospatial calculations, JWT WebSocket middleware, and geo tests.

## 3. Model Inventory and Relationships

### Accounts

#### `accounts.User`

Extends Django `AbstractUser`.

| Field | Type / behavior |
|---|---|
| `id` | inherited primary key |
| `username`, `password`, `first_name`, `last_name`, `email` | inherited Django auth fields |
| `role` | `CharField`, one `Role` choice, defaults to `BENEFICIARY` |
| `phone_number` | optional string, max 15 |
| `preferred_language` | string, defaults to `en` |
| `state`, `district` | optional text scope used for authority filtering |
| `base_latitude`, `base_longitude` | optional floats used by assignment distance scoring |
| `is_staff`, `is_superuser`, `is_active` | inherited Django authorization/account flags |

Relationships are created by other models: `NGO.admin_user`, `Institute.incharge`, `Staff.linked_user`, `Beneficiary.linked_user`, `SchemeApplication.applicant`, `SchemeApplication.reviewed_by`, and `InspectionAssignment.officer`.

#### `Role`

Choices are `SUPER_ADMIN`, `STATE_AUTHORITY`, `DISTRICT_AUTHORITY`, `PMU_TEAM`, `INSPECTION_OFFICER`, `NGO_ADMIN`, `PROJECT_INCHARGE`, and `BENEFICIARY`.

### Registry

#### `Scheme`

Fields: `id`, `name`, `description`, `created_at`, and `history` (`HistoricalRecords`). One Scheme has reverse one-to-many collections of `NGO`, `Institute`, `Project`, and `SchemeApplication`.

#### `NGO`

Fields: required FK `scheme` (cascade), `name`, unique `registration_number`, optional `contact_person`, `contact_phone`, `contact_email`, optional FK `admin_user` to `User` (set null), `created_at`, and `history`. The current architecture intentionally has no NGO-to-Institute FK.

#### `Institute`

Fields: required FK `scheme` (cascade), `name`, optional `address`, required `state` and `district`, optional float `latitude` and `longitude`, optional FK `incharge` to `User` (set null), `is_active`, `created_at`, and `history`. Reverse relationships are `staff_members`, `cameras`, `inspection_templates`, `inspection_assignments`, `attendance_records`, `risk_snapshots`, and `ai_alerts`.

#### `Project`

Fields: required FK `scheme` (cascade), `name`, optional `start_date`, `end_date`, optional decimal `sanctioned_budget`, `is_active`, `created_at`, and `history`. The current architecture intentionally has no Project-to-Institute FK.

#### `Staff`

Fields: required FK `institute` (cascade), `full_name`, optional `designation`, optional `phone_number`, and optional OneToOne `linked_user` to `User` (set null). It represents institute staff.

#### `Beneficiary`

Fields: required FK `project` (cascade), `full_name`, optional `phone_number`, optional OneToOne `linked_user` to `User` (set null), and auto-created `enrolled_on`. It represents a project participant.

### Onboarding

#### `SchemeApplication`

Fields: FK `applicant` to `User`; `applicant_type` (`NGO` or `INSTITUTE`); FK `scheme`; organization fields `organization_name`, `registration_number`, `contact_person`, `contact_phone`, `contact_email`, `address`, `state`, `district`, `latitude`, `longitude`; proposal fields `project_name`, `project_plan`, `proposed_fund_amount`, `proposed_start_date`, `proposed_end_date`; review fields `status` (`PENDING`, `APPROVED`, `REJECTED`), `review_notes`, `approved_fund_amount`, FK `reviewed_by`, `reviewed_at`; provisioning FKs `created_ngo`, `created_institute`, `created_project`; and `created_at`. Approval creates one NGO or Institute plus one Project in `apps.onboarding.services.approve_application()` inside one transaction.

### Inspections

#### `InspectionTemplate`

Optional FK `institute`; `name`, `description`, `is_active`, `created_at`. It represents a checklist definition, with nullable institute allowing a shared/general checklist.

#### `InspectionField`

FK `template`; `label`; `field_type` (`TEXT`, `TEXTAREA`, `YES_NO`, `RATING`, `NUMBER`); `is_required`; and `order`. It represents one checklist question.

#### `InspectionAssignment`

Fields: FK `officer` to `User`; FK `institute`; protected FK `template`; `assigned_at`; optional `scheduled_at`; `due_date`; `status` (`PENDING`, `SUBMITTED`, `OVERDUE`); `random_seed`; JSON `weight_snapshot`; and historical audit. It represents one inspection duty.

#### `InspectionReport`

OneToOne with `InspectionAssignment`. Fields: `submitted_at`, `submitted_latitude`, `submitted_longitude`, `distance_from_site_meters`, `is_geofence_verified`, `location_verified`, JSON `answers`, `overall_score`, `notes`, and historical audit. It is the submitted checklist result, but has no reviewer/status field.

#### `Evidence`

FK `report`; `media_type` (`PHOTO`, `VIDEO`, `DOCUMENT`); `file` uploaded under `evidence/%Y/%m/%d/`; `captured_at`; `latitude`; `longitude`. The current API validator accepts only images, so the model choices exceed the implemented capture path.

### CCTV

#### `Camera`

Fields: FK `institute`; `name`; `camera_index` for local OpenCV device; optional `stream_url`; `is_active`; `is_maintenance`; `last_online`; `created_at`; and historical audit. Computed `status` is `DISABLED`, `MAINTENANCE`, `ONLINE`, or `OFFLINE` from flags and `last_online`; it is not persisted.

### Attendance

#### `AttendanceRecord`

Fields: FK `staff`; FK `institute`; `date`; `check_in`; `check_out`; `status` (`PRESENT`, `ABSENT`, `LATE`, `HALF_DAY`); `notes`; `created_at`; and `updated_at`. A unique constraint enforces one record per `(staff, institute, date)`. The duplicate `institute` FK is a denormalized reporting dimension, but the API does not verify it matches `staff.institute`.

### Analytics

#### `RiskSnapshot`

Fields: FK `institute`; numeric `score` 0-100; `severity` (`LOW`, `MEDIUM`, `HIGH`); JSON `factors`; JSON `features`; `is_anomaly`; optional `anomaly_score`; `computed_at`; and an index on `(institute, -computed_at)`. It is historical output of a risk-engine run.

#### `AIAlert`

Fields: FK `institute`; optional FK `snapshot`; `alert_type` (`ATTENDANCE_MISMATCH`, `CCTV_OFFLINE`, `CCTV_OFFLINE_OVER_48H`, `FAILED_INSPECTION`, `UNUSUAL_ATTENDANCE`, `REPEATED_ISSUES`); `description`; `risk_score`; `severity`; `status` (`OPEN`, `ACKNOWLEDGED`, `RESOLVED`); `created_at`; and `resolved_at`. It represents an operational alert, not a trained-model explanation object.

## 4. End-to-End SIH Workflow

```text
Government / DoSJE
        |
      Scheme
        |
 NGO / Institute / Project
        |
 Staff / Beneficiaries
        |
    Inspection
        |
 Inspector / PMU
        |
     Evidence
        |
      Report
        |
 AI analytics / alerts
```

### Current implementation

1. A government official creates a `Scheme` through `/manage`, Django admin, or `POST /api/registry/schemes/`.
2. An NGO/Institute applicant registers through `POST /api/onboarding/register/`; registration creates a bare user with `NGO_ADMIN` or `PROJECT_INCHARGE`.
3. The applicant selects a scheme from `/api/onboarding/schemes-catalogue/` and submits `SchemeApplication` with organization and project proposal data.
4. A DoSJE HQ Super Admin approves or rejects through `POST /api/onboarding/applications/<id>/approve/` or `/reject/`. Approval transactionally creates an `NGO` or `Institute`, creates a `Project`, and links the applicant account to the created entity.
5. Officials create `Staff` and `Beneficiary` records, cameras, and inspection templates. Staff belongs to an Institute; Beneficiary belongs to a Project. Because `Project.institute` was removed, the system cannot reliably derive which institute a beneficiary/project belongs to.
6. An official calls `POST /api/inspections/assignments/auto-assign/`, clicks the frontend “Surprise Inspection” action, runs a daily Celery task, or invokes `auto_assign_inspections`. The service selects an institute/officer/template and creates `InspectionAssignment`.
7. The assigned field officer sees pending assignments and submits a checklist from `frontend/src/pages/SubmitInspection.jsx`. Browser geolocation is required; backend Haversine distance must be at most 200 meters.
8. The report is created with answers and location. Image files in `request.FILES.getlist("evidence")` become `Evidence` rows with the report coordinates. Assignment status becomes `SUBMITTED`.
9. Officials retrieve the report, view answers/evidence, export a PDF/HTML report, and see it in institute detail. There is no explicit review decision or completion transition.
10. `collect_features()` gathers attendance, camera, latest inspection, inspection-frequency, and prior-alert signals. `run_risk_engine()` stores `RiskSnapshot` rows and creates `AIAlert` rows for newly triggered factors. Channels can push alerts and Celery beat can run scheduled analysis when infrastructure is running.

### Important workflow break

The code intentionally flattens the hierarchy to `Scheme -> {NGO, Institute, Project}`. This makes `Project` a scheme-level activity, but the SIH workflow expects projects to operate at identifiable institutes/sites. The current model has no direct path from `Project` to `Institute`, and `features.py` still calls `Beneficiary.objects.filter(project__institute=institute)`. That call is inconsistent with the current schema and will raise a Django field lookup error when risk analysis reaches it.

## 5. Authentication and Authorization

Authentication is JWT-first via Simple JWT (`/api/auth/login/`, `/api/auth/refresh/`), with Django session and legacy DRF token authentication also enabled. `/admin/` uses Django admin/session auth. WebSockets use JWT in `?token=`.

| Role | Current capabilities |
|---|---|
| Admin / `is_staff` / `is_superuser` | `is_official()` treats either flag as a government official. Staff/superuser can access official registry, inspections, CCTV, analytics, dashboard, and Django admin according to admin permissions. `is_superuser` can approve/reject onboarding. This fallback can accidentally elevate an NGO or field account if its staff flag is set. |
| `SUPER_ADMIN` | Official dashboard/API CRUD; only role-based account (besides superuser) allowed to approve/reject applications. |
| `STATE_AUTHORITY` | Official dashboard/API, filtered by `User.state` in institute/risk/dashboard paths. Can read/write official ModelViewSets; state scoping is not consistently applied to every related CRUD object. Cannot approve/reject onboarding. |
| `DISTRICT_AUTHORITY` | Official dashboard/API, filtered by `User.district` in institute/risk/dashboard paths. Can read/write official ModelViewSets; related object scoping is not consistently applied. Cannot approve/reject onboarding. |
| `PMU_TEAM` | Field-officer assignment visibility is limited to own assignments. Can submit own assigned report. Frontend routes to inspector portal. Cannot use official CCTV/analytics APIs. |
| `INSPECTION_OFFICER` | Same field-officer behavior as PMU: own assignments and own reports, geofenced submission. |
| `NGO_ADMIN` | Read-only portal institute/project/staff/beneficiary data scoped by schemes of administered NGOs; can register/apply/track applications. No inspection submission or attendance API role restriction is applied. |
| `PROJECT_INCHARGE` | Read-only portal data scoped to institutes where `Institute.incharge` is the user; can apply/track applications. No direct inspection/attendance workflow is provided. |
| `BENEFICIARY` | Role exists and is the default, but no dedicated frontend/API workflow is implemented. A generic authenticated user may access endpoints where only `IsAuthenticated` is used. |
| Linked staff/beneficiary user | OneToOne fields exist, but no complete self-service staff/beneficiary or attendance identity workflow exists. |

Authorization gaps:

- `AttendanceRecordViewSet` uses only `IsAuthenticated`; any authenticated user can list/filter/create/check-in/check-out records by arbitrary `staff_id` and `institute_id`.
- `InspectionTemplateViewSet` allows any authenticated user to list/retrieve active templates, with no object-level institute visibility.
- `SchemeCatalogueView` allows any authenticated user to browse all schemes.
- Official ModelViewSet writes are role-gated but state/district object-level restrictions are not uniform.
- `AIAlertConsumer._can_join_institute()` and `_authorized_institute_ids()` still contain `institute.ngo` lookups even though `Institute.ngo` was removed.

## 6. Scheme Allocation/Application Workflow

Both workflows exist:

1. **Government creates/assigns a scheme:** officials create `Scheme` through registry CRUD/admin and may directly create/link NGO, Institute, and Project rows.
2. **Applicant applies/selects a scheme:** public registration and `/ngo-portal/apply` select an existing scheme and create `SchemeApplication`.
3. **Government approval provisions allocation:** `approve_application()` creates the operational NGO/Institute and Project records and stores approved funding.

This is logically appropriate for SIH because DoSJE schemes should be government-defined while implementing organizations propose/apply and government reviews. The model should be tightened so an approved applicant can reuse its existing organization and associate multiple projects without creating a new NGO/Institute on every application. A direct Project-to-Institute or explicit project-site assignment is also needed for monitoring correctness.

## 7. Inspection Workflow State

| Stage | Current behavior | Code evidence / gap |
|---|---|---|
| Created | Official creates assignment through admin or auto-assign endpoint/service. | `InspectionAssignmentViewSet.auto_assign_action()`, `apps/inspections/services.py::auto_assign()` |
| Assigned | Officer selected using distance/workload scoring or random eligible candidate in batch mode. | `select_inspector_for_institute()`, `run_auto_assignment()` |
| Accepted | Not implemented. | `InspectionAssignment.Status` has no `ACCEPTED`. |
| Conducted | Officer fills a dynamic checklist in React. | `InspectorAssignments.jsx`, `SubmitInspection.jsx` |
| Evidenced | Browser selects image files, watermarks time/GPS/assignment, uploads multipart files. | `SubmitInspection.jsx::watermarkImage()`, `InspectionReportViewSet.create()` |
| Submitted | Backend validates coordinates, creates report/evidence, computes score, sets assignment `SUBMITTED`. | `InspectionReportCreateSerializer.validate()`, `InspectionReportViewSet.create()` |
| Reviewed | Officials can view/export; no review decision, reviewer, or approval endpoint. | `ReportDetail.jsx`, `templates/inspections/report.html` |
| Completed | No explicit completed state; `SUBMITTED` is effectively terminal. | `InspectionAssignment.Status` |

## 8. Random Inspection Assignment

This is actually implemented, but is a hybrid heuristic/random system rather than AI:

- `apps/inspections/services.py::select_surprise_institute()` uses `random.choices()` with weights: never inspected 5, overdue 4, submitted 2, pending 1.
- `apps/inspections/views.py::InspectionAssignmentViewSet.surprise_action()` exposes `POST /api/inspections/assignments/surprise/` and calls `auto_assign()`.
- `run_auto_assignment()` filters high-risk/overdue institutes without pending work, applies radius, same-day workload, and 180-day same-scheme anti-collusion checks, then uses `random.choice(candidates)`.
- `auto_assign()` uses the lowest distance + workload score from `score_officers_for_institute()` for direct assignment.
- `config/settings.py` schedules `apps.inspections.tasks.auto_assign_inspections_task` daily at 06:00 through Celery beat.
- `frontend/src/pages/Dashboard.jsx` calls the surprise endpoint; `frontend/src/pages/admin/Manage.jsx` runs batch assignment.

`random_seed` and `weight_snapshot` preserve assignment evidence, but the UUID seed is not used to seed/replay the random generator, so assignments are not reproducible from stored data.

## 9. CCTV Integration

### Implemented

- `Camera` stores site, local camera index, optional stream URL, active/maintenance flags, and last heartbeat.
- `Camera.status` computes online/offline from `last_online` and a 30-second threshold.
- `POST /api/cctv/cameras/<id>/ping/` opens a source with OpenCV, reads a frame, and updates `last_online`.
- `GET /api/cctv/cameras/<id>/stream/?token=<JWT>` opens the server webcam or configured source and emits an MJPEG stream.
- `CctvPanel.jsx` lists cameras, refreshes status every 10 seconds, creates/edits/deletes cameras, and shows a video panel.
- `features.py` uses camera online ratio and offline duration in risk scoring.

### Not a complete SIH CCTV platform

- The default real stream path is a local server webcam, not an installed CCTV/IP-camera fleet.
- No RTSP gateway, MediaMTX, WebRTC/HLS production pipeline, camera credential vault, recording, retention, playback, stream authorization policy, or multi-camera event history exists.
- `CctvPanel.jsx` uses `DEMO_STREAM_URL = https://test-streams.mux.dev/...` whenever `camera.stream_url` is empty. The visible frontend feed can therefore be a public demo stream rather than the backend camera.
- The frontend does not consume the backend MJPEG `stream_path`; it renders HLS/demo playback instead.
- OpenCV capture is synchronous inside request/stream handling and is not production-scalable.

Conclusion: functional demo/prototype integration, not production live CCTV surveillance.

## 10. Video Conferencing

A partial VC feature exists:

- `InstituteViewSet.initiate_vc()` generates a unique room name and broadcasts `SURPRISE_VC_ALERT` through Channels to `institute_<id>`.
- `InstituteDetail.jsx` and `NGODashboard.jsx` embed `https://meet.jit.si/<room>` in an iframe.
- `apps/analytics/consumers.py` has `surprise_vc_alert()` to deliver the event.

Missing: VC session/participant tables; invitation/acknowledgment; staff/beneficiary selection; consent; attendance; start/end/duration; recording; transcript; evidence; audit trail; participant-online guarantees; and controlled Jitsi/WebRTC deployment. The intended portal WebSocket authorization path is also broken by stale `Institute.ngo` queries.

Status: UI-triggered external-room prototype, not a complete random VC subsystem.

## 11. Geo-Tagging

Geo-tagging is genuinely implemented for inspection submission:

1. `Institute.latitude` and `Institute.longitude` store registered site coordinates.
2. `SubmitInspection.jsx` calls `navigator.geolocation.getCurrentPosition()` at submission time.
3. Coordinates are sent as `submitted_latitude` and `submitted_longitude`.
4. `InspectionReportCreateSerializer.validate()` calls `apps.core.geo.distance_meters()` and rejects locations over 200 meters.
5. `InspectionReportViewSet.create()` stores coordinates, distance, and verification booleans.
6. Evidence inherits report coordinates; the frontend also burns GPS/time/assignment text into image pixels.

Limitations: plain floats instead of PostGIS; no accuracy/radius metadata, device timestamp validation, anti-spoofing, offline capture, route history, or per-evidence independent coordinates. Both report flags are set to `True` after serializer validation rather than independently recomputed in `create()`.

## 12. Evidence Capture

Implemented path:

- `InspectionReportCreateSerializer` accepts multipart `evidence` files.
- `SubmitInspection.jsx` accepts multiple `image/*` files with `capture="environment"`, previews, watermarks, and uploads them.
- `InspectionReportViewSet.create()` creates `Evidence` rows linked to the report.
- `Evidence.file` stores under date-partitioned media paths and `EvidenceSerializer` exposes the file URL.
- `ReportDetail.jsx` displays image evidence and labels non-photo media types.

Missing/incorrect relative to the model and SIH:

- Backend explicitly rejects non-image content types; video/documents cannot currently be captured through the API.
- No file size limits, virus scanning, checksum, retention policy, resumable/offline upload, EXIF integrity validation, or object-storage requirement is enforced.
- Frontend says “photos/videos” but `accept="image/*"` prevents video selection.
- `media_type` is not inferred from the upload and defaults to `PHOTO`.

## 13. AI / ML / Automation Classification

### Real AI/ML

`apps/analytics/services/anomaly.py` uses scikit-learn `IsolationForest` with five features: attendance rate, camera online ratio, normalized latest inspection score, inspection frequency, and recent high alerts. It requires at least five active institute samples; below that it returns no anomalies and no anomaly score. This is unsupervised statistical anomaly detection, not computer vision, language AI, or a learned inspection model.

### Rule-based logic

`risk_engine.py::_factors_for()` adds fixed points for low attendance, all cameras offline, cameras offline over 48 hours, failed inspection, Isolation Forest anomaly, and repeated high alerts. Severity is deterministic: 0-30 LOW, 31-60 MEDIUM, 61-100 HIGH.

### Randomization / optimization

Surprise institute selection uses weighted `random.choices()`. Batch officer choice uses `random.choice()`. Direct officer choice is distance plus pending-workload scoring with radius and anti-collusion filters. None of this is machine learning.

### Placeholder/mock functionality

No YOLO person detection, headcount, reported-vs-detected attendance comparison, or CCTV visual anomaly detection exists. Empty `stream_url` in the frontend displays a public Mux test stream. VC room names are generated and embedded in Jitsi; no platform-owned VC system exists.

## 14. Attendance Analytics

Attendance is recorded through `POST /api/attendance/records/check-in/`, `check-out`, or generic create. `Attendance.jsx` lets an authenticated operator select an institute/staff pair, set status/notes, and check in/out. `summary` returns total, present, late, and absent counts; CSV export is available.

Risk analytics uses the last 30 days of records and computes `PRESENT / total marks`. Attendance below 70% adds `ATTENDANCE_MISMATCH` risk points. Isolation Forest also consumes attendance rate.

Missing: staff self-service identity, geofenced attendance, biometric/face validation, shift/roster, absence generation for unmarked staff, beneficiary attendance, attendance-to-CCTV headcount comparison, date-range summaries, and authorization scoping. The API trusts arbitrary IDs from any authenticated user and does not ensure `AttendanceRecord.institute == staff.institute`.

## 15. Risk and Anomaly Alerts

`collect_features()` gathers staff/beneficiary counts, 30-day attendance rate, active-camera online ratio and downtime, latest submitted inspection score, inspection frequency, and high-severity alerts over 90 days.

`run_risk_engine()` collects features, runs Isolation Forest across the batch, computes deterministic factors and a capped score, saves a new `RiskSnapshot`, creates an `AIAlert` for each factor unless the same type is already open, and attempts a Channels broadcast. Celery tasks can run this every six hours and audit CCTV hourly if Redis, worker, beat, and ASGI infrastructure are active. Alerts can be acknowledged/resolved by officials. Risk history is retained for charts.

Material risks:

- `features.py` uses `project__institute`, but `Project.institute` no longer exists; risk runs with beneficiaries can fail at feature collection.
- `consumers.py` uses `institute.ngo` and `ngo__admin_user`, but `Institute.ngo` no longer exists; portal WebSocket authorization can fail.
- Latest-snapshot queries use timestamp matching rather than robust per-institute subqueries; timestamp ties can return multiple snapshots.
- Alerts are deduplicated only while open; resolved alerts can be recreated on later runs.
- There is no model-version, feature-version, run actor, or explainability audit record.

## 16. Dashboard and Real-Time Monitoring

`Dashboard.jsx` displays institute/project totals, high-risk count, pending/submitted/overdue inspections, open alerts, map markers, inspection status, AI alerts, “Run AI Analysis”, and “Surprise Inspection”. `InstituteDetail.jsx` adds assignments, reports, risk breakdown/history, CCTV, CSV/PDF actions, and VC trigger.

REST loads occur on mount and after actions. `useAlertsSocket.js` connects to `/ws/analytics/alerts/?token=...` and reconnects. `AIAlertConsumer` can push alert-created, analysis-completed, assignment-created, and VC events. Celery beat schedules risk, CCTV audit, and assignment tasks.

This is a real-time-capable architecture, not guaranteed real-time monitoring by itself. It requires Daphne/ASGI, Redis, Channels, Celery worker, and beat. Without them, the UI degrades to REST/manual behavior. WebSocket broadcasts put all officials in a common `ai_alerts` group without state/district filtering, so officials can receive events outside REST scope. The consumer also has stale relationship references.

## 17. API Endpoint Catalog

All endpoints are mounted by `config/urls.py`. DRF routers provide standard list/create/retrieve/update/partial-update/delete actions where the viewset permits them.

### Authentication/accounts

- `POST /api/auth/login/` - JWT pair.
- `POST /api/auth/refresh/` - refresh access token.
- `POST /api-token-auth/` - legacy DRF token auth.
- `GET /api/accounts/me/` - current user and role.

### Registry

- `/api/registry/schemes/` - official Scheme CRUD.
- `/api/registry/ngos/` - official NGO CRUD.
- `/api/registry/institutes/` - official Institute CRUD, `initiate-vc`, `export-csv`.
- `/api/registry/projects/` - official Project CRUD, optional `?scheme=`.
- `/api/registry/staff/` - official Staff CRUD.
- `/api/registry/beneficiaries/` - official Beneficiary CRUD.
- `GET /api/registry/dashboard-summary/` - scoped dashboard counts.
- `/api/registry/portal/institutes/`, `/projects/`, `/staff/`, `/beneficiaries/` - read-only portal data.
- `GET /api/registry/portal/dashboard-summary/` - portal-scoped counts.

### Onboarding

- `POST /api/onboarding/register/` - public applicant registration and JWT.
- `GET /api/onboarding/schemes-catalogue/` - authenticated scheme catalogue.
- `/api/onboarding/applications/` - applicant-owned or Super Admin application list/create/retrieve/update/delete behavior.
- `POST /api/onboarding/applications/<id>/approve/` - Super Admin approval/provisioning.
- `POST /api/onboarding/applications/<id>/reject/` - Super Admin rejection.

### Inspections

- `/api/inspections/templates/` - authenticated read; official write.
- `/api/inspections/fields/` - official checklist-field CRUD.
- `/api/inspections/assignments/` - official history; field officers see own assignments.
- `POST /api/inspections/assignments/auto-assign/` - direct or batch assignment.
- `POST /api/inspections/assignments/surprise/` - weighted surprise selection.
- `GET /api/inspections/assignments/export-csv/` - assignment export.
- `/api/inspections/reports/` - scoped report list/retrieve/create.
- `GET /api/inspections/reports/assignments/` - officer pending assignments.
- `GET /api/inspections/reports/<id>/pdf/` - PDF or HTML report.
- `GET /api/inspections/submit/` - legacy server-rendered page.

### CCTV

- `/api/cctv/cameras/` - official camera CRUD.
- `POST /api/cctv/cameras/<id>/ping/` - OpenCV one-frame status refresh.
- `GET /api/cctv/cameras/<id>/stream/?token=<JWT>` - official-only MJPEG stream.

### Attendance

- `/api/attendance/records/` - authenticated attendance CRUD/list/filter.
- `POST /api/attendance/records/check-in/` - mark check-in.
- `POST /api/attendance/records/check-out/` - mark check-out.
- `GET /api/attendance/records/summary/` - aggregate counts.
- `GET /api/attendance/records/export-csv/` - CSV export.

### Analytics

- `POST /api/analytics/run/` - persist risk analysis.
- `GET /api/analytics/risk/` - latest snapshot per institute.
- `GET /api/analytics/risk/institute/<id>/live/` - fresh unsaved risk breakdown.
- `GET /api/analytics/risk/institute/<id>/pdf/` - risk report PDF/HTML.
- `GET /api/analytics/risk/institute/<id>/history/` - chronological snapshots.
- `GET /api/analytics/alerts/` - filterable alert list.
- `POST /api/analytics/alerts/<id>/acknowledge/` and `/resolve/` - alert lifecycle actions.
- `WS /ws/analytics/alerts/?token=<JWT>&institute=<optional>` - alert/analysis/assignment/VC events.

## 18. Frontend Screens and SIH Mapping

| Screen | Main implementation | SIH mapping |
|---|---|---|
| Login | `pages/Login.jsx` | Authentication |
| Applicant registration | `pages/Register.jsx` | NGO/Institute onboarding |
| Government dashboard | `pages/Dashboard.jsx` | Department monitoring, risk, alerts, surprise assignment |
| Institutes list/map | `pages/Institutes.jsx`, `components/ProjectMap.jsx` | Institute/project visibility and geo view |
| Institute detail | `pages/InstituteDetail.jsx` | Inspection history, CCTV, VC, risk, reports |
| Report detail | `pages/ReportDetail.jsx` | Report review/view, evidence, geolocation, export |
| Inspector assignments | `pages/InspectorAssignments.jsx` | PMU/Inspector assignment queue |
| Submit inspection | `pages/SubmitInspection.jsx` | Checklist, GPS, camera-image evidence, report submission |
| Attendance | `pages/Attendance.jsx` | Attendance entry, summary, export |
| Manage | `pages/admin/Manage.jsx` | Scheme/NGO/project/staff/beneficiary administration and batch assignment |
| Inspection templates | `pages/admin/InspectionTemplates.jsx`, `TemplateDetail.jsx` | Configurable checklist |
| Scheme applications | `pages/admin/SchemeApplications.jsx` | Government application review/allocation |
| NGO dashboard | `pages/ngo/NGODashboard.jsx` | NGO/Project Incharge portal and VC receipt |
| NGO institute detail | `pages/ngo/NGOInstituteDetail.jsx` | Portal view of own monitoring data |
| Apply/My Applications | `pages/ngo/ApplyForScheme.jsx`, `MyApplications.jsx` | Scheme application/status |
| AI alerts panel | `components/AIAlertsPanel.jsx` | Risk alert operations |
| CCTV panel | `components/CctvPanel.jsx` | Camera list/status/live-feed prototype |
| Risk trend | `components/RiskTrendChart.jsx` | Historical risk monitoring |

There is no native mobile app in this repository; the mobile-based inspection flow is a responsive React web form using browser geolocation and file capture.

## 19. Database Design Assessment

### Logically sound areas

- Custom user plus explicit role choices is a reasonable RBAC foundation.
- Assignment -> one report is correctly modeled as OneToOne for a single submission.
- Report -> many Evidence records is appropriate.
- Institute -> cameras/staff/assignments/attendance/risk snapshots/alerts is coherent for site monitoring.
- SchemeApplication is separated from provisioned registry entities and approved transactionally.
- HistoricalRecords on important entities is useful for auditability.

### Duplicate or unnecessary relationships

- `AttendanceRecord.institute` duplicates `staff.institute` and can become inconsistent; validate it strictly or derive it from staff.
- `InspectionReport.is_geofence_verified` and `location_verified` duplicate the same concept and are set together.
- `Camera.last_ping` is only a property alias for `last_online`.
- `SchemeApplication.created_ngo`, `created_institute`, and `created_project` are useful traceability links, but repeated approvals/applications have no organization reuse/uniqueness policy.

### Missing/incorrect relationships

- `Project` needs a site relationship: FK to `Institute`, many-to-many sites, or `ProjectSite`. Current `Project -> Scheme` cannot support reliable site-level monitoring or beneficiary risk features.
- `NGO` needs explicit relationships to its institutes/projects if it operates them. Scheme-based portal scoping is too broad.
- No inspection reviewer/decision relationship, acceptance/start/completion event, VC session/participant relation, camera health history, beneficiary attendance model, or alert acknowledgment actor.
- `features.py` uses removed `Project.institute`; `consumers.py` uses removed `Institute.ngo`. Django system checks do not catch these runtime query paths.

## 20. SIH Requirement Matrix

| SIH Requirement | Status | Evidence in Code | What is Missing | Priority |
|---|---|---|---|---|
| Centralized mobile application for real-time monitoring | 🟡 Partially implemented | `frontend/src/App.jsx`, dashboard, inspector portal, JWT API | No native mobile app; live operation depends on infrastructure; offline mobile support absent | High |
| Surprise inspections | ✅ Fully implemented | `select_surprise_institute()`, `surprise_action()`, Dashboard button | Formal policy, replayable randomness, notification guarantees | Medium |
| CCTV surveillance integration | 🟡 Partially implemented | `Camera`, OpenCV `_open_capture()`, `CctvPanel.jsx` | Production IP-camera fleet, gateway, recording, retention, secure streams | Critical |
| Random inspection assignment | ✅ Fully implemented | `run_auto_assignment()`, `random.choice()`, `auto_assign()` | Reproducible seed use, fairness metrics | Medium |
| DoSJE schemes, projects, institutes, NGOs | 🟡 Partially implemented | `Scheme`, `NGO`, `Institute`, `Project`, onboarding | Missing NGO/site/project relationships; project-site monitoring ambiguous | Critical |
| Live CCTV feed integration | 🟡 Partially implemented | OpenCV MJPEG backend; HLS player in `CctvPanel.jsx` | Frontend ignores MJPEG; default is public demo stream; no production transport | Critical |
| Random VC with incharge/staff/beneficiaries | 🔴 Not implemented | `initiate_vc()`, Jitsi iframe, VC alert | Session/participant/consent/audit/recording and actual targeting | Critical |
| Real-time monitoring dashboard | 🟡 Partially implemented | `Dashboard.jsx`, REST summary, Channels, Celery schedule | Infrastructure hardening, scoped WebSocket events, reliable live data | High |
| Mobile inspection module for PMU/teams | 🟡 Partially implemented | `InspectorAssignments.jsx`, `SubmitInspection.jsx` | Native/offline mode, accept/start flow, complete media capture, sync | High |
| Geo-tagged inspection reports | ✅ Fully implemented | `getCurrentPosition()`, `distance_meters()`, 200m validation, report fields | Anti-spoofing, accuracy metadata, PostGIS, offline integrity | Medium |
| Live evidence capture | 🟡 Partially implemented | Multipart evidence, camera capture, watermarking | Video/document support, robust upload, security/integrity | High |
| AI-based anomaly detection | 🟡 Partially implemented | `IsolationForest` in `services/anomaly.py` | Domain model, model monitoring, visual anomaly detection | Medium |
| Attendance analytics | 🟡 Partially implemented | `AttendanceRecord`, summary, `collect_features()` | Secure capture, geofencing/biometrics, beneficiary/headcount comparison, date analytics | High |
| Inspection review and completion | 🔴 Not implemented | Report viewer and `SUBMITTED` status only | Reviewer workflow, approve/reject, corrective action, completion | Critical |
| Risk/anomaly alerts | 🟡 Partially implemented | `run_risk_engine()`, `AIAlert`, Channels | Fix stale joins, alert ownership/audit, governance | Critical |

## 21. Top 10 Next Implementations

1. **Repair flattened-schema runtime failures.** Replace `project__institute` in `features.py` and stale `institute.ngo` references in `consumers.py` with an intentional project-site/organization relationship. Add analytics and portal WebSocket tests.
2. **Restore a correct project-site domain model.** Add `Project -> Institute` or `ProjectSite`, explicit NGO operating relationships, and migrate onboarding/portal/risk queries.
3. **Build the inspection state machine.** Add `ACCEPTED`, `IN_PROGRESS`, `SUBMITTED`, `UNDER_REVIEW`, `CHANGES_REQUESTED`, `APPROVED`, and `COMPLETED`, with timestamps, actors, reviewer actions, and corrective actions.
4. **Replace demo CCTV playback with a real camera pipeline.** Integrate RTSP/IP cameras through a controlled gateway, use signed/proxied URLs, remove the Mux fallback, and add recordings/health history.
5. **Implement VC as a first-class audited workflow.** Add session/participant models, select incharge/staff/beneficiaries, persist invitations/join events, consent, duration, outcome, and controlled deployment.
6. **Make evidence capture complete and secure.** Support image/video/document consistently, infer/validate media type, enforce size/extensions/content scanning, preserve metadata, and support resumable/offline uploads.
7. **Close authorization and tenancy gaps.** Scope attendance, staff/institute consistency, registry writes, portal data, WebSocket groups, and state/district access by object-level policies.
8. **Deliver a real mobile/offline inspection client.** Add native or PWA offline checklist/GPS/media capture, encrypted queue, sync conflicts, assignment acceptance/start, and device audit.
9. **Strengthen analytics governance and quality.** Fix feature joins, add date-scoped metrics, model/version metadata, evaluation tests, thresholds, alert ownership, explainability, and idempotent scheduled runs.
10. **Operationalize real-time services.** Provide Redis/Daphne/Celery deployment, health checks, retries/idempotency, scoped broadcasts, observability, backups, and production secrets/storage handling.

## Final Assessment

The project demonstrates most of the SIH concept in a coherent prototype: government dashboard, applicant onboarding, configurable inspections, randomized assignment, geo-validated evidence reports, CCTV status, attendance signals, risk scoring, and alert presentation. The strongest implemented slice is the inspection/report path.

The biggest blockers to calling it a complete SIH solution are the missing inspection review lifecycle, unreliable project/site data model, demo-level CCTV/VC, incomplete evidence media support, authorization gaps, and stale runtime relationships in analytics/WebSockets. Fixing those areas in the order above would move the project from a feature-rich demonstration to a defensible end-to-end monitoring platform.
# Frontend-completion patch — integration guide

Goal: every feature that previously required `/admin/` (except creating user
accounts, which you chose to keep in `/admin/`) is now reachable as a normal
logged-in user through the React app.

No new pip/npm packages. No new migrations — every change is either a new
frontend page/component, or a small serializer/view/urls edit reusing models
that already existed.

## How to apply

Copy each file below over the matching path in your project root,
overwriting the existing one. New files just get added.

### Backend (all **replace**)
- `apps/inspections/serializers.py` — `InspectionField.template` is now
  writable; `InspectionReportSerializer` gains `institute`, `institute_name`,
  `officer_name`, `template_name`, `answers_display` (human-readable answers
  instead of raw `{field_id: answer}`); `InspectionAssignmentSerializer`
  gains `has_report`.
- `apps/inspections/views.py` — `InspectionTemplateViewSet` is now full CRUD
  (read: any authenticated user, same as before; write: officials only via
  `get_permissions()`). New `InspectionFieldViewSet` (officials only,
  supports `?template=<id>`). `InspectionReportViewSet` now lets officials
  list/retrieve/PDF **any** report in scope (previously officer-only) via
  `_scoped_queryset()`.
- `apps/inspections/urls.py` — registers the new `InspectionFieldViewSet`
  at `/api/inspections/fields/`.
- `apps/registry/serializers.py` — `NGOSerializer` now includes `admin_user`
  (previously omitted, so the NGO portal could only ever be wired up from
  `/admin/`); `StaffSerializer`/`BeneficiarySerializer` gain readable
  `institute_name`/`project_name` for the new Manage tables.

### Frontend (**replace**)
- `src/App.jsx` — adds `/manage`, `/templates`, `/templates/:id`,
  `/institutes/:instituteId/reports/:assignmentId`,
  `/inspector/reports/:assignmentId`.
- `src/components/Layout.jsx` — adds "Inspection Templates" and "Manage" to
  the sidebar nav.
- `src/pages/Dashboard.jsx` — passes `onChanged={loadData}` into
  `AIAlertsPanel` so Acknowledge/Resolve refreshes the stat cards.
- `src/pages/Institutes.jsx` — adds a "+ New Institute" form.
- `src/pages/InstituteDetail.jsx` — adds "Edit Institute", full Project
  add/edit/delete, and a "View report" link per submitted inspection.
- `src/pages/InspectorAssignments.jsx` — adds "View report" link for the
  officer's own submitted assignments.
- `src/components/CctvPanel.jsx` — adds "+ Add camera" / Edit / Delete.
- `src/components/AIAlertsPanel.jsx` — adds Acknowledge / Resolve buttons.

### Frontend (**new files**)
- `src/pages/admin/Manage.jsx` — tabbed CRUD: Schemes, NGOs, Staff,
  Beneficiaries.
- `src/pages/admin/InspectionTemplates.jsx` — list/create/activate/delete
  templates.
- `src/pages/admin/TemplateDetail.jsx` — add/edit/reorder/delete a
  template's checklist questions.
- `src/pages/ReportDetail.jsx` — full report viewer (answers + evidence
  photos + PDF download), used by both officials and field officers.

## What you can now do without `/admin/`

| Feature | Where |
|---|---|
| Create/edit Schemes, NGOs (incl. wiring `admin_user` for the NGO portal) | `/manage` |
| Create/edit Staff, Beneficiaries | `/manage` |
| Create/edit Institutes (incl. `incharge` for the Project Incharge portal) | `/institutes` (create) and `/institutes/:id` → **Edit Institute** |
| Create/edit/delete Projects | `/institutes/:id` → Projects panel |
| Build inspection checklists (add/reorder/remove questions, any of the 5 field types) | `/templates` → click a template |
| View a submitted inspection's actual answers + evidence photos | `/institutes/:id` → Inspection history → **View report** (officials), or `/inspector` → **View report** (officers, own reports only) |
| Add/edit/delete CCTV cameras | `/institutes/:id` → CCTV panel → **+ Add camera** |
| Acknowledge / Resolve an AI alert | Dashboard → AI alerts panel |

## Still intentionally in `/admin/`
- Creating user accounts and setting roles (your choice, for security)
- Setting an officer's `base_latitude`/`base_longitude` (used by the
  auto-assignment engine) — minor, could be added to a future "My Profile"
  page if you want it later

## Quick test pass after copying files in

```bash
python manage.py check
python manage.py runserver
```
```bash
cd frontend && npm run dev
```

1. Log in as an official → sidebar should now show **Inspection Templates**
   and **Manage**.
2. `/manage` → create a Scheme, an NGO. Set the NGO's "Admin user ID" to a
   test account's numeric ID (find it in `/admin/` Users list once) — then
   log in as that account and confirm it lands on `/ngo-portal` and can see
   institutes under that NGO.
3. `/institutes` → **+ New Institute**, fill it in, save, confirm it appears
   in the table and on the dashboard map.
4. `/institutes/:id` → **Edit Institute**, change something, save, confirm
   it persists. Add a Project inline, edit it, delete it.
5. `/templates` → **+ New Template**, then **Edit questions** → add a few
   questions of different types, reorder with ↑/↓.
6. Have a field officer submit an inspection against that template
   (`/inspector`) → as an official, open the institute → Inspection history
   → **View report** → confirm answers render with real labels and any
   evidence photo displays. Try **Download PDF** too.
7. `/institutes/:id` → CCTV panel → **+ Add camera**, save, confirm it lists
   with OFFLINE status (expected — no real webcam), then Edit and Delete it.
8. Dashboard → run **Run AI Analysis** until an alert appears → click
   **Acknowledge**, then **Resolve** → confirm it drops off the list and the
   "Open AI alerts" stat card decrements.

# Architecture-fix patch — Scheme -> {NGO, Institute, Project}

## What was wrong, and what this fixes

**Before (wrong):** `Scheme -> NGO -> Institute -> Project`
(`Institute.ngo` FK, `Project.institute` FK)

**After (correct):** `Scheme -> {NGO, Institute, Project}` independently
NGO, Institute, and Project each carry their own FK straight to `Scheme`.
`Institute.ngo` and `Project.institute` are gone. `Staff -> Institute` and
`Beneficiary -> Project` are untouched — those were never part of the wrong
nesting, they're simple "works at" / "enrolled in" relations.

## How to apply

Copy every file below over the matching path in your project root,
overwriting the existing one.

### Backend
| File | What changed |
|---|---|
| `apps/registry/models.py` | **Replace.** `NGO` gains `scheme` FK. `Institute.ngo` removed. `Project.institute` removed, `Project.scheme` added. |
| `apps/registry/migrations/0002_flatten_scheme_hierarchy.py` | **New file.** Drops the old FKs, adds the new ones (see "Migrating existing data" below). |
| `apps/registry/admin.py` | **Replace.** `list_display`/`list_filter` updated to the new fields. |
| `apps/registry/serializers.py` | **Replace.** `NGOSerializer` gains `scheme`/`scheme_name`. `InstituteSerializer` loses `ngo`/`ngo_name`. `ProjectSerializer` loses `institute`/`institute_name`, gains `scheme`/`scheme_name`. |
| `apps/registry/views.py` | **Replace.** CSV export drops the NGO column. `ProjectViewSet` now filters by `?scheme=` instead of `?institute=`. Dashboard's "active projects" count is now scheme-scoped. |
| `apps/registry/portal_views.py` | **Replace.** NGO-portal scoping is now Scheme-based (see below — this is the one real behavior change). |
| `apps/inspections/services.py` | **Replace.** The anti-collusion check ("don't send the same officer back to institutes tied to the same NGO too often") now keys off `Institute.scheme` since `Institute.ngo` no longer exists. |
| `apps/attendance/tests.py`, `apps/cctv/tests/test_camera_status.py`, `apps/inspections/tests/test_submission.py`, `apps/inspections/tests/test_auto_assignment.py` | **Replace.** These constructed `Institute.objects.create(..., ngo=ngo, ...)`, which no longer compiles against the new model — updated to the new shape. |

### Frontend
| File | What changed |
|---|---|
| `frontend/src/pages/Institutes.jsx` | **Replace.** Create form drops the NGO select (Institute has no `ngo` field); table shows a "Scheme" column instead of "NGO". |
| `frontend/src/pages/InstituteDetail.jsx` | **Replace.** Header no longer shows `ngo_name`. The "Projects" panel that used to live on this page is **removed** — Projects aren't tied to one Institute anymore, so they're managed from `/manage` → **Projects** instead. |
| `frontend/src/pages/admin/Manage.jsx` | **Replace.** NGOs tab gets a Scheme select. New **Projects** tab (Scheme-scoped CRUD, replacing the old per-institute panel). Beneficiaries picker now labels projects by Scheme instead of Institute. |
| `frontend/src/pages/ngo/NGOInstituteDetail.jsx` | **Replace.** Drops `ngo_name`; the "Projects" panel now fetches by the institute's Scheme (`?scheme=`) instead of by institute id. |

## Migrating existing data

This is a real schema change on required (`NOT NULL`) foreign keys. The
migration adds `NGO.scheme` and `Project.scheme` with a one-off placeholder
default (`scheme_id=1`) purely so Django can add the column — it does
**not** know which real Scheme your existing NGOs/Projects should belong to.

Two options:

1. **Fresh dev DB (recommended for this stage of the project):** stop the
   server, delete `db.sqlite3`, then:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
   Re-create your Schemes/NGOs/Institutes/Projects through `/admin/` or
   `/manage` with the correct Scheme links from the start. Given this repo's
   `.gitignore` already excludes `db.sqlite3` (no committed data), this is
   the path of least friction.

2. **Keep existing data:** apply the migration as-is, then in
   `python manage.py shell` (or `/admin/`) manually set the correct
   `scheme` on every existing `NGO` and `Project` row (they'll all point at
   whatever Scheme has `id=1` until you do).

Either way, run:
```bash
python manage.py migrate
python manage.py check
```

## The one real behavior change: NGO portal scoping

The NGO_ADMIN portal used to show "every Institute under my NGO" via
`Institute.ngo__admin_user`. That link is gone by design. The adapted rule
(`apps/registry/portal_views.py::portal_scoped_schemes/_institutes/_projects`)
is:

- **NGO_ADMIN** sees every Institute/Project under any **Scheme** that an
  NGO they administer also belongs to.
- **PROJECT_INCHARGE** is unaffected — still scoped by `Institute.incharge`,
  which never depended on NGO.

This is the closest honest equivalent under the flat model, since Scheme is
now the only thing NGO/Institute/Project share. If later you want NGO
portals scoped more narrowly than "same Scheme" (e.g. an explicit
NGO↔Project assignment table), `portal_views.py` is the single place to
change it — everything else reads through those three helper functions.

## Quick sanity check after copying files in

```bash
python manage.py migrate      # or delete db.sqlite3 first, see above
python manage.py check
python manage.py test         # confirms the updated test files pass
python manage.py runserver
```
```bash
cd frontend && npm run dev
```

Then:
1. `/manage` → **Schemes**: create a Scheme.
2. `/manage` → **NGOs**: create an NGO, picking that Scheme (no Institute
   link anymore).
3. `/institutes` → **+ New Institute**: picks a Scheme directly (no NGO
   field).
4. `/manage` → **Projects** (new tab): create a Project, picking a Scheme
   directly (no Institute field).
5. Open an Institute's detail page — confirm there's no NGO shown, and the
   old Projects panel is gone (replaced by Manage → Projects).
6. Log in as an NGO_ADMIN test account (`NGO.admin_user`) → `/ngo-portal`
   should show institutes/projects under the same Scheme as their NGO.

# Onboarding & Approval patch — NGO/Institute self-registration -> Government review -> Monitoring begins

Implements the flow from your diagram end-to-end:

```
GOVERNMENT -> Creates Schemes -> Scheme Catalogue
    -> NGO / Institute / Project apply/propose
    -> Government Review -> APPROVED / REJECTED
    -> (if approved) Scheme Allotted -> Monitoring begins
```

"Government" = the DoSJE HQ Super Admin / Django superuser, exactly as you
specified — not District/State Authority.

## New Django app: `apps/onboarding`

A `SchemeApplication` is a *request*, kept separate from `apps.registry`'s
real NGO/Institute/Project tables. Nothing in the existing monitoring
platform (CCTV, attendance, inspections, AI risk engine) touches this app
at all — it only ever produces normal `NGO`/`Institute`/`Project` rows,
which is why nothing else needed to change.

| File | Purpose |
|---|---|
| `models.py` | `SchemeApplication` — applicant, chosen Scheme, org details (name/registration number/address/etc — become the NGO or Institute row), proposal (project name/plan/fund amount/dates — becomes the Project row), and review fields (status/notes/reviewed_by/reviewed_at). |
| `migrations/0001_initial.py` | Creates the table. Depends on `registry.0002_flatten_scheme_hierarchy`, so apply the earlier architecture-fix patch first if you haven't. |
| `services.py` | `approve_application()` — the one place that actually creates the NGO/Institute + Project rows and promotes the applicant's account into `NGO.admin_user` / `Institute.incharge`, all in one transaction. `reject_application()`. |
| `serializers.py` | `ApplicantRegisterSerializer` (public registration), `SchemeApplicationCreateSerializer` (applying), `SchemeApplicationSerializer` (full read, used by both the applicant's own list and the government queue), `SchemeApplicationReviewSerializer` (approve/reject body). |
| `views.py` | `RegisterApplicantView` (`POST /api/onboarding/register/`, public), `SchemeCatalogueView` (`GET /api/onboarding/schemes-catalogue/`, any authenticated user), `SchemeApplicationViewSet` (`/api/onboarding/applications/` — list/create scoped to your own applications unless you're the Super Admin, plus `approve`/`reject` actions locked to Super Admin). |
| `urls.py`, `admin.py`, `apps.py` | Standard wiring; applications are also visible/reviewable from `/admin/` if you'd rather do it there. |

## Changed files

| File | What changed |
|---|---|
| `apps/core/permissions.py` | **Replace.** Adds `is_super_admin()` / `IsSuperAdmin` — deliberately narrower than `is_official()`, since District/State Authority can see the dashboard but must NOT approve/reject applications per your spec. |
| `config/settings.py` | **Replace.** Adds `"apps.onboarding"` to `LOCAL_APPS`. |
| `config/urls.py` | **Replace.** Mounts `path("api/onboarding/", include("apps.onboarding.urls"))`. |

## Frontend

| File | What changed |
|---|---|
| `frontend/src/pages/Register.jsx` | **New.** Public self-registration — pick "NGO" or "Institute", fill in the admin's own name/username/password. Creates a bare login (role `NGO_ADMIN` or `PROJECT_INCHARGE`), no org exists yet. |
| `frontend/src/pages/Login.jsx` | **Replace — also fixes a real bug.** The old post-login redirect only checked `isOfficial(me) ? "/" : "/inspector"`, which sent NGO_ADMIN/PROJECT_INCHARGE accounts to `/inspector`. `FieldOfficerRoute` would then bounce them to `/`, `OfficialRoute` would bounce them back to `/inspector` — an infinite redirect loop. This never surfaced before because nothing created NGO_ADMIN/PROJECT_INCHARGE accounts through the login flow; now that `/register` does, it would have. Fixed to route through all three portals like `RoleRedirect.jsx` already does. Also adds a "Register here" link. |
| `frontend/src/pages/ngo/ApplyForScheme.jsx` | **New.** The "apply/propose" step — scheme picker (from the catalogue endpoint) + org details + project plan/fund amount/dates. Applicant type is inferred from the logged-in user's role, not asked again. |
| `frontend/src/pages/ngo/MyApplications.jsx` | **New.** Applicant's own applications with status and any government review note. |
| `frontend/src/pages/ngo/NGODashboard.jsx` | **Replace.** Header gains "Apply for a Scheme" / "My Applications" buttons. Empty state (zero institutes — true for every freshly-registered account) now explains the approval flow and links to Apply, instead of just "nothing here yet". |
| `frontend/src/components/NGOPortalLayout.jsx` | **Replace.** Sidebar gains "Apply for a Scheme" / "My Applications". |
| `frontend/src/pages/admin/SchemeApplications.jsx` | **New.** Government Review step — list pending/approved/rejected applications, expand to read the full plan, and (Super Admin only) approve with an adjustable fund amount or reject with a note. |
| `frontend/src/components/Layout.jsx` | **Replace.** Adds a "Scheme Applications" sidebar link, shown only when the logged-in user is the Super Admin (`is_superuser` or `role === "SUPER_ADMIN"`) — District/State Authority won't see a button they can't use. |
| `frontend/src/App.jsx` | **Replace.** Adds `/register` (public), `/ngo-portal/apply`, `/ngo-portal/applications`, `/scheme-applications` (official route; backend still enforces Super-Admin-only approve/reject even if someone opens the URL directly). |

## How to apply

1. Apply this on top of the earlier `scheme-flatten-patch.zip` — `apps/onboarding`'s migration depends on `registry.0002_flatten_scheme_hierarchy`.
2. Copy every file above into place, matching paths.
3. ```bash
   python manage.py migrate
   python manage.py check
   python manage.py runserver
   ```
   ```bash
   cd frontend && npm run dev
   ```

## Walking through the flow end to end

1. Go to `/register`, register as an **NGO** (or Institute) admin.
2. You're logged straight in and land on `/ngo-portal` — empty state, "Apply for a Scheme".
3. Click through, pick a Scheme (create one first from `/manage` → Schemes if none exist yet), fill in the org + project plan + fund amount, submit.
4. Log back in as your **Super Admin** account → `/scheme-applications` (sidebar link only you see) → the application is under **PENDING** → expand "View plan" → adjust the approved amount if you like → **Approve**.
5. Log back in as the NGO/Institute account → `/ngo-portal` now shows the real Institute/NGO and Project, with the approved funding as `sanctioned_budget` — CCTV, attendance, inspections, AI risk scoring all work on it exactly as before, since approval just creates normal `apps.registry` rows.
6. Try rejecting a different application as Super Admin — the applicant sees the rejection + your note under "My Applications", nothing is created.

## Design notes / things worth knowing

- **Why a separate app instead of bolting onto `apps.registry`:** an application is not yet a real NGO/Institute — validating and reviewing it has a different lifecycle (pending/approved/rejected) than the CRUD `apps.registry` already does. Keeping it separate means none of the existing registry/portal/analytics code needed to change.
- **Fund amount can be adjusted on approval:** `approved_fund_amount` defaults to what the applicant requested but the Super Admin can lower/raise it before approving; the created `Project.sanctioned_budget` uses whatever was actually approved, not the original ask.
- **One applicant, one role, one org type:** the role picked at `/register` (NGO_ADMIN vs PROJECT_INCHARGE) is what determines whether their applications create an NGO or an Institute — there's no per-application override, matching "he will register himself as NGO/Institute" from your spec.
- **Not built (flag if you need it):** an applicant can currently only ever get one NGO/one Institute (each approval creates one), but can submit unlimited *Project* applications under different schemes over time — each approved one just adds another `Project` row. If you want a cap, or want a second scheme application to reuse an already-approved NGO/Institute rather than create a fresh one, that's a follow-up to `apps.onboarding.services.approve_application`.

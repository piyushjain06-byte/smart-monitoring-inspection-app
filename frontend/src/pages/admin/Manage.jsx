import { useEffect, useState } from "react";
import { ClipboardCheck, LoaderCircle, RefreshCw } from "lucide-react";
import { autoAssignInspections, client } from "../../api/client";

const TABS = ["Schemes", "NGOs", "Projects", "Staff", "Beneficiaries", "Inspections"];

// ---------------------------------------------------------------------------
// Generic list+form CRUD block. Each tab below configures this once instead
// of writing four near-identical table/form components — the ProjectMap
// panels use the same "white card, hairline border" look everywhere else,
// so this reuses those Tailwind + CSS-var conventions.
// ---------------------------------------------------------------------------
function CrudPanel({ endpoint, columns, formFields, emptyLabel, rowLabel }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // null = not editing, {} = new, {...} = existing
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    client.get(endpoint).then(({ data }) => setRows(data)).finally(() => setLoading(false));
  }

  useEffect(load, [endpoint]);

  function startCreate() {
    const blank = {};
    formFields.forEach((f) => (blank[f.name] = f.default ?? ""));
    setForm(blank);
    setEditing({});
  }

  function startEdit(row) {
    setForm({ ...row });
    setEditing(row);
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = { ...form };
      formFields.forEach((f) => {
        if (f.type === "number" && payload[f.name] === "") payload[f.name] = null;
      });
      if (editing && editing.id) {
        await client.patch(`${endpoint}${editing.id}/`, payload);
      } else {
        await client.post(endpoint, payload);
      }
      setEditing(null);
      load();
    } catch (err) {
      const detail = err.response?.data;
      setError(typeof detail === "string" ? detail : JSON.stringify(detail) || "Could not save.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(row) {
    if (!window.confirm(`Delete "${rowLabel(row)}"? This cannot be undone.`)) return;
    try {
      await client.delete(`${endpoint}${row.id}/`);
      load();
    } catch {
      setError("Could not delete — it may still be referenced elsewhere.");
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-[var(--ink-soft)]">{rows.length} record(s)</p>
        <button
          onClick={startCreate}
          className="bg-[var(--ink)] text-white text-sm font-medium px-3 py-1.5 hover:bg-[var(--accent)] transition-colors"
        >
          + New
        </button>
      </div>

      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

      {editing !== null && (
        <form onSubmit={handleSave} className="bg-white border border-[var(--line)] p-4 grid grid-cols-1 md:grid-cols-2 gap-3">
          {formFields.map((f) => (
            <label key={f.name} className="text-sm space-y-1">
              <span className="text-[var(--ink-soft)]">{f.label}</span>
              {f.type === "select" ? (
                <select
                  className="w-full border border-[var(--line)] px-3 py-2 bg-white"
                  value={form[f.name] ?? ""}
                  onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
                  required={f.required}
                >
                  <option value="">--</option>
                  {(f.options || []).map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              ) : f.type === "checkbox" ? (
                <input
                  type="checkbox"
                  className="block mt-1"
                  checked={!!form[f.name]}
                  onChange={(e) => setForm({ ...form, [f.name]: e.target.checked })}
                />
              ) : (
                <input
                  type={f.type || "text"}
                  className="w-full border border-[var(--line)] px-3 py-2"
                  value={form[f.name] ?? ""}
                  onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
                  required={f.required}
                />
              )}
            </label>
          ))}
          <div className="md:col-span-2 flex gap-2 pt-1">
            <button
              type="submit"
              disabled={saving}
              className="bg-[var(--ink)] text-white text-sm font-medium px-4 py-2 hover:bg-[var(--accent)] disabled:opacity-60"
            >
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              onClick={() => setEditing(null)}
              className="border border-[var(--line)] text-sm font-medium px-4 py-2"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="bg-white border border-[var(--line)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--line)] text-left text-[var(--ink-soft)]">
              {columns.map((c) => (
                <th key={c.key} className="px-4 py-2 font-medium">{c.label}</th>
              ))}
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td className="px-4 py-4 text-[var(--ink-soft)]" colSpan={columns.length + 1}>Loading…</td></tr>
            )}
            {!loading && rows.length === 0 && (
              <tr><td className="px-4 py-4 text-[var(--ink-soft)]" colSpan={columns.length + 1}>{emptyLabel}</td></tr>
            )}
            {rows.map((row) => (
              <tr key={row.id} className="border-b border-[var(--line)] last:border-0">
                {columns.map((c) => (
                  <td key={c.key} className="px-4 py-2.5">{c.render ? c.render(row) : row[c.key]}</td>
                ))}
                <td className="px-4 py-2.5 text-right whitespace-nowrap">
                  <button onClick={() => startEdit(row)} className="text-[var(--accent)] underline mr-3">Edit</button>
                  <button onClick={() => handleDelete(row)} className="text-[var(--danger)] underline">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SchemesTab() {
  return (
    <CrudPanel
      endpoint="/registry/schemes/"
      columns={[{ key: "name", label: "Name" }, { key: "description", label: "Description" }]}
      formFields={[
        { name: "name", label: "Name", required: true },
        { name: "description", label: "Description" },
      ]}
      emptyLabel="No schemes yet."
      rowLabel={(r) => r.name}
    />
  );
}

// FLATTENED ARCHITECTURE: NGO -> Scheme directly now (no Institute
// ownership) — the create/edit form gets a Scheme select.
function NGOsTab() {
  const [schemes, setSchemes] = useState([]);
  useEffect(() => {
    client.get("/registry/schemes/").then(({ data }) => setSchemes(data));
  }, []);

  return (
    <CrudPanel
      endpoint="/registry/ngos/"
      columns={[
        { key: "name", label: "Name" },
        { key: "scheme_name", label: "Scheme" },
        { key: "registration_number", label: "Reg. No." },
        { key: "contact_person", label: "Contact" },
        { key: "admin_user", label: "Admin user ID" },
      ]}
      formFields={[
        { name: "name", label: "Name", required: true },
        {
          name: "scheme", label: "Scheme", type: "select", required: true,
          options: schemes.map((s) => ({ value: s.id, label: s.name })),
        },
        { name: "registration_number", label: "Registration number", required: true },
        { name: "contact_person", label: "Contact person" },
        { name: "contact_phone", label: "Contact phone" },
        { name: "contact_email", label: "Contact email", type: "email" },
        {
          name: "admin_user", label: "Admin user ID (NGO portal login — check /admin/ Users for the ID)",
          type: "number",
        },
      ]}
      emptyLabel="No NGOs yet."
      rowLabel={(r) => r.name}
    />
  );
}

// FLATTENED ARCHITECTURE (new tab): Projects used to be managed from inside
// an Institute's detail page (Project -> Institute). Now that Project ->
// Scheme directly, they're a first-class Manage tab of their own, same
// pattern as NGOs.
function ProjectsTab() {
  const [schemes, setSchemes] = useState([]);
  useEffect(() => {
    client.get("/registry/schemes/").then(({ data }) => setSchemes(data));
  }, []);

  return (
    <CrudPanel
      endpoint="/registry/projects/"
      columns={[
        { key: "name", label: "Name" },
        { key: "scheme_name", label: "Scheme" },
        { key: "start_date", label: "Start date" },
        { key: "end_date", label: "End date" },
        {
          key: "is_active", label: "Status",
          render: (r) => (r.is_active ? "Active" : "Inactive"),
        },
      ]}
      formFields={[
        { name: "name", label: "Name", required: true },
        {
          name: "scheme", label: "Scheme", type: "select", required: true,
          options: schemes.map((s) => ({ value: s.id, label: s.name })),
        },
        { name: "start_date", label: "Start date", type: "date" },
        { name: "end_date", label: "End date", type: "date" },
        { name: "sanctioned_budget", label: "Sanctioned budget", type: "number" },
        { name: "is_active", label: "Active", type: "checkbox", default: true },
      ]}
      emptyLabel="No projects yet."
      rowLabel={(r) => r.name}
    />
  );
}

function StaffTab() {
  const [institutes, setInstitutes] = useState([]);
  useEffect(() => {
    client.get("/registry/institutes/").then(({ data }) => setInstitutes(data));
  }, []);

  return (
    <CrudPanel
      endpoint="/registry/staff/"
      columns={[
        { key: "full_name", label: "Name" },
        { key: "institute_name", label: "Institute" },
        { key: "designation", label: "Designation" },
        { key: "phone_number", label: "Phone" },
      ]}
      formFields={[
        { name: "full_name", label: "Full name", required: true },
        {
          name: "institute", label: "Institute", type: "select", required: true,
          options: institutes.map((i) => ({ value: i.id, label: i.name })),
        },
        { name: "designation", label: "Designation" },
        { name: "phone_number", label: "Phone number" },
      ]}
      emptyLabel="No staff records yet."
      rowLabel={(r) => r.full_name}
    />
  );
}

function BeneficiariesTab() {
  const [projects, setProjects] = useState([]);
  useEffect(() => {
    client.get("/registry/projects/").then(({ data }) => setProjects(data));
  }, []);

  return (
    <CrudPanel
      endpoint="/registry/beneficiaries/"
      columns={[
        { key: "full_name", label: "Name" },
        { key: "project_name", label: "Project" },
        { key: "phone_number", label: "Phone" },
        { key: "enrolled_on", label: "Enrolled on" },
      ]}
      formFields={[
        { name: "full_name", label: "Full name", required: true },
        {
          // FLATTENED ARCHITECTURE: Project -> Scheme now, not Institute —
          // the picker label shows the project's Scheme instead.
          name: "project", label: "Project", type: "select", required: true,
          options: projects.map((p) => ({ value: p.id, label: `${p.name} (${p.scheme_name})` })),
        },
        { name: "phone_number", label: "Phone number" },
      ]}
      emptyLabel="No beneficiaries yet."
      rowLabel={(r) => r.full_name}
    />
  );
}

function InspectionsTab() {
  const [radiusKm, setRadiusKm] = useState(50);
  const [dueInHours, setDueInHours] = useState(4);
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [feedback, setFeedback] = useState(null);

  function loadAssignments() {
    setLoading(true);
    client.get("/inspections/assignments/")
      .then(({ data }) => setAssignments(Array.isArray(data) ? data : data.results || []))
      .catch(() => setFeedback({ ok: false, message: "Could not load inspection assignments." }))
      .finally(() => setLoading(false));
  }

  useEffect(loadAssignments, []);

  async function handleAutoAssign() {
    setRunning(true);
    setFeedback(null);
    try {
      const { data } = await autoAssignInspections({
        radius_km: Number(radiusKm),
        due_in_hours: Number(dueInHours),
      });
      setFeedback({
        ok: true,
        message: `${data.assigned ?? 0} inspection(s) assigned. ${data.skipped ?? 0} institute(s) skipped.`,
      });
      loadAssignments();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setFeedback({ ok: false, message: typeof detail === "string" ? detail : "Could not run automated duty assignment." });
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-4">
      <section className="bg-white border border-[var(--line)] p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-[var(--ink)] flex items-center gap-2">
              <ClipboardCheck size={18} aria-hidden="true" />
              Automated Inspector Duty Assignment
            </h2>
            <p className="text-sm text-[var(--ink-soft)] mt-1 max-w-2xl">
              Randomly assigns high-risk or overdue institutes to nearby officers while applying workload and anti-collusion checks.
            </p>
          </div>
          <button
            type="button"
            onClick={handleAutoAssign}
            disabled={running}
            className="inline-flex items-center gap-2 bg-[var(--ink)] text-white text-sm font-medium px-4 py-2 hover:bg-[var(--accent)] transition-colors disabled:opacity-60"
          >
            {running ? <LoaderCircle size={16} className="animate-spin" aria-hidden="true" /> : <ClipboardCheck size={16} aria-hidden="true" />}
            {running ? "Assigning…" : "Run AI Duty Assignment"}
          </button>
        </div>

        <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg">
          <label className="text-sm space-y-1">
            <span className="block text-[var(--ink-soft)]">Radius (km)</span>
            <input type="number" min="1" max="500" step="1" value={radiusKm} onChange={(e) => setRadiusKm(e.target.value)} className="w-full border border-[var(--line)] px-3 py-2" />
          </label>
          <label className="text-sm space-y-1">
            <span className="block text-[var(--ink-soft)]">Short-notice due window (hours)</span>
            <input type="number" min="2" max="24" step="1" value={dueInHours} onChange={(e) => setDueInHours(e.target.value)} className="w-full border border-[var(--line)] px-3 py-2" />
          </label>
        </div>

        {feedback && (
          <div role="status" className={`mt-4 text-sm border px-3 py-2 ${feedback.ok ? "border-[var(--ok)] text-[var(--ok)]" : "border-[var(--danger)] text-[var(--danger)]"}`}>
            {feedback.message}
          </div>
        )}
      </section>

      <section className="bg-white border border-[var(--line)]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--line)]">
          <h2 className="text-sm font-semibold text-[var(--ink)]">Inspection assignments</h2>
          <button type="button" onClick={loadAssignments} disabled={loading} className="inline-flex items-center gap-1 text-sm text-[var(--accent)] disabled:opacity-60" title="Refresh assignments">
            <RefreshCw size={15} aria-hidden="true" /> Refresh
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-[var(--line)] text-left text-[var(--ink-soft)]"><th className="px-4 py-2 font-medium">Institute</th><th className="px-4 py-2 font-medium">Officer</th><th className="px-4 py-2 font-medium">Due</th><th className="px-4 py-2 font-medium">Status</th></tr></thead>
            <tbody>
              {loading && <tr><td colSpan="4" className="px-4 py-4 text-[var(--ink-soft)]">Loading…</td></tr>}
              {!loading && assignments.length === 0 && <tr><td colSpan="4" className="px-4 py-4 text-[var(--ink-soft)]">No assignments yet.</td></tr>}
              {!loading && assignments.map((assignment) => (
                <tr key={assignment.id} className="border-b border-[var(--line)] last:border-0">
                  <td className="px-4 py-2.5">{assignment.institute_name}</td>
                  <td className="px-4 py-2.5">{assignment.officer_name}</td>
                  <td className="px-4 py-2.5">{assignment.scheduled_at ? new Date(assignment.scheduled_at).toLocaleString() : assignment.due_date}</td>
                  <td className="px-4 py-2.5">{assignment.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default function Manage() {
  const [tab, setTab] = useState("Schemes");

  return (
    <div className="p-8 space-y-4">
      <header>
        <h1 className="text-lg font-semibold text-[var(--ink)]">Manage</h1>
        <p className="text-sm text-[var(--ink-soft)]">
          Schemes, NGOs, projects, staff, and beneficiaries — everything that used to require /admin/.
        </p>
      </header>

      <div className="flex gap-1 border-b border-[var(--line)]">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              tab === t ? "border-[var(--accent)] text-[var(--accent)]" : "border-transparent text-[var(--ink-soft)]"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Schemes" && <SchemesTab />}
      {tab === "NGOs" && <NGOsTab />}
      {tab === "Projects" && <ProjectsTab />}
      {tab === "Staff" && <StaffTab />}
      {tab === "Beneficiaries" && <BeneficiariesTab />}
      {tab === "Inspections" && <InspectionsTab />}
    </div>
  );
}

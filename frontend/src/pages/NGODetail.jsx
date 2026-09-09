import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { client } from "../api/client";
import StatCard from "../components/StatCard";
import ProjectMap from "../components/ProjectMap";
import AIAlertsPanel from "../components/AIAlertsPanel";

const STATUS_STYLE = {
  PENDING: "text-[var(--warn)]",
  ACCEPTED: "text-[var(--accent)]",
  IN_PROGRESS: "text-[var(--accent)]",
  OVERDUE: "text-[var(--danger)]",
  SUBMITTED: "text-[var(--ok)]",
  UNDER_REVIEW: "text-[var(--warn)]",
  CHANGES_REQUIRED: "text-[var(--danger)]",
  APPROVED: "text-[var(--ok)]",
  COMPLETED: "text-[var(--ok)]",
  NO_INSPECTION: "text-[var(--ink-soft)]",
};

const CAMERA_STATUS_STYLE = {
  ONLINE: "text-[var(--ok)]",
  OFFLINE: "text-[var(--danger)]",
  MAINTENANCE: "text-[var(--warn)]",
  DISABLED: "text-[var(--ink-soft)]",
};

/**
 * NGO detail page — the NGO-side equivalent of InstituteDetail.jsx.
 *
 * FLATTENED ARCHITECTURE: an NGO doesn't own Institutes/Projects directly
 * (Scheme is the only thing they share — see ARCHITECTURE_FIX.md), so
 * "monitoring this NGO" means every Institute/Project under the same
 * Scheme(s) it belongs to. That aggregation — including the same
 * inspection-history and CCTV visibility a single Institute's page has —
 * is computed server-side by NGOViewSet.monitoring()
 * (apps/registry/views.py) so this page doesn't re-derive scoping logic
 * that already exists for the NGO portal.
 *
 * Deliberately read-only/aggregate here (no "Assign Inspection", no
 * "+ Add camera", no live stream) — those actions stay on the single
 * Institute page where "which site does this apply to" is unambiguous.
 * Each row below links straight into that institute's own detail page for
 * anything that needs an action taken.
 */
export default function NGODetail() {
  const { id } = useParams();
  const [ngo, setNgo] = useState(null);
  const [summary, setSummary] = useState(null);
  const [institutes, setInstitutes] = useState([]);
  const [projects, setProjects] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [cameras, setCameras] = useState([]);
  const [schemes, setSchemes] = useState([]);
  const [notFound, setNotFound] = useState(false);
  const [loading, setLoading] = useState(true);

  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);

  const [alerts, setAlerts] = useState([]);
  const [alertsLoading, setAlertsLoading] = useState(true);

  function loadMonitoring() {
    setLoading(true);
    client.get(`/registry/ngos/${id}/monitoring/`)
      .then(({ data }) => {
        setNgo(data.ngo);
        setSummary(data.summary);
        setInstitutes(data.institutes);
        setProjects(data.projects);
        setAssignments(data.assignments);
        setCameras(data.cameras);
      })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }

  function loadAlerts(instituteIds) {
    setAlertsLoading(true);
    client.get("/analytics/alerts/?status=open")
      .then(({ data }) => setAlerts(data.filter((a) => instituteIds.includes(a.institute))))
      .catch(() => setAlerts([]))
      .finally(() => setAlertsLoading(false));
  }

  useEffect(() => {
    loadMonitoring();
    client.get("/registry/schemes/").then(({ data }) => setSchemes(data));
  }, [id]);

  useEffect(() => {
    if (ngo) {
      loadAlerts(institutes.map((i) => i.id));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [institutes, ngo]);

  function startEdit() {
    setForm({
      name: ngo.name,
      scheme: ngo.scheme,
      registration_number: ngo.registration_number,
      contact_person: ngo.contact_person || "",
      contact_phone: ngo.contact_phone || "",
      contact_email: ngo.contact_email || "",
      admin_user: ngo.admin_user ?? "",
    });
    setEditing(true);
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...form, admin_user: form.admin_user === "" ? null : form.admin_user };
      await client.patch(`/registry/ngos/${id}/`, payload);
      setEditing(false);
      loadMonitoring();
    } finally {
      setSaving(false);
    }
  }

  if (notFound) {
    return (
      <div className="p-8">
        <p className="text-sm text-[var(--ink-soft)]">NGO not found.</p>
        <Link to="/ngos" className="text-[var(--accent)] underline text-sm">Back to list</Link>
      </div>
    );
  }

  if (loading || !ngo) {
    return <div className="p-8 text-sm text-[var(--ink-soft)]">Loading…</div>;
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link to="/ngos" className="text-xs text-[var(--accent)] underline">← Back to NGOs</Link>
          <h1 className="text-lg font-semibold text-[var(--ink)] mt-2">{ngo.name}</h1>
          <p className="text-sm text-[var(--ink-soft)]">
            {ngo.scheme_name} · Reg. No. {ngo.registration_number}
          </p>
        </div>
        <button onClick={startEdit}
          className="border border-[var(--ink)] text-[var(--ink)] text-sm font-medium px-4 py-2 hover:bg-[var(--ink)] hover:text-white transition-colors">
          Edit NGO
        </button>
      </div>

      {editing && (
        <form onSubmit={handleSave} className="bg-white border border-[var(--line)] p-5 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <label className="space-y-1">
            <span className="text-[var(--ink-soft)]">Name</span>
            <input required className="w-full border border-[var(--line)] px-3 py-2"
              value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </label>
          <label className="space-y-1">
            <span className="text-[var(--ink-soft)]">Scheme</span>
            <select required className="w-full border border-[var(--line)] px-3 py-2 bg-white"
              value={form.scheme} onChange={(e) => setForm({ ...form, scheme: e.target.value })}>
              {schemes.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>
          <label className="space-y-1">
            <span className="text-[var(--ink-soft)]">Registration number</span>
            <input required className="w-full border border-[var(--line)] px-3 py-2"
              value={form.registration_number} onChange={(e) => setForm({ ...form, registration_number: e.target.value })} />
          </label>
          <label className="space-y-1">
            <span className="text-[var(--ink-soft)]">Admin user ID</span>
            <input type="number" className="w-full border border-[var(--line)] px-3 py-2"
              value={form.admin_user} onChange={(e) => setForm({ ...form, admin_user: e.target.value })} />
          </label>
          <label className="space-y-1">
            <span className="text-[var(--ink-soft)]">Contact person</span>
            <input className="w-full border border-[var(--line)] px-3 py-2"
              value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} />
          </label>
          <label className="space-y-1">
            <span className="text-[var(--ink-soft)]">Contact phone</span>
            <input className="w-full border border-[var(--line)] px-3 py-2"
              value={form.contact_phone} onChange={(e) => setForm({ ...form, contact_phone: e.target.value })} />
          </label>
          <label className="md:col-span-2 space-y-1">
            <span className="text-[var(--ink-soft)]">Contact email</span>
            <input type="email" className="w-full border border-[var(--line)] px-3 py-2"
              value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} />
          </label>
          <div className="md:col-span-2 flex gap-2">
            <button type="submit" disabled={saving} className="bg-[var(--ink)] text-white px-4 py-2 disabled:opacity-60">
              {saving ? "Saving…" : "Save changes"}
            </button>
            <button type="button" onClick={() => setEditing(false)} className="border border-[var(--line)] px-4 py-2">
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Institutes" value={summary.total_institutes} />
        <StatCard label="Active projects" value={summary.active_projects} />
        <StatCard label="High risk (AI)" value={summary.high_risk_institutes} accent="var(--danger)" />
        <StatCard label="Open AI alerts" value={summary.open_ai_alerts} accent="var(--danger)" />
        <StatCard label="Pending inspections" value={summary.pending_inspections} accent="var(--warn)" />
        <StatCard label="Overdue" value={summary.overdue_inspections} accent="var(--danger)" />
        <StatCard label="Submitted" value={summary.submitted_inspections} accent="var(--ok)" />
        <StatCard label="Cameras online" value={`${summary.cameras_online}/${summary.total_cameras}`} accent="var(--ok)" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-white border border-[var(--line)] h-[420px]">
          <ProjectMap institutes={institutes} />
        </div>
        <AIAlertsPanel alerts={alerts} loading={alertsLoading} onChanged={() => loadAlerts(institutes.map((i) => i.id))} />
      </div>

      <section className="bg-white border border-[var(--line)]">
        <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">
          Institutes under this Scheme ({institutes.length})
        </div>
        <ul className="divide-y divide-[var(--line)]">
          {institutes.length === 0 && (
            <li className="px-4 py-3 text-sm text-[var(--ink-soft)]">No institutes under this NGO's scheme yet.</li>
          )}
          {institutes.map((inst) => (
            <li key={inst.id} className="px-4 py-3 text-sm flex items-center justify-between">
              <div>
                <div className="font-medium">{inst.name}</div>
                <div className="text-xs text-[var(--ink-soft)]">{inst.district}, {inst.state}</div>
              </div>
              <span className="flex items-center gap-3">
                {inst.latest_risk_severity && (
                  <span className="text-xs font-medium text-[var(--ink-soft)]">
                    {inst.latest_risk_score}/100 — {inst.latest_risk_severity}
                  </span>
                )}
                <span className={`text-xs font-medium ${STATUS_STYLE[inst.latest_inspection_status] || ""}`}>
                  {inst.latest_inspection_status}
                </span>
                <Link to={`/institutes/${inst.id}`} className="text-[var(--accent)] underline">View</Link>
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="bg-white border border-[var(--line)]">
        <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">
          Projects under this Scheme ({projects.length})
        </div>
        <ul className="divide-y divide-[var(--line)]">
          {projects.length === 0 && (
            <li className="px-4 py-3 text-sm text-[var(--ink-soft)]">No projects under this NGO's scheme yet.</li>
          )}
          {projects.map((p) => (
            <li key={p.id} className="px-4 py-3 text-sm flex justify-between">
              <span>{p.name}</span>
              <span className={p.is_active ? "text-[var(--ok)]" : "text-[var(--ink-soft)]"}>
                {p.is_active ? "Active" : "Inactive"}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="bg-white border border-[var(--line)]">
        <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">
          Inspection history — all institutes under this NGO ({assignments.length})
        </div>
        <ul className="divide-y divide-[var(--line)] max-h-96 overflow-y-auto">
          {assignments.length === 0 && (
            <li className="px-4 py-3 text-sm text-[var(--ink-soft)]">No inspections assigned yet under this NGO's institutes.</li>
          )}
          {assignments.map((a) => (
            <li key={a.id} className="px-4 py-3 text-sm flex justify-between items-center">
              <div>
                <div>
                  <Link to={`/institutes/${a.institute}`} className="text-[var(--accent)] underline font-medium">
                    {a.institute_name}
                  </Link>
                  <span className="text-[var(--ink-soft)]"> — {a.template_name}</span>
                </div>
                <div className="text-xs text-[var(--ink-soft)]">{a.officer_name} · due {a.due_date}</div>
              </div>
              <span className="flex items-center gap-3 shrink-0">
                <span className={`text-xs font-medium ${STATUS_STYLE[a.status] || ""}`}>{a.status}</span>
                {a.has_report && (
                  <Link to={`/institutes/${a.institute}/reports/${a.id}`} className="text-xs text-[var(--accent)] underline">
                    View report
                  </Link>
                )}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="bg-white border border-[var(--line)]">
        <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">
          CCTV surveillance — all institutes under this NGO ({cameras.length})
        </div>
        <ul className="divide-y divide-[var(--line)] max-h-96 overflow-y-auto">
          {cameras.length === 0 && (
            <li className="px-4 py-3 text-sm text-[var(--ink-soft)]">No cameras registered under this NGO's institutes yet.</li>
          )}
          {cameras.map((cam) => (
            <li key={cam.id} className="px-4 py-3 text-sm flex justify-between items-center">
              <div>
                <div className="font-medium">{cam.name}</div>
                <Link to={`/institutes/${cam.institute}`} className="text-xs text-[var(--accent)] underline">
                  {cam.institute_name}
                </Link>
              </div>
              <span className="flex items-center gap-3">
                {cam.offline_hours > 48 && (
                  <span className="text-xs font-medium text-[var(--danger)]">DOWNTIME &gt; 48h</span>
                )}
                <span className={`text-xs font-medium ${CAMERA_STATUS_STYLE[cam.status] || ""}`}>
                  {cam.status}
                </span>
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
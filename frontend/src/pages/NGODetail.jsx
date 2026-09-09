import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Video, X } from "lucide-react";
import { client, initiateSurpriseVC } from "../api/client";
import StatCard from "../components/StatCard";
import ProjectMap from "../components/ProjectMap";
import AIAlertsPanel from "../components/AIAlertsPanel";
import CctvPanel from "../components/CctvPanel";
import VCSessionPanel from "../components/VCSessionPanel";
import useAlertsSocket from "../hooks/useAlertsSocket";

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
 * IMPORTANT — NGO and Institute are independent entities. An NGO does NOT
 * own institutes (there is no Institute.ngo field — see
 * ARCHITECTURE_FIX.md). The only thing connecting them is that both
 * reference the same Scheme. Every "institutes" list/section on this page
 * really means "institutes registered under this NGO's Scheme."
 *
 * On InstituteDetail.jsx, "Assign Inspection", "Initiate Surprise VC",
 * "+ Add camera", and the "Start VC" form are all permanent page chrome —
 * they show up even when there are zero cameras or the institute has
 * never been inspected, because they act on ONE known institute (the one
 * in the URL). This page acts on a *Scheme* that can have many institutes
 * (or, as with a freshly-approved NGO, zero), so the same actions live
 * here as permanent sections too, driven by an institute picker — they
 * never disappear just because the list happens to be empty right now.
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

  // Which institute (under this NGO's Scheme) the action bar / CCTV panel /
  // Video consultations panel are currently pointed at.
  const [selectedInstituteId, setSelectedInstituteId] = useState(null);

  // "Assign Inspection" (top action bar)
  const [assigning, setAssigning] = useState(false);
  const [assignResult, setAssignResult] = useState(null);

  // "Initiate Surprise VC" (top action bar) — mirrors InstituteDetail.jsx
  const [vcRoom, setVcRoom] = useState(null);
  const [vcAlert, setVcAlert] = useState(null);

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

  // Keep the institute picker pointed at a real institute: default to the
  // first one once the list loads, and fall back cleanly if the
  // previously-selected institute disappears (e.g. deactivated).
  useEffect(() => {
    if (institutes.length === 0) {
      setSelectedInstituteId(null);
      return;
    }
    if (!institutes.some((inst) => inst.id === selectedInstituteId)) {
      setSelectedInstituteId(institutes[0].id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [institutes]);

  useAlertsSocket((event) => {
    if (event.type === "SURPRISE_VC_ALERT" && String(event.institute_id) === String(selectedInstituteId)) {
      setVcAlert(event);
    }
  }, selectedInstituteId);

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

  async function handleAssign() {
    if (!selectedInstituteId) return;
    setAssigning(true);
    setAssignResult(null);
    try {
      const { data } = await client.post("/inspections/assignments/auto-assign/", { institute: selectedInstituteId });
      setAssignResult({ ok: true, data: data.assignment, candidates: data.candidates });
      loadMonitoring();
    } catch (err) {
      setAssignResult({ ok: false, message: err.response?.data?.detail || "Could not assign an inspection." });
    } finally {
      setAssigning(false);
    }
  }

  async function handleInitiateVC() {
    if (!selectedInstituteId) return;
    setVcAlert(null);
    try {
      const { data } = await initiateSurpriseVC(selectedInstituteId);
      await openVC(data.session_id, data.room_name);
    } catch (err) {
      setVcAlert({ error: err.response?.data?.detail || "Could not initiate the surprise video call." });
    }
  }

  async function openVC(sessionId, fallbackRoom) {
    if (sessionId) {
      const { data } = await client.post(`/consultations/sessions/${sessionId}/join/`);
      setVcRoom(data.room_name);
      return;
    }
    setVcRoom(fallbackRoom);
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

  const selectedInstitute = institutes.find((inst) => inst.id === selectedInstituteId) || null;
  const hasInstitutes = institutes.length > 0;

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <Link to="/ngos" className="text-xs text-[var(--accent)] underline">← Back to NGOs</Link>
          <h1 className="text-lg font-semibold text-[var(--ink)] mt-2">{ngo.name}</h1>
          <p className="text-sm text-[var(--ink-soft)]">
            {ngo.scheme_name} · Reg. No. {ngo.registration_number}
          </p>
          <p className="text-xs text-[var(--ink-soft)] mt-2 max-w-2xl">
            Note: an NGO does not own institutes directly — an NGO and an Institute are separate
            entities that both belong to the same Scheme. Everything below is every institute
            and project registered under <strong>{ngo.scheme_name}</strong> (this NGO's Scheme),
            not property of this NGO itself.
          </p>
        </div>
        <button onClick={startEdit}
          className="shrink-0 border border-[var(--ink)] text-[var(--ink)] text-sm font-medium px-4 py-2 hover:bg-[var(--ink)] hover:text-white transition-colors">
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

      {/* ------------------------------------------------------------------
          Action bar — permanent, same as InstituteDetail's header buttons.
          The only difference is a Scheme can hold multiple institutes, so
          you pick which one "Assign Inspection" / "Initiate Surprise VC"
          apply to. Disabled (not hidden) when this Scheme has no institutes.
      ------------------------------------------------------------------- */}
      <section className="bg-white border border-[var(--line)] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-[var(--ink-soft)]">Acting on institute:</span>
            <select
              value={selectedInstituteId ?? ""}
              onChange={(e) => setSelectedInstituteId(e.target.value ? Number(e.target.value) : null)}
              disabled={!hasInstitutes}
              className="border border-[var(--line)] px-3 py-2 bg-white text-[var(--ink)] outline-none disabled:opacity-50 min-w-[220px]"
            >
              {!hasInstitutes && <option value="">No institutes under this Scheme</option>}
              {institutes.map((inst) => (
                <option key={inst.id} value={inst.id}>{inst.name}</option>
              ))}
            </select>
            {selectedInstitute && (
              <Link to={`/institutes/${selectedInstitute.id}`} className="text-xs text-[var(--accent)] underline">
                Open full institute page
              </Link>
            )}
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleAssign}
              disabled={!hasInstitutes || assigning}
              className="bg-[var(--ink)] text-white text-sm font-medium px-4 py-2 hover:bg-[var(--accent)] transition-colors disabled:opacity-50"
            >
              {assigning ? "Assigning…" : "Assign Inspection"}
            </button>
            <button
              onClick={handleInitiateVC}
              disabled={!hasInstitutes}
              className="inline-flex items-center gap-2 bg-[var(--danger)] text-white text-sm font-medium px-4 py-2 hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              <Video size={16} aria-hidden="true" />
              Initiate Surprise VC
            </button>
          </div>
        </div>

        {!hasInstitutes && (
          <p className="text-xs text-[var(--ink-soft)] mt-3">
            This Scheme has no institutes registered yet, so there's nothing to assign an
            inspection to or start a video call with. Register an institute under{" "}
            <strong>{ngo.scheme_name}</strong> (Institutes page or Manage) and it will appear
            in this picker automatically.
          </p>
        )}

        {assignResult && (
          <div className={`mt-3 text-sm px-4 py-2 border ${
            assignResult.ok
              ? "border-[var(--ok)] text-[var(--ok)] bg-[var(--ok)]/5"
              : "border-[var(--danger)] text-[var(--danger)] bg-[var(--danger)]/5"
          }`}>
            {assignResult.ok ? (
              <div>
                <div>Assigned to <strong>{assignResult.data.officer_name}</strong> — due {assignResult.data.due_date}.</div>
                <div className="mt-1 text-xs text-[var(--ink-soft)]">
                  {assignResult.candidates.map((c) => `${c.officer_name} → ${c.distance_km ?? "?"} km (workload ${c.workload})`).join("  ·  ")}
                </div>
              </div>
            ) : assignResult.message}
          </div>
        )}

        {vcAlert && (
          <div role="alert" className={`mt-3 flex items-center justify-between gap-4 border px-4 py-3 text-sm ${vcAlert.error ? "border-[var(--danger)] text-[var(--danger)]" : "border-[var(--warn)] bg-[var(--warn)]/10 text-[var(--ink)]"}`}>
            <span>{vcAlert.error || "A surprise video call has been initiated for this institute."}</span>
            {!vcAlert.error && (
              <button
                onClick={() => {
                  openVC(vcAlert.session_id, vcAlert.room_name)
                    .then(() => setVcAlert(null))
                    .catch(() => setVcAlert({ error: "You are not an invited participant in this VC." }));
                }}
                className="shrink-0 bg-[var(--ink)] text-white px-3 py-1.5 font-medium"
              >
                Join Call Now
              </button>
            )}
            <button onClick={() => setVcAlert(null)} aria-label="Dismiss video call notification" className="shrink-0 text-[var(--ink-soft)]">
              <X size={17} />
            </button>
          </div>
        )}

        {vcRoom && (
          <section className="mt-3 bg-black border border-[var(--line)]">
            <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-[var(--line)] text-sm font-medium">
              <span>Surprise video call</span>
              <button onClick={() => setVcRoom(null)} className="text-[var(--accent)] underline">Close call</button>
            </div>
            <iframe
              title="Surprise video call"
              src={`https://meet.jit.si/${encodeURIComponent(vcRoom)}`}
              allow="camera; microphone; fullscreen; display-capture"
              className="w-full aspect-video"
            />
          </section>
        )}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-white border border-[var(--line)] h-[420px]">
          <ProjectMap institutes={institutes} />
        </div>
        <AIAlertsPanel alerts={alerts} loading={alertsLoading} onChanged={() => loadAlerts(institutes.map((i) => i.id))} />
      </div>

      {/* ------------------------------------------------------------------
          CCTV surveillance — permanent section, same as InstituteDetail's
          CctvPanel. Always mounted; it just points at whichever institute
          is selected above, and explains itself when there's none yet.
      ------------------------------------------------------------------- */}
      <section className="bg-white border border-[var(--line)]">
        <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">
          CCTV surveillance{selectedInstitute ? ` — ${selectedInstitute.name}` : ""}
        </div>
        {hasInstitutes ? (
          <CctvPanel instituteId={selectedInstituteId} />
        ) : (
          <p className="px-4 py-3 text-sm text-[var(--ink-soft)]">
            No institutes under this Scheme yet — select one above once one is registered to
            add and manage its cameras here.
          </p>
        )}
      </section>

      {/* ------------------------------------------------------------------
          Video consultations — permanent section, same as InstituteDetail's
          VCSessionPanel (Start VC form + session history).
      ------------------------------------------------------------------- */}
      <section>
        {hasInstitutes ? (
          <VCSessionPanel instituteId={selectedInstituteId} />
        ) : (
          <div className="bg-white border border-[var(--line)]">
            <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">Video consultations</div>
            <p className="px-4 py-3 text-sm text-[var(--ink-soft)]">
              No institutes under this Scheme yet — select one above once one is registered to
              start or review video consultations here.
            </p>
          </div>
        )}
      </section>

      <section className="bg-white border border-[var(--line)]">
        <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">
          Institutes under this Scheme ({institutes.length})
        </div>
        <ul className="divide-y divide-[var(--line)]">
          {institutes.length === 0 && (
            <li className="px-4 py-3 text-sm text-[var(--ink-soft)]">No institutes under this Scheme yet.</li>
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
                <button
                  onClick={() => setSelectedInstituteId(inst.id)}
                  className={`text-xs underline ${selectedInstituteId === inst.id ? "text-[var(--ink-soft)]" : "text-[var(--accent)]"}`}
                  disabled={selectedInstituteId === inst.id}
                >
                  {selectedInstituteId === inst.id ? "Selected above" : "Manage above"}
                </button>
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
            <li className="px-4 py-3 text-sm text-[var(--ink-soft)]">No projects under this Scheme yet.</li>
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
          Inspection history — institutes under this Scheme ({assignments.length})
        </div>
        <ul className="divide-y divide-[var(--line)] max-h-96 overflow-y-auto">
          {assignments.length === 0 && (
            <li className="px-4 py-3 text-sm text-[var(--ink-soft)]">
              No inspections assigned yet across institutes under this Scheme.
            </li>
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
          All cameras — institutes under this Scheme ({cameras.length})
        </div>
        <ul className="divide-y divide-[var(--line)] max-h-96 overflow-y-auto">
          {cameras.length === 0 && (
            <li className="px-4 py-3 text-sm text-[var(--ink-soft)]">
              No cameras registered yet across institutes under this Scheme.
            </li>
          )}
          {cameras.map((cam) => (
            <li key={cam.id} className="px-4 py-3 text-sm flex justify-between items-center">
              <div>
                <div className="font-medium">{cam.name}</div>
                <button
                  onClick={() => setSelectedInstituteId(cam.institute)}
                  className="text-xs text-[var(--accent)] underline"
                >
                  {cam.institute_name} — manage above
                </button>
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
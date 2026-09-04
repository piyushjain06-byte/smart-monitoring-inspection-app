import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Video, X } from "lucide-react";
import { client, downloadBlob, initiateSurpriseVC } from "../api/client";
import CctvPanel from "../components/CctvPanel";
import RiskTrendChart from "../components/RiskTrendChart";
import useAlertsSocket from "../hooks/useAlertsSocket";

const STATUS_STYLE = {
  PENDING: "text-[var(--warn)]",
  OVERDUE: "text-[var(--danger)]",
  SUBMITTED: "text-[var(--ok)]",
};

const SEVERITY_STYLE = {
  LOW: "text-[var(--ok)]",
  MEDIUM: "text-[var(--warn)]",
  HIGH: "text-[var(--danger)]",
};

const STALE_AFTER_DAYS = 7;

function staleTrendMessage(risk) {
  if (!risk) return null;
  if (risk.last_snapshot_at == null) {
    return "This institute has never been analyzed — click \"Run AI Analysis\" on the dashboard.";
  }
  const days = risk.last_snapshot_age_days;
  if (days >= STALE_AFTER_DAYS) {
    return `Last analyzed ${days} day${days === 1 ? "" : "s"} ago — this score may be out of date. Run AI Analysis on the dashboard to refresh it.`;
  }
  return `Last analyzed ${days === 0 ? "today" : `${days} day${days === 1 ? "" : "s"} ago`}.`;
}

export default function InstituteDetail() {
  const { id } = useParams();
  const [institute, setInstitute] = useState(null);
  const [editingInstitute, setEditingInstitute] = useState(false);
  const [instForm, setInstForm] = useState(null);
  const [savingInst, setSavingInst] = useState(false);
  const [assignments, setAssignments] = useState([]);
  const [notFound, setNotFound] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [assignResult, setAssignResult] = useState(null);
  const [risk, setRisk] = useState(null);
  const [riskLoading, setRiskLoading] = useState(true);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [exportingHistory, setExportingHistory] = useState(false);
  const [vcRoom, setVcRoom] = useState(null);
  const [vcAlert, setVcAlert] = useState(null);

  function loadInstitute() {
    client.get(`/registry/institutes/${id}/`).then(({ data }) => setInstitute(data)).catch(() => setNotFound(true));
  }
  function loadAssignments() {
    client.get(`/inspections/assignments/?institute=${id}`).then(({ data }) => setAssignments(data));
  }
  function loadRisk() {
    setRiskLoading(true);
    client.get(`/analytics/risk/institute/${id}/live/`)
      .then(({ data }) => setRisk(data)).catch(() => setRisk(null)).finally(() => setRiskLoading(false));
  }
  function loadHistory() {
    setHistoryLoading(true);
    client.get(`/analytics/risk/institute/${id}/history/`)
      .then(({ data }) => setHistory(data)).catch(() => setHistory([])).finally(() => setHistoryLoading(false));
  }

  useEffect(() => {
    loadInstitute();
    loadAssignments();
    loadRisk();
    loadHistory();
  }, [id]);

  useAlertsSocket((event) => {
    if (event.type === "SURPRISE_VC_ALERT" && String(event.institute_id) === String(id)) {
      setVcAlert(event);
    }
  }, id);

  function startEditInstitute() {
    setInstForm({
      name: institute.name,
      address: institute.address || "",
      state: institute.state,
      district: institute.district,
      latitude: institute.latitude ?? "",
      longitude: institute.longitude ?? "",
      incharge: institute.incharge ?? "",
      is_active: institute.is_active,
    });
    setEditingInstitute(true);
  }

  async function handleSaveInstitute(e) {
    e.preventDefault();
    setSavingInst(true);
    try {
      const payload = {
        ...instForm,
        latitude: instForm.latitude === "" ? null : parseFloat(instForm.latitude),
        longitude: instForm.longitude === "" ? null : parseFloat(instForm.longitude),
        incharge: instForm.incharge === "" ? null : instForm.incharge,
      };
      await client.patch(`/registry/institutes/${id}/`, payload);
      setEditingInstitute(false);
      loadInstitute();
    } finally {
      setSavingInst(false);
    }
  }

  async function handleAssign() {
    setAssigning(true);
    setAssignResult(null);
    try {
      const { data } = await client.post("/inspections/assignments/auto-assign/", { institute: id });
      setAssignResult({ ok: true, data: data.assignment, candidates: data.candidates });
      loadAssignments();
    } catch (err) {
      setAssignResult({ ok: false, message: err.response?.data?.detail || "Could not assign an inspection." });
    } finally {
      setAssigning(false);
    }
  }

  async function handleInitiateVC() {
    setVcAlert(null);
    try {
      const { data } = await initiateSurpriseVC(id);
      setVcRoom(data.room_name);
    } catch (err) {
      setVcAlert({ error: err.response?.data?.detail || "Could not initiate the surprise video call." });
    }
  }

  async function handleDownloadRiskPdf() {
    try {
      const res = await client.get(`/analytics/risk/institute/${id}/pdf/`, { responseType: "blob" });
      const contentType = res.headers["content-type"] || "";
      const isPdf = contentType.includes("pdf");
      const blob = new Blob([res.data], { type: isPdf ? "application/pdf" : "text/html" });
      const url = window.URL.createObjectURL(blob);
      if (isPdf) {
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", `risk-report-${id}.pdf`);
        document.body.appendChild(link);
        link.click();
        link.remove();
      } else {
        window.open(url, "_blank");
      }
      window.URL.revokeObjectURL(url);
    } catch {
      // Silently ignore — the panel already shows risk data on-screen either way.
    }
  }

  async function handleExportHistory() {
    setExportingHistory(true);
    try {
      await downloadBlob(`/inspections/assignments/export-csv/?institute=${id}`, `inspections-institute-${id}.csv`);
    } finally {
      setExportingHistory(false);
    }
  }

  if (notFound) {
    return (
      <div className="p-8">
        <p className="text-sm text-[var(--ink-soft)]">Institute not found.</p>
        <Link to="/institutes" className="text-[var(--accent)] underline text-sm">Back to list</Link>
      </div>
    );
  }

  if (!institute) {
    return <div className="p-8 text-sm text-[var(--ink-soft)]">Loading…</div>;
  }

  const staleMessage = staleTrendMessage(risk);
  const isStale = risk && risk.last_snapshot_age_days != null && risk.last_snapshot_age_days >= STALE_AFTER_DAYS;
  const neverAnalyzed = risk && risk.last_snapshot_at == null;

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link to="/institutes" className="text-xs text-[var(--accent)] underline">← Back to institutes</Link>
          <h1 className="text-lg font-semibold text-[var(--ink)] mt-2">{institute.name}</h1>
          {/* FLATTENED ARCHITECTURE: Institute -> Scheme only now (no NGO to show). */}
          <p className="text-sm text-[var(--ink-soft)]">
            {institute.scheme_name} · {institute.district}, {institute.state}
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button onClick={startEditInstitute}
            className="border border-[var(--ink)] text-[var(--ink)] text-sm font-medium px-4 py-2 hover:bg-[var(--ink)] hover:text-white transition-colors">
            Edit Institute
          </button>
          <button onClick={handleAssign} disabled={assigning}
            className="bg-[var(--ink)] text-white text-sm font-medium px-4 py-2 hover:bg-[var(--accent)] transition-colors disabled:opacity-60">
            {assigning ? "Assigning…" : "Assign Inspection"}
          </button>
          <button onClick={handleInitiateVC}
            className="inline-flex items-center gap-2 bg-[var(--danger)] text-white text-sm font-medium px-4 py-2 hover:opacity-90 transition-opacity">
            <Video size={16} aria-hidden="true" />
            Initiate Surprise VC
          </button>
        </div>
      </div>

      {vcAlert && (
        <div role="alert" className={`flex items-center justify-between gap-4 border px-4 py-3 text-sm ${vcAlert.error ? "border-[var(--danger)] text-[var(--danger)]" : "border-[var(--warn)] bg-[var(--warn)]/10 text-[var(--ink)]"}`}>
          <span>{vcAlert.error || "A surprise video call has been initiated for this institute."}</span>
          {!vcAlert.error && <button onClick={() => { setVcRoom(vcAlert.room_name); setVcAlert(null); }} className="shrink-0 bg-[var(--ink)] text-white px-3 py-1.5 font-medium">Join Call Now</button>}
          <button onClick={() => setVcAlert(null)} aria-label="Dismiss video call notification" className="shrink-0 text-[var(--ink-soft)]"><X size={17} /></button>
        </div>
      )}

      {vcRoom && (
        <section className="bg-black border border-[var(--line)]">
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

      {editingInstitute && (
        <form onSubmit={handleSaveInstitute} className="bg-white border border-[var(--line)] p-5 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <label className="space-y-1">
            <span className="text-[var(--ink-soft)]">Name</span>
            <input required className="w-full border border-[var(--line)] px-3 py-2"
              value={instForm.name} onChange={(e) => setInstForm({ ...instForm, name: e.target.value })} />
          </label>
          <label className="space-y-1">
            <span className="text-[var(--ink-soft)]">Incharge user ID</span>
            <input type="number" className="w-full border border-[var(--line)] px-3 py-2"
              value={instForm.incharge} onChange={(e) => setInstForm({ ...instForm, incharge: e.target.value })} />
          </label>
          <label className="md:col-span-2 space-y-1">
            <span className="text-[var(--ink-soft)]">Address</span>
            <input className="w-full border border-[var(--line)] px-3 py-2"
              value={instForm.address} onChange={(e) => setInstForm({ ...instForm, address: e.target.value })} />
          </label>
          <label className="space-y-1">
            <span className="text-[var(--ink-soft)]">State</span>
            <input required className="w-full border border-[var(--line)] px-3 py-2"
              value={instForm.state} onChange={(e) => setInstForm({ ...instForm, state: e.target.value })} />
          </label>
          <label className="space-y-1">
            <span className="text-[var(--ink-soft)]">District</span>
            <input required className="w-full border border-[var(--line)] px-3 py-2"
              value={instForm.district} onChange={(e) => setInstForm({ ...instForm, district: e.target.value })} />
          </label>
          <label className="space-y-1">
            <span className="text-[var(--ink-soft)]">Latitude</span>
            <input className="w-full border border-[var(--line)] px-3 py-2"
              value={instForm.latitude} onChange={(e) => setInstForm({ ...instForm, latitude: e.target.value })} />
          </label>
          <label className="space-y-1">
            <span className="text-[var(--ink-soft)]">Longitude</span>
            <input className="w-full border border-[var(--line)] px-3 py-2"
              value={instForm.longitude} onChange={(e) => setInstForm({ ...instForm, longitude: e.target.value })} />
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={instForm.is_active}
              onChange={(e) => setInstForm({ ...instForm, is_active: e.target.checked })} />
            <span className="text-[var(--ink-soft)]">Active</span>
          </label>
          <div className="md:col-span-2 flex gap-2">
            <button type="submit" disabled={savingInst}
              className="bg-[var(--ink)] text-white px-4 py-2 disabled:opacity-60">
              {savingInst ? "Saving…" : "Save changes"}
            </button>
            <button type="button" onClick={() => setEditingInstitute(false)} className="border border-[var(--line)] px-4 py-2">
              Cancel
            </button>
          </div>
        </form>
      )}

      {assignResult && (
        <div className={`text-sm px-4 py-2 border ${
          assignResult.ok ? "border-[var(--ok)] text-[var(--ok)] bg-[var(--ok)]/5" : "border-[var(--danger)] text-[var(--danger)] bg-[var(--danger)]/5"
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

      {/*
        FLATTENED ARCHITECTURE: Projects no longer belong to a specific
        Institute (Project -> Scheme directly now), so the old "Projects"
        panel that lived here has been removed. Manage projects from
        /manage -> Projects, scoped by Scheme.
      */}
      <section className="bg-white border border-[var(--line)]">
        <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium flex items-center justify-between">
          <span>Inspection history</span>
          <button onClick={handleExportHistory} disabled={exportingHistory} className="text-xs text-[var(--accent)] underline disabled:opacity-50">
            {exportingHistory ? "Exporting…" : "Export CSV"}
          </button>
        </div>
        <ul className="divide-y divide-[var(--line)]">
          {assignments.length === 0 && (
            <li className="px-4 py-3 text-sm text-[var(--ink-soft)]">No inspections assigned yet.</li>
          )}
          {assignments.map((a) => (
            <li key={a.id} className="px-4 py-3 text-sm flex justify-between items-center">
              <div>
                <div>{a.template_name}</div>
                <div className="text-xs text-[var(--ink-soft)]">{a.officer_name} · due {a.due_date}</div>
              </div>
              <span className="flex items-center gap-3">
                <span className={`text-xs font-medium ${STATUS_STYLE[a.status] || ""}`}>{a.status}</span>
                {a.has_report && (
                  <Link to={`/institutes/${id}/reports/${a.id}`} className="text-xs text-[var(--accent)] underline">
                    View report
                  </Link>
                )}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="bg-white border border-[var(--line)]">
        <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium flex items-center justify-between">
          <span>AI risk assessment</span>
          <div className="flex items-center gap-3">
            {risk && (
              <span className={`text-sm font-semibold ${SEVERITY_STYLE[risk.severity] || ""}`}>
                {risk.score}/100 — {risk.severity}
              </span>
            )}
            <button onClick={handleDownloadRiskPdf} className="text-xs text-[var(--accent)] underline">Download PDF</button>
          </div>
        </div>

        {staleMessage && (
          <div className={`px-4 py-2 text-xs border-b border-[var(--line)] ${
            isStale || neverAnalyzed ? "text-[var(--warn)] bg-[var(--warn)]/5" : "text-[var(--ink-soft)]"
          }`}>
            {staleMessage}
          </div>
        )}

        <div className="p-4 text-sm space-y-3">
          {riskLoading && <p className="text-[var(--ink-soft)]">Computing…</p>}
          {!riskLoading && risk && risk.factors.length === 0 && (
            <p className="text-[var(--ink-soft)]">No risk factors currently triggered for this institute.</p>
          )}
          {!riskLoading && risk && risk.factors.length > 0 && (
            <ul className="space-y-2">
              {risk.factors.map((f) => (
                <li key={f.factor} className="flex justify-between gap-4">
                  <span>{f.detail}</span>
                  <span className="shrink-0 text-[var(--danger)] font-medium">+{f.points}</span>
                </li>
              ))}
            </ul>
          )}
          {!riskLoading && risk?.is_anomaly && (
            <p className="text-xs text-[var(--ink-soft)] border-t border-[var(--line)] pt-2">
              Flagged by the anomaly model (Isolation Forest) as statistically unusual compared to other institutes.
            </p>
          )}
        </div>
      </section>

      <section className="bg-white border border-[var(--line)]">
        <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">Risk score trend</div>
        <div className="p-4">
          {historyLoading && <p className="text-sm text-[var(--ink-soft)]">Loading…</p>}
          {!historyLoading && history.length < 2 && (
            <p className="text-sm text-[var(--ink-soft)]">
              Not enough history yet — each click of "Run AI Analysis" on the dashboard adds one point here.
            </p>
          )}
          {!historyLoading && history.length >= 2 && <RiskTrendChart data={history} />}
        </div>
      </section>

      <CctvPanel instituteId={id} />
    </div>
  );
}

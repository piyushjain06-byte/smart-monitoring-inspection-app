import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { client, downloadBlob } from "../api/client";

const STATUS_STYLE = {
  PENDING: "text-[var(--warn)]",
  OVERDUE: "text-[var(--danger)]",
  SUBMITTED: "text-[var(--ok)]",
  NO_INSPECTION: "text-[var(--ink-soft)]",
};

const STATUS_LABEL = {
  PENDING: "Pending",
  OVERDUE: "Overdue",
  SUBMITTED: "Submitted",
  NO_INSPECTION: "No inspection yet",
};

const BLANK_FORM = {
  name: "", scheme: "", ngo: "", address: "", state: "", district: "",
  latitude: "", longitude: "", incharge: "", is_active: true,
};

export default function Institutes() {
  const [institutes, setInstitutes] = useState([]);
  const [schemes, setSchemes] = useState([]);
  const [ngos, setNgos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(BLANK_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  function load() {
    setLoading(true);
    Promise.all([
      client.get("/registry/institutes/"),
      client.get("/registry/schemes/"),
      client.get("/registry/ngos/"),
    ])
      .then(([i, s, n]) => {
        setInstitutes(i.data);
        setSchemes(s.data);
        setNgos(n.data);
      })
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleExport() {
    setExporting(true);
    setExportError("");
    try {
      await downloadBlob("/registry/institutes/export-csv/", "institutes.csv");
    } catch {
      setExportError("Could not export institutes.");
    } finally {
      setExporting(false);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    setSaving(true);
    setFormError("");
    try {
      const payload = {
        ...form,
        latitude: form.latitude === "" ? null : parseFloat(form.latitude),
        longitude: form.longitude === "" ? null : parseFloat(form.longitude),
        incharge: form.incharge === "" ? null : form.incharge,
      };
      await client.post("/registry/institutes/", payload);
      setShowForm(false);
      setForm(BLANK_FORM);
      load();
    } catch (err) {
      const detail = err.response?.data;
      setFormError(typeof detail === "string" ? detail : JSON.stringify(detail) || "Could not create institute.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="p-8 space-y-4">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold text-[var(--ink)]">Institutes &amp; Projects</h1>
          <p className="text-sm text-[var(--ink-soft)]">
            Every registered institute under the platform's schemes.
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button
            onClick={() => setShowForm((v) => !v)}
            className="bg-[var(--ink)] text-white text-sm font-medium px-4 py-2 hover:bg-[var(--accent)] transition-colors"
          >
            {showForm ? "Cancel" : "+ New Institute"}
          </button>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="border border-[var(--ink)] text-[var(--ink)] text-sm font-medium px-4 py-2 hover:bg-[var(--ink)] hover:text-white transition-colors disabled:opacity-60"
          >
            {exporting ? "Exporting…" : "Export CSV"}
          </button>
        </div>
      </header>

      {exportError && <p className="text-sm text-[var(--danger)]">{exportError}</p>}

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white border border-[var(--line)] p-5 grid grid-cols-1 md:grid-cols-2 gap-3">
          <label className="text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">Name</span>
            <input required className="w-full border border-[var(--line)] px-3 py-2"
              value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </label>
          <label className="text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">Scheme</span>
            <select required className="w-full border border-[var(--line)] px-3 py-2 bg-white"
              value={form.scheme} onChange={(e) => setForm({ ...form, scheme: e.target.value })}>
              <option value="">--</option>
              {schemes.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>
          <label className="text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">NGO</span>
            <select required className="w-full border border-[var(--line)] px-3 py-2 bg-white"
              value={form.ngo} onChange={(e) => setForm({ ...form, ngo: e.target.value })}>
              <option value="">--</option>
              {ngos.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
            </select>
          </label>
          <label className="text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">Incharge user ID (optional — Project Incharge portal login)</span>
            <input type="number" className="w-full border border-[var(--line)] px-3 py-2"
              value={form.incharge} onChange={(e) => setForm({ ...form, incharge: e.target.value })} />
          </label>
          <label className="text-sm space-y-1 md:col-span-2">
            <span className="text-[var(--ink-soft)]">Address</span>
            <input className="w-full border border-[var(--line)] px-3 py-2"
              value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </label>
          <label className="text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">State</span>
            <input required className="w-full border border-[var(--line)] px-3 py-2"
              value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} />
          </label>
          <label className="text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">District</span>
            <input required className="w-full border border-[var(--line)] px-3 py-2"
              value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} />
          </label>
          <label className="text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">Latitude (e.g. 19.0760)</span>
            <input className="w-full border border-[var(--line)] px-3 py-2"
              value={form.latitude} onChange={(e) => setForm({ ...form, latitude: e.target.value })} />
          </label>
          <label className="text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">Longitude (e.g. 72.8777)</span>
            <input className="w-full border border-[var(--line)] px-3 py-2"
              value={form.longitude} onChange={(e) => setForm({ ...form, longitude: e.target.value })} />
          </label>
          <p className="text-xs text-[var(--ink-soft)] md:col-span-2">
            Tip: right-click any point on Google Maps — the top of the menu shows lat/lng to copy.
          </p>

          {formError && <p className="text-sm text-[var(--danger)] md:col-span-2">{formError}</p>}

          <div className="md:col-span-2">
            <button type="submit" disabled={saving}
              className="bg-[var(--ink)] text-white text-sm font-medium px-4 py-2 hover:bg-[var(--accent)] disabled:opacity-60">
              {saving ? "Creating…" : "Create Institute"}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white border border-[var(--line)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--line)] text-left text-[var(--ink-soft)]">
              <th className="px-4 py-2 font-medium">Institute</th>
              <th className="px-4 py-2 font-medium">NGO</th>
              <th className="px-4 py-2 font-medium">District</th>
              <th className="px-4 py-2 font-medium">Inspection</th>
              <th className="px-4 py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td className="px-4 py-4 text-[var(--ink-soft)]" colSpan={5}>Loading…</td></tr>
            )}
            {!loading && institutes.length === 0 && (
              <tr><td className="px-4 py-4 text-[var(--ink-soft)]" colSpan={5}>No institutes registered yet.</td></tr>
            )}
            {institutes.map((inst) => (
              <tr key={inst.id} className="border-b border-[var(--line)] last:border-0">
                <td className="px-4 py-2.5 font-medium">{inst.name}</td>
                <td className="px-4 py-2.5">{inst.ngo_name}</td>
                <td className="px-4 py-2.5">{inst.district}, {inst.state}</td>
                <td className={`px-4 py-2.5 ${STATUS_STYLE[inst.latest_inspection_status] || ""}`}>
                  {STATUS_LABEL[inst.latest_inspection_status] || "—"}
                </td>
                <td className="px-4 py-2.5 text-right">
                  <Link to={`/institutes/${inst.id}`} className="text-[var(--accent)] underline">
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { client } from "../api/client";

const BLANK_FORM = {
  name: "", scheme: "", registration_number: "",
  contact_person: "", contact_phone: "", contact_email: "", admin_user: "",
};

export default function NGOs() {
  const [ngos, setNgos] = useState([]);
  const [schemes, setSchemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(BLANK_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  function load() {
    setLoading(true);
    Promise.all([
      client.get("/registry/ngos/"),
      client.get("/registry/schemes/"),
    ])
      .then(([n, s]) => {
        setNgos(n.data);
        setSchemes(s.data);
      })
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleCreate(e) {
    e.preventDefault();
    setSaving(true);
    setFormError("");
    try {
      const payload = { ...form, admin_user: form.admin_user === "" ? null : form.admin_user };
      await client.post("/registry/ngos/", payload);
      setShowForm(false);
      setForm(BLANK_FORM);
      load();
    } catch (err) {
      const detail = err.response?.data;
      setFormError(typeof detail === "string" ? detail : JSON.stringify(detail) || "Could not create NGO.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(ngo) {
    if (!window.confirm(`Delete "${ngo.name}"? This cannot be undone.`)) return;
    try {
      await client.delete(`/registry/ngos/${ngo.id}/`);
      load();
    } catch {
      window.alert("Could not delete — it may still be referenced elsewhere.");
    }
  }

  return (
    <div className="p-8 space-y-4">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold text-[var(--ink)]">NGOs</h1>
          <p className="text-sm text-[var(--ink-soft)]">
            Every NGO partner registered under the platform's schemes.
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="bg-[var(--ink)] text-white text-sm font-medium px-4 py-2 hover:bg-[var(--accent)] transition-colors"
        >
          {showForm ? "Cancel" : "+ New NGO"}
        </button>
      </header>

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
            <span className="text-[var(--ink-soft)]">Registration number</span>
            <input required className="w-full border border-[var(--line)] px-3 py-2"
              value={form.registration_number} onChange={(e) => setForm({ ...form, registration_number: e.target.value })} />
          </label>
          <label className="text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">Admin user ID (optional — NGO portal login)</span>
            <input type="number" className="w-full border border-[var(--line)] px-3 py-2"
              value={form.admin_user} onChange={(e) => setForm({ ...form, admin_user: e.target.value })} />
          </label>
          <label className="text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">Contact person</span>
            <input className="w-full border border-[var(--line)] px-3 py-2"
              value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} />
          </label>
          <label className="text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">Contact phone</span>
            <input className="w-full border border-[var(--line)] px-3 py-2"
              value={form.contact_phone} onChange={(e) => setForm({ ...form, contact_phone: e.target.value })} />
          </label>
          <label className="text-sm space-y-1 md:col-span-2">
            <span className="text-[var(--ink-soft)]">Contact email</span>
            <input type="email" className="w-full border border-[var(--line)] px-3 py-2"
              value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} />
          </label>

          {formError && <p className="text-sm text-[var(--danger)] md:col-span-2">{formError}</p>}

          <div className="md:col-span-2">
            <button type="submit" disabled={saving}
              className="bg-[var(--ink)] text-white text-sm font-medium px-4 py-2 hover:bg-[var(--accent)] disabled:opacity-60">
              {saving ? "Creating…" : "Create NGO"}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white border border-[var(--line)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--line)] text-left text-[var(--ink-soft)]">
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium">Scheme</th>
              <th className="px-4 py-2 font-medium">Reg. No.</th>
              <th className="px-4 py-2 font-medium">Contact</th>
              <th className="px-4 py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td className="px-4 py-4 text-[var(--ink-soft)]" colSpan={5}>Loading…</td></tr>
            )}
            {!loading && ngos.length === 0 && (
              <tr><td className="px-4 py-4 text-[var(--ink-soft)]" colSpan={5}>No NGOs registered yet.</td></tr>
            )}
            {ngos.map((ngo) => (
              <tr key={ngo.id} className="border-b border-[var(--line)] last:border-0">
                <td className="px-4 py-2.5 font-medium">{ngo.name}</td>
                <td className="px-4 py-2.5">{ngo.scheme_name}</td>
                <td className="px-4 py-2.5">{ngo.registration_number}</td>
                <td className="px-4 py-2.5">{ngo.contact_person || "—"}</td>
                <td className="px-4 py-2.5 text-right whitespace-nowrap">
                  <Link to={`/ngos/${ngo.id}`} className="text-[var(--accent)] underline mr-3">View</Link>
                  <button onClick={() => handleDelete(ngo)} className="text-[var(--danger)] underline">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
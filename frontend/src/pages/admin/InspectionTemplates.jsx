import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { client } from "../../api/client";

export default function InspectionTemplates() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    client.get("/inspections/templates/").then(({ data }) => setTemplates(data)).finally(() => setLoading(false));
  }
  useEffect(load, []);

  async function handleCreate(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await client.post("/inspections/templates/", { name, description, is_active: true });
      setName("");
      setDescription("");
      setShowForm(false);
      load();
    } catch {
      setError("Could not create template.");
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(t) {
    await client.patch(`/inspections/templates/${t.id}/`, { is_active: !t.is_active });
    load();
  }

  async function handleDelete(t) {
    if (!window.confirm(`Delete template "${t.name}"? Existing assignments using it will be affected.`)) return;
    try {
      await client.delete(`/inspections/templates/${t.id}/`);
      load();
    } catch {
      setError("Could not delete — it's likely still referenced by existing assignments.");
    }
  }

  return (
    <div className="p-8 space-y-4">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold text-[var(--ink)]">Inspection Templates</h1>
          <p className="text-sm text-[var(--ink-soft)]">Checklists used when officers submit an inspection.</p>
        </div>
        <button onClick={() => setShowForm((v) => !v)}
          className="bg-[var(--ink)] text-white text-sm font-medium px-4 py-2 hover:bg-[var(--accent)] transition-colors">
          {showForm ? "Cancel" : "+ New Template"}
        </button>
      </header>

      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white border border-[var(--line)] p-4 space-y-3">
          <label className="block text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">Name</span>
            <input required className="w-full border border-[var(--line)] px-3 py-2" value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="block text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">Description</span>
            <textarea rows={2} className="w-full border border-[var(--line)] px-3 py-2" value={description} onChange={(e) => setDescription(e.target.value)} />
          </label>
          <button type="submit" disabled={saving} className="bg-[var(--ink)] text-white text-sm font-medium px-4 py-2 disabled:opacity-60">
            {saving ? "Creating…" : "Create — then add questions"}
          </button>
        </form>
      )}

      <div className="bg-white border border-[var(--line)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--line)] text-left text-[var(--ink-soft)]">
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium">Questions</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td className="px-4 py-4 text-[var(--ink-soft)]" colSpan={4}>Loading…</td></tr>}
            {!loading && templates.length === 0 && (
              <tr><td className="px-4 py-4 text-[var(--ink-soft)]" colSpan={4}>No templates yet — create one above.</td></tr>
            )}
            {templates.map((t) => (
              <tr key={t.id} className="border-b border-[var(--line)] last:border-0">
                <td className="px-4 py-2.5 font-medium">{t.name}</td>
                <td className="px-4 py-2.5">{t.fields.length}</td>
                <td className="px-4 py-2.5">
                  <button onClick={() => toggleActive(t)} className={t.is_active ? "text-[var(--ok)]" : "text-[var(--ink-soft)]"}>
                    {t.is_active ? "Active" : "Inactive"}
                  </button>
                </td>
                <td className="px-4 py-2.5 text-right whitespace-nowrap">
                  <Link to={`/templates/${t.id}`} className="text-[var(--accent)] underline mr-3">Edit questions</Link>
                  <button onClick={() => handleDelete(t)} className="text-[var(--danger)] underline">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

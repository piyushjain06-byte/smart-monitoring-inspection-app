import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { client } from "../../api/client";

const FIELD_TYPES = [
  { value: "TEXT", label: "Short text" },
  { value: "TEXTAREA", label: "Long text" },
  { value: "YES_NO", label: "Yes / No" },
  { value: "RATING", label: "Rating (1-5)" },
  { value: "NUMBER", label: "Number" },
];

const BLANK = { label: "", field_type: "YES_NO", is_required: true, order: 0 };

export default function TemplateDetail() {
  const { id } = useParams();
  const [template, setTemplate] = useState(null);
  const [fields, setFields] = useState([]);
  const [form, setForm] = useState(BLANK);
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function load() {
    client.get(`/inspections/templates/${id}/`).then(({ data }) => {
      setTemplate(data);
      setFields(data.fields);
    });
  }
  useEffect(load, [id]);

  function startAdd() {
    setForm({ ...BLANK, order: fields.length });
    setEditingId(null);
  }

  function startEdit(f) {
    setForm({ label: f.label, field_type: f.field_type, is_required: f.is_required, order: f.order });
    setEditingId(f.id);
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = { ...form, template: id };
      if (editingId) {
        await client.patch(`/inspections/fields/${editingId}/`, payload);
      } else {
        await client.post("/inspections/fields/", payload);
      }
      setForm(BLANK);
      setEditingId(null);
      load();
    } catch {
      setError("Could not save question.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(f) {
    if (!window.confirm(`Delete question "${f.label}"?`)) return;
    await client.delete(`/inspections/fields/${f.id}/`);
    load();
  }

  async function move(f, direction) {
    const newOrder = f.order + direction;
    await client.patch(`/inspections/fields/${f.id}/`, { order: newOrder, template: id });
    load();
  }

  if (!template) return <div className="p-8 text-sm text-[var(--ink-soft)]">Loading…</div>;

  const sorted = [...fields].sort((a, b) => a.order - b.order);

  return (
    <div className="p-8 space-y-4 max-w-2xl">
      <div>
        <Link to="/templates" className="text-xs text-[var(--accent)] underline">← Back to templates</Link>
        <h1 className="text-lg font-semibold text-[var(--ink)] mt-2">{template.name}</h1>
        <p className="text-sm text-[var(--ink-soft)]">{template.description}</p>
      </div>

      <form onSubmit={handleSave} className="bg-white border border-[var(--line)] p-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
        <label className="md:col-span-2 space-y-1">
          <span className="text-[var(--ink-soft)]">Question / label</span>
          <input required className="w-full border border-[var(--line)] px-3 py-2"
            value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} />
        </label>
        <label className="space-y-1">
          <span className="text-[var(--ink-soft)]">Answer type</span>
          <select className="w-full border border-[var(--line)] px-3 py-2 bg-white"
            value={form.field_type} onChange={(e) => setForm({ ...form, field_type: e.target.value })}>
            {FIELD_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-2 mt-6">
          <input type="checkbox" checked={form.is_required}
            onChange={(e) => setForm({ ...form, is_required: e.target.checked })} />
          <span className="text-[var(--ink-soft)]">Required</span>
        </label>
        {error && <p className="md:col-span-2 text-[var(--danger)]">{error}</p>}
        <div className="md:col-span-2 flex gap-2">
          <button type="submit" disabled={saving} className="bg-[var(--ink)] text-white px-4 py-2 text-sm disabled:opacity-60">
            {saving ? "Saving…" : editingId ? "Update question" : "Add question"}
          </button>
          {editingId && (
            <button type="button" onClick={startAdd} className="border border-[var(--line)] px-4 py-2 text-sm">
              Cancel edit
            </button>
          )}
        </div>
      </form>

      <div className="bg-white border border-[var(--line)]">
        <ul className="divide-y divide-[var(--line)]">
          {sorted.length === 0 && (
            <li className="px-4 py-3 text-sm text-[var(--ink-soft)]">No questions yet — add one above.</li>
          )}
          {sorted.map((f) => (
            <li key={f.id} className="px-4 py-3 text-sm flex items-center justify-between">
              <div>
                <div className="font-medium">{f.label} {f.is_required && <span className="text-[var(--danger)]">*</span>}</div>
                <div className="text-xs text-[var(--ink-soft)]">{FIELD_TYPES.find((t) => t.value === f.field_type)?.label}</div>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <button onClick={() => move(f, -1)} className="text-[var(--ink-soft)] hover:text-[var(--ink)]">↑</button>
                <button onClick={() => move(f, 1)} className="text-[var(--ink-soft)] hover:text-[var(--ink)]">↓</button>
                <button onClick={() => startEdit(f)} className="text-[var(--accent)] underline">Edit</button>
                <button onClick={() => handleDelete(f)} className="text-[var(--danger)] underline">Delete</button>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

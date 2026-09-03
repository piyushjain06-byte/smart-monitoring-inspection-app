import { useEffect, useState } from "react";
import { client, getAccessToken, API_BASE_URL } from "../api/client";

const STATUS_STYLE = {
  ONLINE: "text-[var(--ok)]",
  OFFLINE: "text-[var(--danger)]",
  DISABLED: "text-[var(--ink-soft)]",
};

const BLANK_CAMERA = { name: "", camera_index: 0, stream_url: "", is_active: true };

/**
 * Phase 7 — CCTV panel for the institute detail page.
 * Now also supports adding/editing/deleting cameras directly (previously
 * this required /admin/) — see the form below the camera list.
 */
export default function CctvPanel({ instituteId }) {
  const [cameras, setCameras] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [streamFailed, setStreamFailed] = useState(false);
  const [pinging, setPinging] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(BLANK_CAMERA);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function loadCameras() {
    client.get(`/cctv/cameras/?institute=${instituteId}`).then(({ data }) => {
      setCameras(data);
      setSelectedId((current) => current ?? data[0]?.id ?? null);
    });
  }

  useEffect(() => {
    loadCameras();
    const interval = setInterval(loadCameras, 10000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [instituteId]);

  async function handlePing(cameraId) {
    setPinging(cameraId);
    try {
      await client.post(`/cctv/cameras/${cameraId}/ping/`);
    } finally {
      setPinging(null);
      loadCameras();
    }
  }

  function startAdd() {
    setForm(BLANK_CAMERA);
    setEditingId(null);
    setShowForm(true);
  }

  function startEdit(cam) {
    setForm({ name: cam.name, camera_index: cam.camera_index, stream_url: cam.stream_url, is_active: cam.is_active });
    setEditingId(cam.id);
    setShowForm(true);
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = { ...form, institute: instituteId, camera_index: Number(form.camera_index) || 0 };
      if (editingId) {
        await client.patch(`/cctv/cameras/${editingId}/`, payload);
      } else {
        await client.post("/cctv/cameras/", payload);
      }
      setShowForm(false);
      loadCameras();
    } catch {
      setError("Could not save camera.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(cam) {
    if (!window.confirm(`Delete camera "${cam.name}"?`)) return;
    await client.delete(`/cctv/cameras/${cam.id}/`);
    if (selectedId === cam.id) setSelectedId(null);
    loadCameras();
  }

  const selected = cameras.find((c) => c.id === selectedId);
  const streamSrc = selected ? `${API_BASE_URL}${selected.stream_path}?token=${getAccessToken()}` : null;

  return (
    <section className="bg-white border border-[var(--line)]">
      <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium flex items-center justify-between">
        <span>CCTV</span>
        <button onClick={startAdd} className="text-xs text-[var(--accent)] underline">+ Add camera</button>
      </div>

      {error && <p className="px-4 pt-3 text-sm text-[var(--danger)]">{error}</p>}

      {showForm && (
        <form onSubmit={handleSave} className="p-4 border-b border-[var(--line)] grid grid-cols-2 gap-2 text-sm">
          <label className="col-span-2 space-y-1">
            <span className="text-[var(--ink-soft)]">Name</span>
            <input required className="w-full border border-[var(--line)] px-2 py-1.5"
              value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </label>
          <label className="space-y-1">
            <span className="text-[var(--ink-soft)]">Camera index (local webcam demo)</span>
            <input type="number" className="w-full border border-[var(--line)] px-2 py-1.5"
              value={form.camera_index} onChange={(e) => setForm({ ...form, camera_index: e.target.value })} />
          </label>
          <label className="space-y-1">
            <span className="text-[var(--ink-soft)]">Stream URL (RTSP/HLS, optional)</span>
            <input className="w-full border border-[var(--line)] px-2 py-1.5"
              value={form.stream_url} onChange={(e) => setForm({ ...form, stream_url: e.target.value })} />
          </label>
          <label className="col-span-2 flex items-center gap-2">
            <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
            <span className="text-[var(--ink-soft)]">Active</span>
          </label>
          <div className="col-span-2 flex gap-2">
            <button type="submit" disabled={saving} className="bg-[var(--ink)] text-white px-3 py-1.5 disabled:opacity-60">
              {saving ? "Saving…" : "Save"}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="border border-[var(--line)] px-3 py-1.5">
              Cancel
            </button>
          </div>
        </form>
      )}

      {cameras.length === 0 && !showForm && (
        <p className="px-4 py-3 text-sm text-[var(--ink-soft)]">No cameras registered for this institute yet.</p>
      )}

      {cameras.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-0">
          <ul className="divide-y divide-[var(--line)] border-b md:border-b-0 md:border-r border-[var(--line)]">
            {cameras.map((cam) => (
              <li
                key={cam.id}
                onClick={() => { setSelectedId(cam.id); setStreamFailed(false); }}
                className={`px-4 py-3 text-sm flex items-center justify-between cursor-pointer hover:bg-[var(--bg)] ${cam.id === selectedId ? "bg-[var(--bg)]" : ""}`}
              >
                <span>{cam.name}</span>
                <span className="flex items-center gap-3">
                  <span className={`text-xs font-medium ${STATUS_STYLE[cam.status] || ""}`}>{cam.status}</span>
                  <button onClick={(e) => { e.stopPropagation(); handlePing(cam.id); }} disabled={pinging === cam.id}
                    className="text-xs text-[var(--accent)] underline disabled:opacity-50">
                    {pinging === cam.id ? "…" : "Refresh"}
                  </button>
                  <button onClick={(e) => { e.stopPropagation(); startEdit(cam); }} className="text-xs text-[var(--accent)] underline">
                    Edit
                  </button>
                  <button onClick={(e) => { e.stopPropagation(); handleDelete(cam); }} className="text-xs text-[var(--danger)] underline">
                    Delete
                  </button>
                </span>
              </li>
            ))}
          </ul>

          <div className="p-4 flex flex-col items-center justify-center min-h-[220px] bg-black/90">
            {selected && selected.status === "ONLINE" && !streamFailed ? (
              // eslint-disable-next-line jsx-a11y/img-redundant-alt
              <img key={selected.id} src={streamSrc} alt={`Live feed — ${selected.name}`}
                onError={() => setStreamFailed(true)} className="max-w-full max-h-[220px] object-contain" />
            ) : (
              <p className="text-xs text-white/60">{selected ? "No live feed available." : "Select a camera."}</p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

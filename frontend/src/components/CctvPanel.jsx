import Hls from "hls.js";
import { useEffect, useRef, useState } from "react";
import { client } from "../api/client";

const STATUS_STYLE = {
  ONLINE: "text-[var(--ok)]",
  OFFLINE: "text-[var(--danger)]",
  MAINTENANCE: "text-[var(--warn)]",
  DISABLED: "text-[var(--ink-soft)]",
};

const STATUS_LABEL = {
  ONLINE: "LIVE",
  OFFLINE: "OFFLINE",
  MAINTENANCE: "MAINTENANCE",
  DISABLED: "DISABLED",
};
const DEMO_STREAM_URL = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8";
const BLANK_CAMERA = { name: "", camera_index: 0, stream_url: "", is_active: true, is_maintenance: false };

function LiveCameraVideo({ camera, onError }) {
  const videoRef = useRef(null);
  const source = camera.stream_url || DEMO_STREAM_URL;

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !source) return undefined;

    let hls;
    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = source;
    } else if (Hls.isSupported()) {
      hls = new Hls();
      hls.loadSource(source);
      hls.attachMedia(video);
      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) onError();
      });
    } else {
      onError();
    }
    return () => {
      hls?.destroy();
      video.removeAttribute("src");
      video.load();
    };
  }, [source, onError, videoRef]);

  return (
    <video ref={videoRef} controls muted autoPlay playsInline
      onError={onError} className="w-full aspect-video object-contain bg-black" />
  );
}

/**
 * Phase 7 — CCTV panel for the institute detail page.
 * Now also supports adding/editing/deleting cameras directly (previously
 * this required /admin/) — see the form below the camera list.
 */
export default function CctvPanel({ instituteId }) {
  const [cameras, setCameras] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [streamFailed, setStreamFailed] = useState(false);
  const [gridView, setGridView] = useState(false);
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
    setForm({ name: cam.name, camera_index: cam.camera_index, stream_url: cam.stream_url, is_active: cam.is_active, is_maintenance: cam.is_maintenance });
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
  const hasDowntimeAlert = cameras.some((camera) => camera.offline_hours > 48);
  const visibleCameras = gridView ? cameras : (selected ? [selected] : []);

  return (
    <section className="bg-white border border-[var(--line)]">
      <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium flex items-center justify-between">
        <span>CCTV surveillance</span>
        <div className="flex items-center gap-3">
          {cameras.length > 1 && <button onClick={() => setGridView((value) => !value)} className="text-xs text-[var(--accent)] underline">
            {gridView ? "Single view" : "Grid view"}
          </button>}
          <button onClick={startAdd} className="text-xs text-[var(--accent)] underline">+ Add camera</button>
        </div>
      </div>

      {hasDowntimeAlert && <div role="alert" className="px-4 py-2 text-xs font-medium text-[var(--danger)] bg-[var(--danger)]/5 border-b border-[var(--danger)]/30">
        High Risk: CCTV offline &gt; 48h (Score Penalized)
      </div>}

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
          <label className="col-span-2 flex items-center gap-2">
            <input type="checkbox" checked={form.is_maintenance} onChange={(e) => setForm({ ...form, is_maintenance: e.target.checked })} />
            <span className="text-[var(--ink-soft)]">Under maintenance</span>
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
                  <span className={`text-xs font-medium ${STATUS_STYLE[cam.status] || ""}`}>
                    {cam.status === "ONLINE" && <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--danger)] mr-1 animate-pulse" />}
                    {STATUS_LABEL[cam.status] || cam.status}
                  </span>
                  {cam.offline_hours > 48 && <span className="text-xs font-medium text-[var(--danger)]">DOWNTIME ALERT · {cam.offline_hours}h</span>}
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

          <div className={`p-4 bg-black/90 ${gridView ? "grid grid-cols-1 xl:grid-cols-2 gap-3 content-start" : "min-h-[220px]"}`}>
            {visibleCameras.length === 0 && <p className="text-xs text-white/60 text-center py-16">Select a camera.</p>}
            {visibleCameras.map((camera) => (
              <div key={camera.id} className="relative">
                {!streamFailed || gridView ? <LiveCameraVideo camera={camera} onError={() => setStreamFailed(true)} /> : (
                  <p className="text-xs text-white/60 text-center py-16">No live feed available.</p>
                )}
                <span className="absolute top-2 left-2 bg-black/70 text-white text-xs px-2 py-1">{camera.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

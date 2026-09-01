import { useEffect, useState } from "react";
import { client, getAccessToken, API_BASE_URL } from "../api/client";

const STATUS_STYLE = {
  ONLINE: "text-[var(--ok)]",
  OFFLINE: "text-[var(--danger)]",
  DISABLED: "text-[var(--ink-soft)]",
};

/**
 * Phase 7 — CCTV panel for the institute detail page.
 * Lists this institute's cameras with live status, and shows an MJPEG
 * preview (webcam -> OpenCV -> Django stream) for whichever camera is
 * selected. Designed to degrade gracefully when no webcam is attached to
 * the server — that's expected on most laptops/demo machines and just
 * shows "No live feed" instead of erroring the page.
 */
export default function CctvPanel({ instituteId }) {
  const [cameras, setCameras] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [streamFailed, setStreamFailed] = useState(false);
  const [pinging, setPinging] = useState(null);

  function loadCameras() {
    client.get(`/cctv/cameras/?institute=${instituteId}`).then(({ data }) => {
      setCameras(data);
      setSelectedId((current) => current ?? data[0]?.id ?? null);
    });
  }

  useEffect(() => {
    loadCameras();
    // Poll every 10s so ONLINE/OFFLINE status catches up even if nobody
    // is actively viewing the stream (no WebSockets until Phase 4.5).
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

  const selected = cameras.find((c) => c.id === selectedId);
  const streamSrc = selected
    ? `${API_BASE_URL}${selected.stream_path}?token=${getAccessToken()}`
    : null;

  return (
    <section className="bg-white border border-[var(--line)]">
      <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">CCTV</div>

      {cameras.length === 0 && (
        <p className="px-4 py-3 text-sm text-[var(--ink-soft)]">No cameras registered for this institute yet.</p>
      )}

      {cameras.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-0">
          <ul className="divide-y divide-[var(--line)] border-b md:border-b-0 md:border-r border-[var(--line)]">
            {cameras.map((cam) => (
              <li
                key={cam.id}
                onClick={() => {
                  setSelectedId(cam.id);
                  setStreamFailed(false);
                }}
                className={`px-4 py-3 text-sm flex items-center justify-between cursor-pointer hover:bg-[var(--bg)] ${
                  cam.id === selectedId ? "bg-[var(--bg)]" : ""
                }`}
              >
                <span>{cam.name}</span>
                <span className="flex items-center gap-3">
                  <span className={`text-xs font-medium ${STATUS_STYLE[cam.status] || ""}`}>{cam.status}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePing(cam.id);
                    }}
                    disabled={pinging === cam.id}
                    className="text-xs text-[var(--accent)] underline disabled:opacity-50"
                  >
                    {pinging === cam.id ? "…" : "Refresh"}
                  </button>
                </span>
              </li>
            ))}
          </ul>

          <div className="p-4 flex flex-col items-center justify-center min-h-[220px] bg-black/90">
            {selected && selected.status === "ONLINE" && !streamFailed ? (
              // eslint-disable-next-line jsx-a11y/img-redundant-alt
              <img
                key={selected.id}
                src={streamSrc}
                alt={`Live feed — ${selected.name}`}
                onError={() => setStreamFailed(true)}
                className="max-w-full max-h-[220px] object-contain"
              />
            ) : (
              <p className="text-xs text-white/60">
                {selected ? "No live feed available." : "Select a camera."}
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

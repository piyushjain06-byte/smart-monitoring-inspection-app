import { useEffect, useState } from "react";
import { client } from "../api/client";

export default function VCSessionPanel({ instituteId, inspectionId = null, projectId = null }) {
  const [sessions, setSessions] = useState([]);
  const [active, setActive] = useState(null);
  const [purpose, setPurpose] = useState("Inspection consultation");
  const [participantIds, setParticipantIds] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function loadSessions() {
    client.get(`/consultations/sessions/?institute=${instituteId}`)
      .then(({ data }) => setSessions(data))
      .catch(() => setSessions([]));
  }

  useEffect(() => {
    loadSessions();
  }, [instituteId]);

  async function initiate() {
    setBusy(true);
    setError("");
    try {
      const ids = participantIds.split(",").map((value) => Number(value.trim())).filter(Boolean);
      const { data } = await client.post(`/registry/institutes/${instituteId}/initiate-vc/`, {
        purpose,
        inspection: inspectionId,
        project: projectId,
        participant_ids: ids,
      });
      const session = await client.get(`/consultations/sessions/${data.session_id}/`);
      setSessions((current) => [session.data, ...current]);
      setActive(session.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not create the VC session.");
    } finally {
      setBusy(false);
    }
  }

  async function action(name, session = active) {
    setBusy(true);
    setError("");
    try {
      const { data } = await client.post(`/consultations/sessions/${session.id}/${name}/`);
      setActive(data.session || data);
      loadSessions();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not update the VC session.");
    } finally {
      setBusy(false);
    }
  }

  const joined = active?.participants?.find((participant) => participant.joined_at && !participant.left_at);

  return (
    <section className="bg-white border border-[var(--line)]">
      <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">Video consultations</div>
      <div className="p-4 space-y-3 text-sm">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <input value={purpose} onChange={(event) => setPurpose(event.target.value)} placeholder="Purpose / reason" className="border border-[var(--line)] px-3 py-2" />
          <input value={participantIds} onChange={(event) => setParticipantIds(event.target.value)} placeholder="Participant user IDs (comma-separated)" className="border border-[var(--line)] px-3 py-2" />
          <button onClick={initiate} disabled={busy} className="bg-[var(--ink)] text-white px-3 py-2 disabled:opacity-50">Start VC</button>
        </div>
        {error && <p className="text-[var(--danger)]">{error}</p>}
        {active && (
          <div className="border border-[var(--accent)] p-3 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">Session #{active.id} · {active.status}</span>
              <span className="text-xs text-[var(--ink-soft)]">{active.purpose}</span>
            </div>
            <div className="text-xs text-[var(--ink-soft)]">
              Participants: {active.participants.map((participant) => `${participant.user_name} (${participant.joined_at && !participant.left_at ? "joined" : "invited"})`).join(", ")}
            </div>
            <div className="flex flex-wrap gap-2">
              {active.status === "SCHEDULED" && <button onClick={() => action("start")} disabled={busy} className="border border-[var(--ink)] px-3 py-1.5">Start session</button>}
              {active.status === "LIVE" && <button onClick={() => action("join")} disabled={busy} className="bg-[var(--accent)] text-white px-3 py-1.5">Join Jitsi</button>}
              {active.status === "LIVE" && <button onClick={() => action("end")} disabled={busy} className="border border-[var(--danger)] text-[var(--danger)] px-3 py-1.5">End session</button>}
            </div>
            {active.status === "LIVE" && joined && (
              <iframe title={`VC session ${active.id}`} src={`https://meet.jit.si/${encodeURIComponent(active.room_name)}`} allow="camera; microphone; fullscreen; display-capture" className="w-full aspect-video bg-black" />
            )}
          </div>
        )}
        <div className="border-t border-[var(--line)] pt-3">
          <div className="font-medium mb-2">Session history</div>
          {sessions.length === 0 ? <p className="text-[var(--ink-soft)]">No VC sessions recorded.</p> : sessions.map((session) => (
            <button key={session.id} onClick={() => setActive(session)} className="w-full text-left border-b border-[var(--line)] py-2 last:border-0">
              <span className="font-medium">{new Date(session.created_at).toLocaleString()}</span>{" · "}{session.status}{" · "}{session.created_by_name}{session.duration_seconds != null ? ` · ${Math.round(session.duration_seconds / 60)} min` : ""}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

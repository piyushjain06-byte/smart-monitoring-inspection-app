import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { client } from "../api/client";
import CctvPanel from "../components/CctvPanel";

const STATUS_STYLE = {
  PENDING: "text-[var(--warn)]",
  OVERDUE: "text-[var(--danger)]",
  SUBMITTED: "text-[var(--ok)]",
};

export default function InstituteDetail() {
  const { id } = useParams();
  const [institute, setInstitute] = useState(null);
  const [projects, setProjects] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [notFound, setNotFound] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [assignResult, setAssignResult] = useState(null);

  function loadAssignments() {
    client.get(`/inspections/assignments/?institute=${id}`).then(({ data }) => setAssignments(data));
  }

  useEffect(() => {
    client
      .get(`/registry/institutes/${id}/`)
      .then(({ data }) => setInstitute(data))
      .catch(() => setNotFound(true));
    client.get(`/registry/projects/?institute=${id}`).then(({ data }) => setProjects(data));
    loadAssignments();
  }, [id]);

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

  if (notFound) {
    return (
      <div className="p-8">
        <p className="text-sm text-[var(--ink-soft)]">Institute not found.</p>
        <Link to="/institutes" className="text-[var(--accent)] underline text-sm">
          Back to list
        </Link>
      </div>
    );
  }

  if (!institute) {
    return <div className="p-8 text-sm text-[var(--ink-soft)]">Loading…</div>;
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link to="/institutes" className="text-xs text-[var(--accent)] underline">
            ← Back to institutes
          </Link>
          <h1 className="text-lg font-semibold text-[var(--ink)] mt-2">{institute.name}</h1>
          <p className="text-sm text-[var(--ink-soft)]">
            {institute.ngo_name} · {institute.scheme_name} · {institute.district}, {institute.state}
          </p>
        </div>
        <button
          onClick={handleAssign}
          disabled={assigning}
          className="shrink-0 bg-[var(--ink)] text-white text-sm font-medium px-4 py-2 hover:bg-[var(--accent)] transition-colors disabled:opacity-60"
        >
          {assigning ? "Assigning…" : "Assign Inspection"}
        </button>
      </div>

      {assignResult && (
        <div
          className={`text-sm px-4 py-2 border ${
            assignResult.ok
              ? "border-[var(--ok)] text-[var(--ok)] bg-[var(--ok)]/5"
              : "border-[var(--danger)] text-[var(--danger)] bg-[var(--danger)]/5"
          }`}
        >
          {assignResult.ok ? (
            <div>
              <div>
                Assigned to <strong>{assignResult.data.officer_name}</strong> — due {assignResult.data.due_date}.
              </div>
              <div className="mt-1 text-xs text-[var(--ink-soft)]">
                {assignResult.candidates
                  .map((c) => `${c.officer_name} → ${c.distance_km ?? "?"} km (workload ${c.workload})`)
                  .join("  ·  ")}
              </div>
            </div>
          ) : (
            assignResult.message
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <section className="bg-white border border-[var(--line)]">
          <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">Projects</div>
          <ul className="divide-y divide-[var(--line)]">
            {projects.length === 0 && (
              <li className="px-4 py-3 text-sm text-[var(--ink-soft)]">No projects recorded yet.</li>
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
            Inspection history
          </div>
          <ul className="divide-y divide-[var(--line)]">
            {assignments.length === 0 && (
              <li className="px-4 py-3 text-sm text-[var(--ink-soft)]">No inspections assigned yet.</li>
            )}
            {assignments.map((a) => (
              <li key={a.id} className="px-4 py-3 text-sm flex justify-between">
                <div>
                  <div>{a.template_name}</div>
                  <div className="text-xs text-[var(--ink-soft)]">
                    {a.officer_name} · due {a.due_date}
                  </div>
                </div>
                <span className={`text-xs font-medium ${STATUS_STYLE[a.status] || ""}`}>{a.status}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <CctvPanel instituteId={id} />
    </div>
  );
}

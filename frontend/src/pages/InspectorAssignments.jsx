import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { client } from "../api/client";

const STATUS_STYLE = {
  PENDING: "text-[var(--warn)]",
  OVERDUE: "text-[var(--danger)]",
  SUBMITTED: "text-[var(--ok)]",
};

export default function InspectorAssignments() {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    client
      .get("/inspections/assignments/")
      .then(({ data }) => setAssignments(data))
      .catch(() => setError("Could not load your assignments."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 space-y-4">
      <header>
        <h1 className="text-lg font-semibold text-[var(--ink)]">My Assignments</h1>
        <p className="text-sm text-[var(--ink-soft)]">
          Institutes you've been assigned to inspect.
        </p>
      </header>

      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

      <div className="bg-white border border-[var(--line)]">
        {loading && <div className="px-4 py-4 text-sm text-[var(--ink-soft)]">Loading…</div>}
        {!loading && assignments.length === 0 && (
          <div className="px-4 py-4 text-sm text-[var(--ink-soft)]">
            No inspections assigned to you yet.
          </div>
        )}
        <ul className="divide-y divide-[var(--line)]">
          {assignments.map((a) => (
            <li key={a.id} className="px-4 py-3 flex items-center justify-between text-sm">
              <div>
                <div className="font-medium">{a.institute_name}</div>
                <div className="text-xs text-[var(--ink-soft)]">
                  {a.institute_district}, {a.institute_state} · {a.template_name} · due {a.due_date}
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className={`text-xs font-medium ${STATUS_STYLE[a.status] || ""}`}>{a.status}</span>
                {a.status === "PENDING" || a.status === "OVERDUE" ? (
                  <Link
                    to={`/inspector/assignments/${a.id}/submit`}
                    className="text-[var(--accent)] underline"
                  >
                    Submit
                  </Link>
                ) : (
                  <span className="text-[var(--ink-soft)]">Submitted</span>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

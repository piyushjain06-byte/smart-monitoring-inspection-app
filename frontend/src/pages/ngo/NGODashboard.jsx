import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { client } from "../../api/client";
import StatCard from "../../components/StatCard";

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

/**
 * Fills the gap noted in README.md: Role.NGO_ADMIN and Role.PROJECT_INCHARGE
 * exist but had no dedicated frontend. This mirrors Dashboard.jsx + Institutes.jsx
 * for officials, but scoped through /api/registry/portal/* (see
 * apps/registry/portal_views.py) instead of the official-only endpoints.
 */
export default function NGODashboard() {
  const [summary, setSummary] = useState(null);
  const [institutes, setInstitutes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      client.get("/registry/portal/dashboard-summary/"),
      client.get("/registry/portal/institutes/"),
    ])
      .then(([s, i]) => {
        setSummary(s.data);
        setInstitutes(i.data);
      })
      .catch(() => setError("Could not load your institutes. Is the Django server running?"))
      .finally(() => setLoading(false));
  }, []);

  if (error) {
    return <div className="p-8 text-sm text-[var(--danger)]">{error}</div>;
  }

  return (
    <div className="p-8 space-y-6">
      <header>
        <h1 className="text-lg font-semibold text-[var(--ink)]">My Institutes</h1>
        <p className="text-sm text-[var(--ink-soft)]">
          Institutes and projects you administer.
        </p>
      </header>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Institutes" value={summary?.total_institutes ?? "—"} />
        <StatCard label="Active projects" value={summary?.active_projects ?? "—"} />
        <StatCard label="High risk (AI)" value={summary?.high_risk_institutes ?? "—"} accent="var(--danger)" />
        <StatCard label="Inspections pending" value={summary?.pending_inspections ?? "—"} accent="var(--warn)" />
      </div>

      <div className="bg-white border border-[var(--line)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--line)] text-left text-[var(--ink-soft)]">
              <th className="px-4 py-2 font-medium">Institute</th>
              <th className="px-4 py-2 font-medium">District</th>
              <th className="px-4 py-2 font-medium">Inspection</th>
              <th className="px-4 py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td className="px-4 py-4 text-[var(--ink-soft)]" colSpan={4}>Loading…</td></tr>
            )}
            {!loading && institutes.length === 0 && (
              <tr><td className="px-4 py-4 text-[var(--ink-soft)]" colSpan={4}>No institutes assigned to your account yet.</td></tr>
            )}
            {institutes.map((inst) => (
              <tr key={inst.id} className="border-b border-[var(--line)] last:border-0">
                <td className="px-4 py-2.5 font-medium">{inst.name}</td>
                <td className="px-4 py-2.5">{inst.district}, {inst.state}</td>
                <td className={`px-4 py-2.5 ${STATUS_STYLE[inst.latest_inspection_status] || ""}`}>
                  {STATUS_LABEL[inst.latest_inspection_status] || "—"}
                </td>
                <td className="px-4 py-2.5 text-right">
                  <Link to={`/ngo-portal/institutes/${inst.id}`} className="text-[var(--accent)] underline">
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

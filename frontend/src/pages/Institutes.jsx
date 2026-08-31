import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { client } from "../api/client";

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

export default function Institutes() {
  const [institutes, setInstitutes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client
      .get("/registry/institutes/")
      .then(({ data }) => setInstitutes(data))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 space-y-4">
      <header>
        <h1 className="text-lg font-semibold text-[var(--ink)]">Institutes &amp; Projects</h1>
        <p className="text-sm text-[var(--ink-soft)]">
          Every registered institute under the platform's schemes.
        </p>
      </header>

      <div className="bg-white border border-[var(--line)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--line)] text-left text-[var(--ink-soft)]">
              <th className="px-4 py-2 font-medium">Institute</th>
              <th className="px-4 py-2 font-medium">NGO</th>
              <th className="px-4 py-2 font-medium">District</th>
              <th className="px-4 py-2 font-medium">Inspection</th>
              <th className="px-4 py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td className="px-4 py-4 text-[var(--ink-soft)]" colSpan={5}>Loading…</td></tr>
            )}
            {!loading && institutes.length === 0 && (
              <tr><td className="px-4 py-4 text-[var(--ink-soft)]" colSpan={5}>No institutes registered yet.</td></tr>
            )}
            {institutes.map((inst) => (
              <tr key={inst.id} className="border-b border-[var(--line)] last:border-0">
                <td className="px-4 py-2.5 font-medium">{inst.name}</td>
                <td className="px-4 py-2.5">{inst.ngo_name}</td>
                <td className="px-4 py-2.5">{inst.district}, {inst.state}</td>
                <td className={`px-4 py-2.5 ${STATUS_STYLE[inst.latest_inspection_status] || ""}`}>
                  {STATUS_LABEL[inst.latest_inspection_status] || "—"}
                </td>
                <td className="px-4 py-2.5 text-right">
                  <Link to={`/institutes/${inst.id}`} className="text-[var(--accent)] underline">
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

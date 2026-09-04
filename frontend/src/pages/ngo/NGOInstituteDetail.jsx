import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { client } from "../../api/client";

const SEVERITY_STYLE = {
  LOW: "text-[var(--ok)]",
  MEDIUM: "text-[var(--warn)]",
  HIGH: "text-[var(--danger)]",
};

/**
 * NGO/Incharge portal equivalent of InstituteDetail.jsx — deliberately
 * read-only (no "Assign Inspection" button, no CCTV panel): this portal is
 * for the NGO/incharge to see their own standing, not to act on behalf of
 * the government dashboard.
 *
 * FLATTENED ARCHITECTURE: Institute no longer references NGO, so there's
 * no ngo_name to show here. Projects are no longer tied to an Institute
 * either (Project -> Scheme now), so the "Projects" panel below fetches
 * by the institute's Scheme instead of by institute id.
 */
export default function NGOInstituteDetail() {
  const { id } = useParams();
  const [institute, setInstitute] = useState(null);
  const [projects, setProjects] = useState([]);
  const [staff, setStaff] = useState([]);
  const [notFound, setNotFound] = useState(false);
  const [risk, setRisk] = useState(null);
  const [riskLoading, setRiskLoading] = useState(true);

  useEffect(() => {
    client
      .get(`/registry/portal/institutes/${id}/`)
      .then(({ data }) => setInstitute(data))
      .catch(() => setNotFound(true));
    client.get(`/registry/portal/staff/?institute=${id}`).then(({ data }) => setStaff(data));

    setRiskLoading(true);
    // Note: the live risk endpoint lives under the official-only
    // analytics API. NGO/incharge accounts see the pre-computed
    // latest_risk_severity/score fields on the institute itself instead
    // (see InstituteSerializer) — deliberately not exposing the full
    // factor breakdown/PDF report to this portal.
    setRiskLoading(false);
  }, [id]);

  useEffect(() => {
    if (institute) {
      setRisk({
        severity: institute.latest_risk_severity,
        score: institute.latest_risk_score,
      });
      // FLATTENED ARCHITECTURE: Project -> Scheme, not Institute — the
      // closest thing to "projects related to this institute" now is
      // "projects under the same Scheme".
      if (institute.scheme) {
        client
          .get(`/registry/portal/projects/?scheme=${institute.scheme}`)
          .then(({ data }) => setProjects(data))
          .catch(() => setProjects([]));
      }
    }
  }, [institute]);

  if (notFound) {
    return (
      <div className="p-8">
        <p className="text-sm text-[var(--ink-soft)]">
          Institute not found, or not assigned to your account.
        </p>
        <Link to="/ngo-portal" className="text-[var(--accent)] underline text-sm">
          Back to my institutes
        </Link>
      </div>
    );
  }

  if (!institute) {
    return <div className="p-8 text-sm text-[var(--ink-soft)]">Loading…</div>;
  }

  return (
    <div className="p-8 space-y-6">
      <div>
        <Link to="/ngo-portal" className="text-xs text-[var(--accent)] underline">
          ← Back to my institutes
        </Link>
        <h1 className="text-lg font-semibold text-[var(--ink)] mt-2">{institute.name}</h1>
        <p className="text-sm text-[var(--ink-soft)]">
          {institute.scheme_name} · {institute.district}, {institute.state}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <section className="bg-white border border-[var(--line)]">
          <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">
            Projects under this Scheme
          </div>
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
          <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">Staff</div>
          <ul className="divide-y divide-[var(--line)]">
            {staff.length === 0 && (
              <li className="px-4 py-3 text-sm text-[var(--ink-soft)]">No staff recorded yet.</li>
            )}
            {staff.map((s) => (
              <li key={s.id} className="px-4 py-3 text-sm flex justify-between">
                <span>{s.full_name}</span>
                <span className="text-[var(--ink-soft)]">{s.designation || "—"}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="bg-white border border-[var(--line)]">
        <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium flex items-center justify-between">
          <span>AI risk status</span>
          {!riskLoading && risk?.severity && (
            <span className={`text-sm font-semibold ${SEVERITY_STYLE[risk.severity] || ""}`}>
              {risk.score}/100 — {risk.severity}
            </span>
          )}
        </div>
        <div className="p-4 text-sm text-[var(--ink-soft)]">
          {riskLoading && "Loading…"}
          {!riskLoading && !risk?.severity && "No AI risk analysis has been run for this institute yet."}
          {!riskLoading && risk?.severity && "Contact your district authority for the full risk factor breakdown."}
        </div>
      </section>
    </div>
  );
}

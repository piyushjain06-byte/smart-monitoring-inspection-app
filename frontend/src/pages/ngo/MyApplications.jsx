import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { client } from "../../api/client";

const STATUS_STYLE = {
  PENDING: "text-[var(--warn)]",
  APPROVED: "text-[var(--ok)]",
  REJECTED: "text-[var(--danger)]",
};

export default function MyApplications() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.get("/onboarding/applications/")
      .then(({ data }) => setApplications(data))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 space-y-4">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold text-[var(--ink)]">My Applications</h1>
          <p className="text-sm text-[var(--ink-soft)]">Status of every scheme application you've submitted.</p>
        </div>
        <Link
          to="/ngo-portal/apply"
          className="shrink-0 bg-[var(--ink)] text-white text-sm font-medium px-4 py-2 hover:bg-[var(--accent)] transition-colors"
        >
          + Apply for a scheme
        </Link>
      </header>

      <div className="bg-white border border-[var(--line)]">
        {loading && <div className="px-4 py-4 text-sm text-[var(--ink-soft)]">Loading…</div>}
        {!loading && applications.length === 0 && (
          <div className="px-4 py-4 text-sm text-[var(--ink-soft)]">
            You haven't applied for any scheme yet.
          </div>
        )}
        <ul className="divide-y divide-[var(--line)]">
          {applications.map((a) => (
            <li key={a.id} className="px-4 py-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="font-medium">{a.project_name} — {a.scheme_name}</div>
                  <div className="text-xs text-[var(--ink-soft)] mt-0.5">
                    Requested ₹{a.proposed_fund_amount}
                    {a.status === "APPROVED" && a.approved_fund_amount != null && ` · Approved ₹${a.approved_fund_amount}`}
                  </div>
                </div>
                <span className={`text-xs font-semibold shrink-0 ${STATUS_STYLE[a.status] || ""}`}>
                  {a.status_display}
                </span>
              </div>
              {a.review_notes && (
                <div className="text-xs text-[var(--ink-soft)] mt-2 border-t border-[var(--line)] pt-2">
                  Government note: {a.review_notes}
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

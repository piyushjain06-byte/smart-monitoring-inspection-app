import { useEffect, useState } from "react";
import { client } from "../../api/client";
import { useAuth } from "../../context/AuthContext";

const STATUS_STYLE = {
  PENDING: "text-[var(--warn)]",
  APPROVED: "text-[var(--ok)]",
  REJECTED: "text-[var(--danger)]",
};

function ReviewRow({ application, canReview, onReviewed }) {
  const [expanded, setExpanded] = useState(false);
  const [approvedAmount, setApprovedAmount] = useState(application.proposed_fund_amount);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleDecision(decision) {
    setBusy(true);
    setError("");
    try {
      await client.post(`/onboarding/applications/${application.id}/${decision}/`, {
        approved_fund_amount: decision === "approve" ? approvedAmount : undefined,
        review_notes: notes,
      });
      onReviewed();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not record the decision.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="px-4 py-3 text-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-medium">{application.organization_name} ({application.applicant_type_display})</div>
          <div className="text-xs text-[var(--ink-soft)] mt-0.5">
            {application.scheme_name} · {application.project_name} · requested ₹{application.proposed_fund_amount}
          </div>
          <div className="text-xs text-[var(--ink-soft)]">
            Applicant: {application.applicant_display_name} ({application.applicant_username})
          </div>
        </div>
        <span className={`text-xs font-semibold shrink-0 ${STATUS_STYLE[application.status] || ""}`}>
          {application.status_display}
        </span>
      </div>

      <button onClick={() => setExpanded((v) => !v)} className="text-xs text-[var(--accent)] underline mt-2">
        {expanded ? "Hide plan" : "View plan"}
      </button>

      {expanded && (
        <div className="mt-2 border-t border-[var(--line)] pt-2 space-y-2">
          <p className="text-[var(--ink)] whitespace-pre-wrap">{application.project_plan}</p>
          <div className="text-xs text-[var(--ink-soft)]">
            {application.address && <>Address: {application.address}<br /></>}
            {(application.state || application.district) && <>Location: {application.district}, {application.state}<br /></>}
            {application.proposed_start_date && <>Proposed: {application.proposed_start_date} → {application.proposed_end_date || "—"}</>}
          </div>

          {application.status === "PENDING" && canReview && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-2">
              <label className="text-xs space-y-1">
                <span className="text-[var(--ink-soft)]">Approved fund amount (₹)</span>
                <input type="number" step="0.01" className="w-full border border-[var(--line)] px-2 py-1.5"
                  value={approvedAmount} onChange={(e) => setApprovedAmount(e.target.value)} />
              </label>
              <label className="text-xs space-y-1">
                <span className="text-[var(--ink-soft)]">Review notes (shown to applicant)</span>
                <input className="w-full border border-[var(--line)] px-2 py-1.5"
                  value={notes} onChange={(e) => setNotes(e.target.value)} />
              </label>
              <div className="md:col-span-2 flex gap-2">
                <button onClick={() => handleDecision("approve")} disabled={busy}
                  className="bg-[var(--ok)] text-white px-3 py-1.5 text-xs font-medium disabled:opacity-60">
                  {busy ? "Working…" : "Approve"}
                </button>
                <button onClick={() => handleDecision("reject")} disabled={busy}
                  className="bg-[var(--danger)] text-white px-3 py-1.5 text-xs font-medium disabled:opacity-60">
                  {busy ? "Working…" : "Reject"}
                </button>
              </div>
              {error && <p className="md:col-span-2 text-[var(--danger)] text-xs">{error}</p>}
            </div>
          )}
          {application.status === "PENDING" && !canReview && (
            <p className="text-xs text-[var(--ink-soft)] pt-1">
              Only the DoSJE HQ Super Admin can approve or reject applications.
            </p>
          )}
          {application.status !== "PENDING" && application.review_notes && (
            <p className="text-xs text-[var(--ink-soft)] pt-1">Review note: {application.review_notes}</p>
          )}
        </div>
      )}
    </li>
  );
}

/**
 * Government Review step of the onboarding flow. Backend enforces that
 * only the Super Admin (is_superuser or role=SUPER_ADMIN) can actually
 * call approve/reject — canReview here only controls whether the buttons
 * are shown, not whether the action succeeds.
 */
export default function SchemeApplications() {
  const { user } = useAuth();
  const canReview = !!user && (user.is_superuser || user.role === "SUPER_ADMIN");
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("PENDING");

  function load() {
    setLoading(true);
    client.get("/onboarding/applications/").then(({ data }) => setApplications(data)).finally(() => setLoading(false));
  }

  useEffect(load, []);

  const visible = filter === "ALL" ? applications : applications.filter((a) => a.status === filter);

  return (
    <div className="p-8 space-y-4">
      <header>
        <h1 className="text-lg font-semibold text-[var(--ink)]">Scheme Applications</h1>
        <p className="text-sm text-[var(--ink-soft)]">
          NGO/Institute requests to run a project under a scheme.
          {!canReview && " You can view these, but only the DoSJE HQ Super Admin can approve or reject."}
        </p>
      </header>

      <div className="flex gap-1 border-b border-[var(--line)]">
        {["PENDING", "APPROVED", "REJECTED", "ALL"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              filter === f ? "border-[var(--accent)] text-[var(--accent)]" : "border-transparent text-[var(--ink-soft)]"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      <div className="bg-white border border-[var(--line)]">
        {loading && <div className="px-4 py-4 text-sm text-[var(--ink-soft)]">Loading…</div>}
        {!loading && visible.length === 0 && (
          <div className="px-4 py-4 text-sm text-[var(--ink-soft)]">No applications here.</div>
        )}
        <ul className="divide-y divide-[var(--line)]">
          {visible.map((a) => (
            <ReviewRow key={a.id} application={a} canReview={canReview} onReviewed={load} />
          ))}
        </ul>
      </div>
    </div>
  );
}

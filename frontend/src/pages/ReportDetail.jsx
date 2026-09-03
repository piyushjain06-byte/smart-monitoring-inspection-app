import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { client } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { isOfficial } from "../constants/roles";

// Works under two routes:
//   /institutes/:instituteId/reports/:assignmentId   (officials)
//   /inspector/reports/:assignmentId                 (field officers, own reports only)
// Either way we just fetch /inspections/reports/ (the backend already scopes
// it: officials see everything, officers see only their own) and find the
// one matching this assignment id.
export default function ReportDetail() {
  const { assignmentId } = useParams();
  const { user } = useAuth();
  const [report, setReport] = useState(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    client
      .get("/inspections/reports/")
      .then(({ data }) => {
        const match = data.find((r) => String(r.assignment) === String(assignmentId));
        if (match) setReport(match);
        else setNotFound(true);
      })
      .catch(() => setNotFound(true));
  }, [assignmentId]);

  async function handleDownloadPdf() {
    if (!report) return;
    const res = await client.get(`/inspections/reports/${report.id}/pdf/`, { responseType: "blob" });
    const isPdf = (res.headers["content-type"] || "").includes("pdf");
    const blob = new Blob([res.data], { type: isPdf ? "application/pdf" : "text/html" });
    const url = window.URL.createObjectURL(blob);
    if (isPdf) {
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `report-${report.id}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } else {
      window.open(url, "_blank");
    }
    window.URL.revokeObjectURL(url);
  }

  const official = isOfficial(user);
  const backTo = official && report ? `/institutes/${report.institute}` : "/inspector";
  const backLabel = official ? "Back to institute" : "Back to my assignments";

  if (notFound) {
    return (
      <div className="p-8">
        <p className="text-sm text-[var(--ink-soft)]">Report not found for this assignment.</p>
        <Link to={official ? "/institutes" : "/inspector"} className="text-[var(--accent)] underline text-sm">
          {backLabel}
        </Link>
      </div>
    );
  }

  if (!report) return <div className="p-8 text-sm text-[var(--ink-soft)]">Loading…</div>;

  return (
    <div className="p-8 space-y-4 max-w-2xl">
      <div>
        <Link to={backTo} className="text-xs text-[var(--accent)] underline">
          ← {backLabel}
        </Link>
        <div className="flex items-start justify-between gap-4 mt-2">
          <div>
            <h1 className="text-lg font-semibold text-[var(--ink)]">{report.template_name}</h1>
            <p className="text-sm text-[var(--ink-soft)]">
              {report.institute_name} · submitted by {report.officer_name} on{" "}
              {new Date(report.submitted_at).toLocaleString()}
            </p>
          </div>
          <button
            onClick={handleDownloadPdf}
            className="shrink-0 border border-[var(--ink)] text-[var(--ink)] text-sm font-medium px-4 py-2 hover:bg-[var(--ink)] hover:text-white transition-colors"
          >
            Download PDF
          </button>
        </div>
      </div>

      <div className="bg-white border border-[var(--line)] p-4 flex items-center justify-between text-sm">
        <span className="text-[var(--ink-soft)]">Overall score</span>
        <span className="font-semibold text-[var(--ink)]">{report.overall_score ?? "—"}/100</span>
      </div>

      <div className="bg-white border border-[var(--line)] p-4 flex items-center justify-between text-sm">
        <span className="text-[var(--ink-soft)]">Location verified (within geofence)</span>
        <span className={report.location_verified ? "text-[var(--ok)] font-medium" : "text-[var(--danger)] font-medium"}>
          {report.location_verified ? "Yes" : "No — flagged"}
        </span>
      </div>

      <section className="bg-white border border-[var(--line)]">
        <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">Answers</div>
        <ul className="divide-y divide-[var(--line)]">
          {report.answers_display.length === 0 && (
            <li className="px-4 py-3 text-sm text-[var(--ink-soft)]">No answers recorded.</li>
          )}
          {report.answers_display.map((a) => (
            <li key={a.field_id} className="px-4 py-3 text-sm flex justify-between gap-4">
              <span>{a.label}</span>
              <span className="font-medium text-[var(--ink)]">{String(a.answer)}</span>
            </li>
          ))}
        </ul>
      </section>

      {report.notes && (
        <section className="bg-white border border-[var(--line)] p-4">
          <div className="text-sm font-medium mb-1">Notes</div>
          <p className="text-sm text-[var(--ink-soft)]">{report.notes}</p>
        </section>
      )}

      <section className="bg-white border border-[var(--line)]">
        <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">Evidence</div>
        {report.evidence_items.length === 0 ? (
          <p className="px-4 py-3 text-sm text-[var(--ink-soft)]">No evidence attached.</p>
        ) : (
          <div className="p-4 flex flex-wrap gap-3">
            {report.evidence_items.map((ev) => (
              <a key={ev.id} href={ev.file} target="_blank" rel="noreferrer" className="block">
                {ev.media_type === "PHOTO" ? (
                  <img src={ev.file} alt="evidence" className="w-28 h-24 object-cover border border-[var(--line)]" />
                ) : (
                  <div className="w-28 h-24 border border-[var(--line)] flex items-center justify-center text-xs text-[var(--ink-soft)] text-center px-1">
                    {ev.media_type}
                  </div>
                )}
              </a>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

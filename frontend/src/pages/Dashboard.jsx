import { useEffect, useState } from "react";
import { client } from "../api/client";
import StatCard from "../components/StatCard";
import ProjectMap from "../components/ProjectMap";
import AIAlertsPanel from "../components/AIAlertsPanel";

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [institutes, setInstitutes] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [alertsLoading, setAlertsLoading] = useState(true);
  const [error, setError] = useState("");
  const [surprising, setSurprising] = useState(false);
  const [surpriseResult, setSurpriseResult] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);

  function loadData() {
    Promise.all([
      client.get("/registry/dashboard-summary/"),
      client.get("/registry/institutes/"),
    ])
      .then(([s, i]) => {
        setSummary(s.data);
        setInstitutes(i.data);
      })
      .catch(() => setError("Could not load dashboard data. Is the Django server running?"));

    setAlertsLoading(true);
    client
      .get("/analytics/alerts/?status=open")
      .then(({ data }) => setAlerts(data))
      .catch(() => setAlerts([]))
      .finally(() => setAlertsLoading(false));
  }

  useEffect(loadData, []);

  async function handleSurprise() {
    setSurprising(true);
    setSurpriseResult(null);
    try {
      const { data } = await client.post("/inspections/assignments/surprise/");
      setSurpriseResult({ ok: true, data: data.assignment });
      loadData();
    } catch (err) {
      setSurpriseResult({ ok: false, message: err.response?.data?.detail || "Could not assign an inspection." });
    } finally {
      setSurprising(false);
    }
  }

  async function handleRunAnalysis() {
    setAnalyzing(true);
    setAnalysisResult(null);
    try {
      const { data } = await client.post("/analytics/run/");
      setAnalysisResult({
        ok: true,
        message: `Scored ${data.evaluated} institute(s) — ${data.high_risk_count} HIGH risk, ${data.alerts_created} new alert(s).`,
      });
      loadData();
    } catch (err) {
      setAnalysisResult({ ok: false, message: err.response?.data?.detail || "Could not run AI analysis." });
    } finally {
      setAnalyzing(false);
    }
  }

  if (error) {
    return <div className="p-8 text-sm text-[var(--danger)]">{error}</div>;
  }

  return (
    <div className="p-8 space-y-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold text-[var(--ink)]">Government Dashboard</h1>
          <p className="text-sm text-[var(--ink-soft)]">
            Live overview of institutes, projects, and inspections.
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button
            onClick={handleRunAnalysis}
            disabled={analyzing}
            className="bg-white border border-[var(--ink)] text-[var(--ink)] text-sm font-medium px-4 py-2 hover:bg-[var(--ink)] hover:text-white transition-colors disabled:opacity-60"
          >
            {analyzing ? "Analyzing…" : "Run AI Analysis"}
          </button>
          <button
            onClick={handleSurprise}
            disabled={surprising}
            className="bg-[var(--ink)] text-white text-sm font-medium px-4 py-2 hover:bg-[var(--accent)] transition-colors disabled:opacity-60"
          >
            {surprising ? "Assigning…" : "Surprise Inspection"}
          </button>
        </div>
      </header>

      {surpriseResult && (
        <div
          className={`text-sm px-4 py-2 border ${
            surpriseResult.ok
              ? "border-[var(--ok)] text-[var(--ok)] bg-[var(--ok)]/5"
              : "border-[var(--danger)] text-[var(--danger)] bg-[var(--danger)]/5"
          }`}
        >
          {surpriseResult.ok
            ? `Assigned to ${surpriseResult.data.officer_name} — due ${surpriseResult.data.due_date}.`
            : surpriseResult.message}
        </div>
      )}

      {analysisResult && (
        <div
          className={`text-sm px-4 py-2 border ${
            analysisResult.ok
              ? "border-[var(--ok)] text-[var(--ok)] bg-[var(--ok)]/5"
              : "border-[var(--danger)] text-[var(--danger)] bg-[var(--danger)]/5"
          }`}
        >
          {analysisResult.message}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <StatCard label="Institutes" value={summary?.total_institutes ?? "—"} />
        <StatCard label="Active projects" value={summary?.active_projects ?? "—"} />
        <StatCard label="High risk (AI)" value={summary?.high_risk_institutes ?? "—"} accent="var(--danger)" />
        <StatCard label="Inspections pending" value={summary?.pending_inspections ?? "—"} accent="var(--warn)" />
        <StatCard label="Open AI alerts" value={summary?.open_ai_alerts ?? "—"} accent="var(--danger)" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-white border border-[var(--line)] h-[480px]">
          <ProjectMap institutes={institutes} />
        </div>

        <div className="space-y-4">
          <div className="bg-white border border-[var(--line)]">
            <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">
              Inspection status
            </div>
            <div className="p-4 space-y-3 text-sm">
              <Row label="Submitted" value={summary?.submitted_inspections} color="var(--ok)" />
              <Row label="Pending" value={summary?.pending_inspections} color="var(--warn)" />
              <Row label="Overdue" value={summary?.overdue_inspections} color="var(--danger)" />
            </div>
          </div>

          <AIAlertsPanel alerts={alerts} loading={alertsLoading} />
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, color }) {
  return (
    <div className="flex items-center justify-between">
      <span className="flex items-center gap-2 text-[var(--ink-soft)]">
        <span className="w-2 h-2 rounded-full inline-block" style={{ background: color }} />
        {label}
      </span>
      <span className="font-medium text-[var(--ink)]">{value ?? "—"}</span>
    </div>
  );
}

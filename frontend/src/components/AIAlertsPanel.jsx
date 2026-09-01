import { Link } from "react-router-dom";

const SEVERITY_COLOR = {
  LOW: "var(--ok)",
  MEDIUM: "var(--warn)",
  HIGH: "var(--danger)",
};

/**
 * Phase 9, Part 25/34 — lists open AIAlert rows produced by the risk
 * engine (POST /api/analytics/run/). Replaces the placeholder note that
 * used to sit in Dashboard.jsx before this phase was built.
 */
export default function AIAlertsPanel({ alerts, loading }) {
  return (
    <div className="bg-white border border-[var(--line)]">
      <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">AI alerts</div>

      {loading && <div className="p-4 text-sm text-[var(--ink-soft)]">Loading…</div>}

      {!loading && alerts.length === 0 && (
        <div className="p-4 text-sm text-[var(--ink-soft)]">
          No open alerts. Click "Run AI Analysis" to score institutes.
        </div>
      )}

      <ul className="divide-y divide-[var(--line)]">
        {alerts.map((alert) => (
          <li key={alert.id} className="px-4 py-3 text-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <span
                  className="inline-block w-2 h-2 rounded-full mr-2 align-middle"
                  style={{ background: SEVERITY_COLOR[alert.severity] }}
                />
                <span className="font-medium">{alert.alert_type_display}</span>
                <div className="text-xs text-[var(--ink-soft)] mt-0.5 ml-4">{alert.description}</div>
              </div>
              <Link
                to={`/institutes/${alert.institute}`}
                className="shrink-0 text-xs text-[var(--accent)] underline"
              >
                {alert.institute_name}
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

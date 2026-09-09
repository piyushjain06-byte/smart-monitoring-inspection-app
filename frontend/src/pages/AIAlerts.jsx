import { useEffect, useState } from "react";
import AIAlertsPanel from "../components/AIAlertsPanel";
import { client } from "../api/client";

export default function AIAlerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  function loadAlerts() {
    setLoading(true);
    client.get("/analytics/alerts/?status=open")
      .then(({ data }) => setAlerts(data))
      .catch(() => setAlerts([]))
      .finally(() => setLoading(false));
  }

  useEffect(loadAlerts, []);

  return (
    <div className="p-8 space-y-4">
      <header>
        <h1 className="text-lg font-semibold text-[var(--ink)]">AI Alerts</h1>
        <p className="text-sm text-[var(--ink-soft)]">Explainable risk alerts from attendance, CCTV health, inspection history, and anomaly signals.</p>
      </header>
      <AIAlertsPanel alerts={alerts} loading={loading} onChanged={loadAlerts} />
    </div>
  );
}

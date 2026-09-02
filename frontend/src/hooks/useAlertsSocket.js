import { useEffect, useRef, useState } from "react";
import { WS_BASE_URL, getAccessToken } from "../api/client";

const RECONNECT_DELAY_MS = 3000;

/**
 * Phase 4.5 — subscribes to apps/analytics/consumers.py::AIAlertConsumer.
 * Calls `onMessage(event)` for every message (event.type is
 * "alert.created" or "analysis.completed") and exposes `connected` so the
 * UI can show a small "Live" indicator. Auto-reconnects on drop (e.g. the
 * dev server restarting) rather than leaving the panel silently stale.
 *
 * Safe to use even when Redis/Channels isn't running: the socket simply
 * fails to connect, `connected` stays false, and the caller's existing
 * poll-on-load behaviour (already in Dashboard.jsx from Phase 3/9) is
 * completely unaffected — this is additive, not a replacement.
 */
export default function useAlertsSocket(onMessage) {
  const [connected, setConnected] = useState(false);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    let socket;
    let reconnectTimer;
    let cancelled = false;

    function connect() {
      const token = getAccessToken();
      if (!token || cancelled) return;

      socket = new WebSocket(`${WS_BASE_URL}/ws/analytics/alerts/?token=${token}`);

      socket.onopen = () => setConnected(true);

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessageRef.current?.(data);
        } catch {
          // Ignore malformed frames rather than crashing the dashboard.
        }
      };

      socket.onclose = () => {
        setConnected(false);
        if (!cancelled) reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
      };

      socket.onerror = () => socket.close();
    }

    connect();

    return () => {
      cancelled = true;
      clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);

  return { connected };
}

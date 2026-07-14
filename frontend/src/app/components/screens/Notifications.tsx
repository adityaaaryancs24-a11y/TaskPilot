import { useEffect, useState, useCallback } from "react";
import { Bell, AlertTriangle, Info, AlertCircle, CheckCircle } from "lucide-react";
import { Card } from "../shared/Card";
import { SourceBadge } from "../shared/SourceBadge";
import { getPlan, getDashboard, Alert, WebSocketEvent } from "../../api/taskpilot";
import { useWebSocket } from "../../hooks/useWebSocket";

const ALERT_ICONS: Record<string, typeof AlertCircle> = {
  critical: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const ALERT_COLORS: Record<string, string> = {
  critical: "#F7C5E6",
  warning: "#F5D66E",
  info: "#C9D8FF",
};

export function Notifications() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [narratives, setNarratives] = useState<string[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPlan()
      .then(p => setAlerts(p?.alerts || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleWsEvent = useCallback((event: WebSocketEvent) => {
    if (event.event === "alerts_updated") {
      setAlerts(Array.isArray(event.data) ? event.data as Alert[] : []);
    }
    if (event.event === "plan_updated") {
      const p = event.data as any;
      if (p?.alerts) setAlerts(p.alerts);
    }
    if (event.event === "narrative_alert") {
      setNarratives(prev => [String(event.data), ...prev].slice(0, 10));
    }
  }, []);

  useWebSocket(handleWsEvent);

  const visibleAlerts = alerts.filter(a => !dismissed.has(a.message));

  const handleDismiss = (msg: string) => {
    setDismissed(prev => new Set(prev).add(msg));
  };

  const handleDismissAll = () => {
    setDismissed(new Set(alerts.map(a => a.message)));
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <Bell size={20} /> Notifications
          </h2>
          <p style={{ color: "#7A7A7A", fontSize: 13, marginTop: 4 }}>
            {loading ? "Loading..." : `${visibleAlerts.length} active alerts`}
          </p>
        </div>
        {visibleAlerts.length > 0 && (
          <button onClick={handleDismissAll}
            style={{ background: "none", border: "1px solid #E9E4D8", padding: "8px 16px", borderRadius: 10, fontSize: 12, cursor: "pointer", color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>
            Dismiss All
          </button>
        )}
      </div>

      {narratives.length > 0 && (
        <Card variant="purple" shadow>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <Bell size={12} /> <span style={{ fontSize: 11, fontWeight: 600, fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase", letterSpacing: "0.04em" }}>AI Narratives</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {narratives.map((n, i) => (
              <div key={i} style={{ padding: "6px 0", borderBottom: i < narratives.length - 1 ? "1px solid rgba(0,0,0,0.06)" : "none", fontSize: 12, color: "#7A7A7A", display: "flex", gap: 6 }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#C9D8FF", flexShrink: 0, marginTop: 4 }} />
                {n}
              </div>
            ))}
          </div>
        </Card>
      )}

      {loading ? (
        <div style={{ textAlign: "center", color: "#7A7A7A", padding: 40, fontSize: 13 }}>Loading notifications...</div>
      ) : visibleAlerts.length === 0 ? (
        <Card style={{ textAlign: "center", padding: 40 }}>
          <CheckCircle size={24} style={{ margin: "0 auto 12px", opacity: 0.4 }} />
          <p style={{ color: "#7A7A7A", fontSize: 13, margin: 0 }}>All clear! No active alerts.</p>
        </Card>
      ) : (
        visibleAlerts.map((alert, i) => {
          const Icon = ALERT_ICONS[alert.severity] || Info;
          const bg = ALERT_COLORS[alert.severity] || "#F6F2E9";
          return (
            <Card key={i} shadow style={{ borderLeft: `4px solid ${bg}` }}>
              <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                <Icon size={16} color="#7A7A7A" style={{ flexShrink: 0, marginTop: 2 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                    <span style={{
                      fontSize: 10, fontWeight: 600, fontFamily: "'IBM Plex Mono', monospace",
                      color: "#111111", textTransform: "uppercase", letterSpacing: "0.04em",
                    }}>{alert.severity}</span>
                    {alert.task_id && <SourceBadge source={alert.task_id} />}
                  </div>
                  <p style={{ margin: 0, fontSize: 13, color: "#111111", lineHeight: 1.5 }}>
                    {alert.message}
                  </p>
                </div>
                <button onClick={() => handleDismiss(alert.message)}
                  style={{ background: "none", border: "none", fontSize: 18, color: "#B0A8A0", cursor: "pointer", padding: "0 4px", lineHeight: 1 }}>
                  ×
                </button>
              </div>
            </Card>
          );
        })
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { Link2, Plug, CheckCircle, XCircle, RefreshCw, AlertCircle } from "lucide-react";
import { Card } from "../shared/Card";
import { getSources, getHealth, syncNow, Source, ConnectorStatus } from "../../api/taskpilot";

const INTEGRATION_LOGOS: Record<string, string> = {
  jira: "🔷", github: "🐙", slack: "💬", outlook: "📧", servicenow: "🔧",
};

export function Integrations() {
  const [sources, setSources] = useState<Source[]>([]);
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [s, h] = await Promise.all([
        getSources().catch(() => ({ sources: [], total_tasks: 0 })),
        getHealth().catch(() => null),
      ]);
      setSources(s.sources || []);
      setConnectors(h?.connectors || []);
      setHealth(h);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  const handleSync = async (name?: string) => {
    setSyncing(name || "all");
    try { await syncNow(name?.toLowerCase() === "all" ? undefined : name?.toLowerCase()); }
    catch (err) { console.error(err); }
    finally { setSyncing(null); fetchData(); }
  };

  const uniqueConnectors = new Map<string, ConnectorStatus>();
  [...connectors, ...(sources.map(s => ({ name: s.name, connected: s.status === "connected", last_sync: s.last_sync || null, error: s.error || null })) as ConnectorStatus[])]
    .forEach(c => uniqueConnectors.set(c.name, c));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ margin: 0 }}>Integrations</h2>
          <p style={{ color: "#7A7A7A", fontSize: 13, marginTop: 4 }}>
            {loading ? "Loading..." : `${uniqueConnectors.size} sources`}
          </p>
        </div>
        <button onClick={() => handleSync()} disabled={!!syncing}
          style={{ background: "#0D0D0D", color: "#FFFFFF", border: "none", padding: "10px 20px", borderRadius: 12, fontSize: 12, cursor: syncing ? "wait" : "pointer", display: "flex", alignItems: "center", gap: 6, fontFamily: "'IBM Plex Mono', monospace", opacity: syncing ? 0.7 : 1 }}>
          <RefreshCw size={13} className={syncing ? "" : ""} /> {syncing === "all" ? "Syncing..." : "Sync All"}
        </button>
      </div>

      {health && (
        <Card variant="green" shadow>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <Plug size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>System Health</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 8 }}>
            {[
              { label: "API", ok: health.status === "healthy" },
              { label: "Jira", ok: health.jira_connected },
              { label: "GitHub", ok: health.github_connected },
              { label: "Redis", ok: health.redis_connected },
              { label: "Database", ok: health.database_connected },
            ].map((item, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, background: "#F6F2E9", padding: "8px 12px", borderRadius: 10 }}>
                {item.ok ? <CheckCircle size={13} color="#BFD78D" /> : <XCircle size={13} color="#F7C5E6" />}
                <span style={{ fontSize: 12, color: "#111111" }}>{item.label}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {Array.from(uniqueConnectors.values()).length === 0 && !loading && (
          <Card style={{ textAlign: "center", padding: 40 }}>
            <Link2 size={24} style={{ margin: "0 auto 12px", opacity: 0.4 }} />
            <p style={{ color: "#7A7A7A", fontSize: 13, margin: 0 }}>No integrations configured yet.</p>
          </Card>
        )}
        {Array.from(uniqueConnectors.values()).map((c: ConnectorStatus) => (
          <Card key={c.name} shadow>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{ fontSize: 24, lineHeight: 1 }}>{INTEGRATION_LOGOS[c.name.toLowerCase()] || "🔌"}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#111111" }}>{c.name}</div>
                <div style={{ display: "flex", gap: 8, marginTop: 2 }}>
                  {c.connected ? (
                    <span style={{ fontSize: 11, color: "#BFD78D", fontFamily: "'IBM Plex Mono', monospace" }}>Connected</span>
                  ) : (
                    <span style={{ fontSize: 11, color: "#F7C5E6", fontFamily: "'IBM Plex Mono', monospace" }}>Disconnected</span>
                  )}
                  {c.last_sync && (
                    <span style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>
                      Last sync: {new Date(c.last_sync).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </span>
                  )}
                </div>
                {c.error && (
                  <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 4, fontSize: 11, color: "#F7C5E6" }}>
                    <AlertCircle size={11} /> {c.error}
                  </div>
                )}
              </div>
              <button onClick={() => handleSync(c.name)}
                disabled={!!syncing}
                style={{ background: "none", border: "1px solid #E9E4D8", padding: "8px 16px", borderRadius: 10, fontSize: 12, cursor: syncing ? "wait" : "pointer", color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>
                {syncing === c.name ? "..." : "Sync"}
              </button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

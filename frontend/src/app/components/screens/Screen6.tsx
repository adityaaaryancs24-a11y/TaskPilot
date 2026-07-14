import { useEffect, useState } from "react";
import { AppHeader } from "../shared/AppHeader";

interface Trace {
  id: number;
  timestamp: string;
  step_name: string;
  duration_ms: number;
  tokens_used: number;
  status: string;
}

export function Screen6() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/traces")
      .then((res) => res.json())
      .then((data) => {
        setTraces(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Trace fetch error:", err);
        setLoading(false);
      });
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <AppHeader />
      <main style={{ flex: 1, overflow: "auto", padding: "28px" }}>
        <div style={{ marginBottom: 24 }}>
          <h2 style={{ margin: 0 }}>Pipeline Traces</h2>
          <p style={{ color: "#7A7A7A", fontSize: 13, marginTop: 4 }}>
            {loading ? "Loading..." : `${traces.length} trace${traces.length !== 1 ? "s" : ""}`}
          </p>
        </div>

        {loading && (
          <p style={{ color: "#7A7A7A", fontSize: 13 }}>Loading traces...</p>
        )}

        {!loading && traces.length === 0 && (
          <div style={{ textAlign: "center", color: "#7A7A7A", fontSize: 13, padding: 60 }}>
            <p>No traces available. Run a pipeline to collect step timing data.</p>
          </div>
        )}

        {!loading && traces.length > 0 && (
          <div style={{ border: "1px solid #D9D9D9", overflow: "hidden", background: "#FFFFFF" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#F8F8F6" }}>
                  <th style={{ padding: "10px 14px", textAlign: "left", color: "#7A7A7A", fontWeight: 500, borderBottom: "1px solid #D9D9D9", fontFamily: "'IBM Plex Mono', monospace", fontSize: 11 }}>Step</th>
                  <th style={{ padding: "10px 14px", textAlign: "right", color: "#7A7A7A", fontWeight: 500, borderBottom: "1px solid #D9D9D9", fontFamily: "'IBM Plex Mono', monospace", fontSize: 11 }}>Latency (ms)</th>
                  <th style={{ padding: "10px 14px", textAlign: "right", color: "#7A7A7A", fontWeight: 500, borderBottom: "1px solid #D9D9D9", fontFamily: "'IBM Plex Mono', monospace", fontSize: 11 }}>Tokens</th>
                  <th style={{ padding: "10px 14px", textAlign: "center", color: "#7A7A7A", fontWeight: 500, borderBottom: "1px solid #D9D9D9", fontFamily: "'IBM Plex Mono', monospace", fontSize: 11 }}>Status</th>
                  <th style={{ padding: "10px 14px", textAlign: "right", color: "#7A7A7A", fontWeight: 500, borderBottom: "1px solid #D9D9D9", fontFamily: "'IBM Plex Mono', monospace", fontSize: 11 }}>Time</th>
                </tr>
              </thead>
              <tbody>
                {traces.map((trace, idx) => (
                  <tr key={trace.id} style={{ borderBottom: idx < traces.length - 1 ? "1px solid #D9D9D9" : "none" }}>
                    <td style={{ padding: "10px 14px", color: "#111111", fontFamily: "'IBM Plex Mono', monospace", fontSize: 12 }}>{trace.step_name}</td>
                    <td style={{ padding: "10px 14px", textAlign: "right", color: "#111111", fontFamily: "'IBM Plex Mono', monospace" }}>{trace.duration_ms.toFixed(1)}</td>
                    <td style={{ padding: "10px 14px", textAlign: "right", color: trace.tokens_used > 0 ? "#111111" : "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>
                      {trace.tokens_used > 0 ? trace.tokens_used : "—"}
                    </td>
                    <td style={{ padding: "10px 14px", textAlign: "center" }}>
                      <span style={{
                        display: "inline-block",
                        padding: "2px 10px",
                        fontSize: 11, fontWeight: 500,
                        border: `1px solid ${trace.status === "ok" ? "#16A34A" : "#DC2626"}`,
                        color: trace.status === "ok" ? "#16A34A" : "#DC2626",
                        fontFamily: "'IBM Plex Mono', monospace",
                      }}>
                        {trace.status}
                      </span>
                    </td>
                    <td style={{ padding: "10px 14px", textAlign: "right", color: "#7A7A7A", fontSize: 11, whiteSpace: "nowrap", fontFamily: "'IBM Plex Mono', monospace" }}>
                      {new Date(trace.timestamp).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}

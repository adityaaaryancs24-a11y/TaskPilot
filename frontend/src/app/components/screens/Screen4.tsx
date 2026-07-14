import { useEffect, useState, useCallback } from "react";
import { AppHeader } from "../shared/AppHeader";
import { Card } from "../shared/Card";
import { SourceBadge } from "../shared/SourceBadge";
import { SparkleIcon } from "../shared/SparkleIcon";
import { ExtractionVisualization } from "../shared/ExtractionVisualization";
import { getSources, getRecentExtractions, SourcesResponse, ExtractionItem, WebSocketEvent } from "../../api/taskpilot";
import { useWebSocket } from "../../hooks/useWebSocket";

export function Screen4() {
  const [sources, setSources] = useState<SourcesResponse | null>(null);
  const [extractions, setExtractions] = useState<ExtractionItem[]>([]);
  const [loading, setLoading] = useState(true);

  const handleWsEvent = useCallback((event: WebSocketEvent) => {
    if (event.event === "tasks_updated" || event.event === "plan_updated") {
      getSources().then(setSources).catch(() => {});
      getRecentExtractions().then(r => setExtractions(r.extractions)).catch(() => {});
    }
  }, []);

  useWebSocket(handleWsEvent);

  useEffect(() => {
    Promise.all([
      getSources(),
      getRecentExtractions(),
    ])
      .then(([srcRes, extRes]) => {
        setSources(srcRes);
        setExtractions(extRes.extractions);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const displaySources = sources?.sources ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <AppHeader />
      <main style={{ flex: 1, overflow: "auto", padding: "28px" }}>
        <div style={{ marginBottom: 24 }}>
          <h2 style={{ margin: 0 }}>Sources</h2>
          <p style={{ color: "#7A7A7A", fontSize: 13, marginTop: 4 }}>
            {loading ? "Loading..." : `${displaySources.length} connected integrations`}
          </p>
        </div>

        <div style={{ border: "1px solid #D9D9D9", padding: "10px 16px", background: "#FFFFFF", display: "flex", alignItems: "center", gap: 8, marginBottom: 20 }}>
          <SparkleIcon size={14} />
          <span style={{ color: "#7A7A7A", fontSize: 13 }}>
            Live data from {displaySources.filter(s => s.status === "Synced").length}/{displaySources.length} connected sources
            {extractions.length > 0 && (
              <span style={{ marginLeft: 4 }}>
                &middot; <strong style={{ color: "#F97316" }}>{extractions.length}</strong> hidden action items found
              </span>
            )}
          </span>
        </div>

        {loading ? (
          <div style={{ color: "#7A7A7A", fontSize: 13, textAlign: "center", padding: 40 }}>
            Loading sources...
          </div>
        ) : (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 28 }}>
              {displaySources.map((src) => (
                <div key={src.name} style={{ border: "1px solid #D9D9D9", padding: "16px", background: "#FFFFFF" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                    <div style={{ width: 36, height: 36, border: "1px solid #D9D9D9", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <span style={{ fontSize: 10, fontWeight: 700, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>{src.name.slice(0, 2).toUpperCase()}</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                      <span style={{ width: 7, height: 7, borderRadius: "50%", background: src.status === "Synced" ? "#16A34A" : "#D97706", display: "inline-block" }} />
                      <span style={{ color: "#7A7A7A", fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>{src.status}</span>
                    </div>
                  </div>
                  <div style={{ color: "#111111", fontSize: 13, fontWeight: 500, marginBottom: 4 }}>{src.name}</div>
                  <div style={{ color: "#7A7A7A", fontSize: 12, marginBottom: 4 }}>Live data via API</div>
                  <div style={{ color: "#7A7A7A", fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>
                    Status: {src.status}
                    {src.last_sync ? ` · Last sync: ${new Date(src.last_sync).toLocaleTimeString()}` : ""}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ color: "#7A7A7A", fontSize: 12, fontWeight: 500, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 12, fontFamily: "'IBM Plex Mono', monospace" }}>
              Extracted Action Items
            </div>
            <div style={{ color: "#7A7A7A", fontSize: 13, marginBottom: 16 }}>
              {sources?.total_tasks ?? 0} total tasks across all sources
            </div>

            {extractions.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {extractions.slice(0, 10).map((item) => (
                  <ExtractionVisualization key={item.task_id} item={item} />
                ))}
              </div>
            )}

            {extractions.length === 0 && !loading && (
              <div style={{ border: "1px solid #D9D9D9", padding: 40, background: "#FFFFFF", textAlign: "center" }}>
                <p style={{ color: "#7A7A7A", fontSize: 13, margin: 0 }}>
                  No extractions available yet. Sync your sources to generate tasks.
                </p>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

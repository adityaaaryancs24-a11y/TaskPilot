import { useEffect, useState, useCallback } from "react";
import { GitBranch, ArrowRight, Lightbulb, RefreshCw, Info } from "lucide-react";
import { Card } from "../shared/Card";
import { StatusPill } from "../shared/StatusPill";
import { DependencyGraph } from "../shared/DependencyGraph";
import { getDependencyAnalysis, getTasks, WebSocketEvent } from "../../api/taskpilot";
import { useWebSocket } from "../../hooks/useWebSocket";

function Legend() {
  const items = [
    { color: "#F7C5E6", label: "Depends on" },
    { color: "#BFD78D", label: "Blocks" },
    { color: "#F6F2E9", label: "No relation" },
  ];
  return (
    <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
      <span style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>Legend:</span>
      {items.map((item) => (
        <div key={item.label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ width: 12, height: 12, borderRadius: 4, background: item.color, border: item.label === "No relation" ? "1px solid #E9E4D8" : "none" }} />
          <span style={{ fontSize: 11, color: "#7A7A7A" }}>{item.label}</span>
        </div>
      ))}
    </div>
  );
}

export function Dependencies() {
  const [blockingImpact, setBlockingImpact] = useState<Record<string, any>>({});
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [dep, t] = await Promise.all([
        getDependencyAnalysis().catch(() => null),
        getTasks({ limit: 200 }).catch(() => ({ tasks: [] })),
      ]);
      if (dep) {
        setBlockingImpact(dep.blocking_impacts || {});
        setRecommendations(dep.unblocking_recommendations || []);
      }
      setTasks(t.tasks || []);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  const handleWsEvent = useCallback((event: WebSocketEvent) => {
    if (event.event === "plan_updated") fetchData();
  }, []);

  useWebSocket(handleWsEvent);

  const taskMap = new Map(tasks.map(t => [t.id, t]));

  const blockingEntries = Object.entries(blockingImpact).sort(
    (a, b) => (b[1].total_impact_score || 0) - (a[1].total_impact_score || 0)
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <GitBranch size={20} /> Dependencies
          </h2>
          <p style={{ color: "#7A7A7A", fontSize: 13, marginTop: 4 }}>
            {loading ? "Loading..." : `${tasks.length} tasks · ${blockingEntries.length} blocking impacts · ${recommendations.length} recommendations`}
          </p>
        </div>
        <button onClick={fetchData} style={{ background: "#0D0D0D", color: "#FFFFFF", border: "none", padding: "10px 20px", borderRadius: 12, fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontFamily: "'IBM Plex Mono', monospace" }}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {tasks.length > 0 && (
        <Card shadow>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <GitBranch size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Dependency Graph</span>
            </div>
            <Legend />
          </div>
          <DependencyGraph tasks={tasks} />
        </Card>
      )}

      {blockingEntries.length > 0 && (
        <Card variant="orange" shadow>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
            <Info size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Blocking Impact Map</span>
          </div>
          {blockingEntries.slice(0, 8).map(([tid, bi]) => (
            <div key={tid} style={{ padding: "10px 0", borderBottom: "1px solid #E9E4D8", display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, color: "#111111", fontWeight: 500 }}>{bi.title || tid}</div>
                <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                  <span style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>
                    Blocks {bi.blocks_directly} directly · {bi.blocks_transitively} transitively
                  </span>
                </div>
                {bi.blocked_by_ids?.length > 0 && (
                  <div style={{ display: "flex", gap: 6, marginTop: 4, flexWrap: "wrap" }}>
                    {bi.blocked_by_ids.map((bid: string) => {
                      const bt = taskMap.get(bid);
                      return (
                        <span key={bid} style={{ background: "#F7C5E6", padding: "2px 8px", borderRadius: 6, fontSize: 10, color: "#111111" }}>
                          Blocked by: {bt?.title?.slice(0, 30) || bid}
                        </span>
                      );
                    })}
                  </div>
                )}
              </div>
              <div style={{ background: "#FAD6B3", padding: "6px 12px", borderRadius: 10, fontSize: 12, fontWeight: 600, textAlign: "center", minWidth: 60 }}>
                <div>Impact</div>
                <div>{bi.total_impact_score?.toFixed(1)}</div>
              </div>
            </div>
          ))}
        </Card>
      )}

      {recommendations.length > 0 && (
        <Card variant="purple" shadow>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
            <Lightbulb size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Unblocking Recommendations</span>
          </div>
          {recommendations.slice(0, 6).map((rec, i) => (
            <div key={i} style={{ padding: "10px 0", borderBottom: "1px solid #E9E4D8" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, marginBottom: 4 }}>
                <span style={{ color: "#7A7A7A" }}>{rec.blocked_task_title}</span>
                <ArrowRight size={12} color="#7A7A7A" />
                <span style={{ color: "#111111", fontWeight: 500 }}>{rec.blocking_task_title}</span>
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 2, alignItems: "center" }}>
                <StatusPill status={rec.blocking_task_status as any} />
                <span style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>{rec.suggestion}</span>
              </div>
            </div>
          ))}
        </Card>
      )}

      {!loading && blockingEntries.length === 0 && recommendations.length === 0 && tasks.length === 0 && (
        <Card style={{ textAlign: "center", padding: 40 }}>
          <p style={{ color: "#7A7A7A", fontSize: 13, margin: 0 }}>No dependency information available. Run the pipeline to analyze dependencies.</p>
        </Card>
      )}
    </div>
  );
}

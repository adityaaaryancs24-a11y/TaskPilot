import { useEffect, useState, useCallback } from "react";
import { ChevronDown } from "lucide-react";
import { AppHeader } from "../shared/AppHeader";
import { PriorityPill } from "../shared/PriorityPill";
import { SourceBadge } from "../shared/SourceBadge";
import { StatusPill } from "../shared/StatusPill";
import { SparkleIcon } from "../shared/SparkleIcon";
import { AIRationale } from "../shared/AIRationale";
import { getTasks, Task, WebSocketEvent } from "../../api/taskpilot";
import { useWebSocket } from "../../hooks/useWebSocket";

export function Screen2() {
  const [expanded, setExpanded] = useState("");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  const handleWsEvent = useCallback((event: WebSocketEvent) => {
    if (event.event === "tasks_updated") {
      const data = Array.isArray(event.data) ? event.data : [];
      setTasks(data as Task[]);
    }
  }, []);

  useWebSocket(handleWsEvent);

  useEffect(() => {
    getTasks()
      .then(r => setTasks(Array.isArray(r.tasks) ? r.tasks : []))
      .catch(() => setTasks([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <AppHeader />
      <main style={{ flex: 1, overflow: "auto", padding: "28px" }}>
        <div style={{ marginBottom: 20 }}>
          <h2 style={{ margin: 0 }}>All Tasks</h2>
          <p style={{ color: "#7A7A7A", fontSize: 13, marginTop: 4 }}>
            {loading ? "Loading..." : `${tasks.length} tasks across sources`}
          </p>
        </div>

        {!loading && tasks.length === 0 && (
          <div style={{ textAlign: "center", color: "#7A7A7A", fontSize: 13, padding: 60 }}>
            <p>No tasks found. Connect your sources and run the pipeline to populate your task list.</p>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {tasks.map((task: any) => (
            <div key={task.id}>
              <div style={{ cursor: "pointer", border: "1px solid #D9D9D9", padding: "13px 16px", background: "#FFFFFF" }}>
                <div onClick={() => setExpanded(expanded === task.id ? "" : task.id)} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <ChevronDown size={13} color="#7A7A7A"
                    style={{ transform: expanded === task.id ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 0.15s", flexShrink: 0 }} />
                  <span style={{ color: "#7A7A7A", fontSize: 11, fontFamily: "'IBM Plex Mono', monospace", minWidth: 72 }}>{task.id}</span>
                  <span style={{ color: "#111111", fontSize: 13, flex: 1 }}>{task.title}</span>
                  <SourceBadge source={task.source || task.source_type} />
                  <PriorityPill level={(task.priority ?? "P3") as any} />
                  <span style={{ color: "#7A7A7A", fontSize: 12, minWidth: 110, fontFamily: "'IBM Plex Mono', monospace" }}>{task.deadline || ""}</span>
                  <StatusPill status={task.status || "open"} />
                  {(task.merged_sources?.length > 0 || task.merged_from?.length > 0) && (
                    <span style={{ display: "flex", alignItems: "center", gap: 4, color: "#F97316", fontSize: 11, padding: "2px 8px", border: "1px solid #F97316", whiteSpace: "nowrap", fontFamily: "'IBM Plex Mono', monospace" }}>
                      <SparkleIcon size={10} /> merged
                    </span>
                  )}
                </div>
                {expanded === task.id && (
                  <div style={{ marginTop: 12, borderTop: "1px solid #D9D9D9", paddingTop: 12 }}>
                    <AIRationale text={`Task ${task.id}: ${task.title}. Source: ${task.source || task.source_type}. Priority: ${task.priority || "unset"}.`} />
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}

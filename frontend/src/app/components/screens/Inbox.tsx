import { useEffect, useMemo, useState, useCallback } from "react";
import { Search } from "lucide-react";
import { useSearchParams } from "react-router";
import { Card } from "../shared/Card";
import { SourceBadge } from "../shared/SourceBadge";
import { SparkleIcon } from "../shared/SparkleIcon";
import { TaskCard } from "../shared/TaskCard";
import { CreateTaskModal } from "../shared/CreateTaskModal";
import { getTasks, Task, WebSocketEvent } from "../../api/taskpilot";
import { useWebSocket } from "../../hooks/useWebSocket";

const FILTERS = ["All", "jira", "github", "slack", "outlook", "meetings"];

export function Inbox() {
  const [searchParams] = useSearchParams();
  const urlSearch = searchParams.get("search") || "";
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState("All");
  const [searchQuery, setSearchQuery] = useState(urlSearch);

  const handleWsEvent = useCallback((event: WebSocketEvent) => {
    if (event.event === "tasks_updated") {
      setTasks(Array.isArray(event.data) ? event.data as Task[] : []);
    }
  }, []);

  useWebSocket(handleWsEvent);

  useEffect(() => {
    getTasks()
      .then(r => setTasks(Array.isArray(r.tasks) ? r.tasks : []))
      .catch((err) => { console.error("Failed to load tasks:", err); setTasks([]); })
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    let result = tasks;
    if (activeFilter !== "All") {
      result = result.filter(t => (t.source || t.source_type || "").toLowerCase() === activeFilter.toLowerCase());
    }
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      result = result.filter(t => t.title?.toLowerCase().includes(q) || t.id?.toLowerCase().includes(q) || t.source?.toLowerCase().includes(q));
    }
    return result;
  }, [tasks, activeFilter, searchQuery]);

  const hiddenCount = tasks.filter(t => t.confidence != null && t.confidence >= 0.7).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <h2 style={{ margin: 0 }}>Unified Inbox</h2>
        <p style={{ color: "#7A7A7A", fontSize: 13, marginTop: 4 }}>
          {loading ? "Loading..." : `${tasks.length} tasks across all sources`}
        </p>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8, background: "#FFFFFF", borderRadius: 12, padding: "8px 14px", border: "1px solid #E9E4D8", maxWidth: 360 }}>
          <Search size={15} color="#B0A8A0" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search tasks..."
            style={{ flex: 1, border: "none", outline: "none", background: "none", fontSize: 13, color: "#111111" }}
          />
        </div>
        <div style={{ display: "flex", gap: 4 }}>
          {FILTERS.map((f) => (
            <button key={f} onClick={() => setActiveFilter(f)}
              style={{
                background: activeFilter === f ? "#0D0D0D" : "transparent",
                color: activeFilter === f ? "#FFFFFF" : "#7A7A7A",
                border: activeFilter === f ? "none" : "1px solid #E9E4D8",
                padding: "6px 14px", borderRadius: 10, fontSize: 12, cursor: "pointer",
                fontFamily: "'IBM Plex Mono', monospace", transition: "all 0.15s",
              }}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
        <CreateTaskModal onCreated={() => getTasks().then(r => setTasks(r.tasks)).catch(() => {})} />
      </div>

      {hiddenCount > 0 && (
        <Card variant="purple" shadow>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <SparkleIcon size={14} />
            <span style={{ fontSize: 13, fontWeight: 500 }}>AI Insight</span>
          </div>
          <span style={{ fontSize: 12, color: "#7A7A7A" }}>
            {hiddenCount} high-confidence task{hiddenCount > 1 ? "s" : ""} found from recent sources.{" "}
            <a href="/hidden" style={{ color: "#0D0D0D", fontWeight: 500 }}>View hidden tasks →</a>
          </span>
        </Card>
      )}

      {!loading && filtered.length === 0 && (
        <div style={{ textAlign: "center", color: "#7A7A7A", padding: 40, fontSize: 13 }}>
          {searchQuery.trim() ? `No tasks matching "${searchQuery}".` : "No tasks found for this filter."}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {filtered.map((task: any) => (
          <TaskCard key={task.id} task={task as Task} onUpdate={() => getTasks().then(r => setTasks(r.tasks)).catch(() => {})} />
        ))}
      </div>
    </div>
  );
}

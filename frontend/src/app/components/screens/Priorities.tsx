import { useEffect, useState, useCallback, useRef } from "react";
import { useDrag, useDrop } from "react-dnd";
import { toast } from "sonner";
import { Zap, TrendingUp, AlertTriangle, GripVertical } from "lucide-react";
import { Card } from "../shared/Card";
import { PriorityPill } from "../shared/PriorityPill";
import { SourceBadge } from "../shared/SourceBadge";
import { StatusPill } from "../shared/StatusPill";
import { getPlan, getDashboard, reorderTasks, LeverageTask, RankedTask, DeferredTask, WebSocketEvent } from "../../api/taskpilot";
import { useWebSocket } from "../../hooks/useWebSocket";

export function Priorities() {
  const [ranked, setRanked] = useState<RankedTask[]>([]);
  const [leverage, setLeverage] = useState<LeverageTask[]>([]);
  const [deferred, setDeferred] = useState<DeferredTask[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = () => {
    Promise.all([
      getPlan().catch(() => null),
      getDashboard().catch(() => null),
    ]).then(([plan, db]) => {
      const r = plan?.ranked_tasks ?? db?.plan?.ranked_tasks ?? [];
      const l = db?.dependency_analysis?.highest_leverage_tasks ?? plan?.highest_leverage_tasks ?? [];
      const d = plan?.deferred_tasks_detected ?? db?.deferred_tasks ?? [];
      setRanked(r);
      setLeverage(l);
      setDeferred(d);
    }).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  const handleWsEvent = useCallback((event: WebSocketEvent) => {
    if (event.event === "plan_updated" || event.event === "priorities_updated") {
      const p = event.data as any;
      if (p?.ranked_tasks) setRanked(p.ranked_tasks);
    }
  }, []);

  useWebSocket(handleWsEvent);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <h2 style={{ margin: 0 }}>Priorities</h2>
        <p style={{ color: "#7A7A7A", fontSize: 13, marginTop: 4 }}>
          {loading ? "Loading..." : `${ranked.length} ranked · ${leverage.length} leverage · ${deferred.length} deferred`}
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <Card variant="green" shadow>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
            <TrendingUp size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Highest Leverage Tasks</span>
          </div>
          {leverage.length > 0 ? leverage.slice(0, 5).map((lt: LeverageTask) => (
            <div key={lt.task_id} style={{ padding: "8px 0", borderBottom: "1px solid #E9E4D8", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontSize: 13, color: "#111111" }}>{lt.title}</div>
                <div style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", marginTop: 2 }}>
                  Unblocks {lt.blocks_directly} directly · {lt.blocks_transitively} transitively
                </div>
              </div>
              <div style={{ background: "#BFD78D", padding: "4px 8px", borderRadius: 8, fontSize: 11, fontWeight: 600 }}>L{lt.leverage_score.toFixed(1)}</div>
            </div>
          )) : <div style={{ color: "#7A7A7A", fontSize: 12 }}>Run the pipeline to identify leverage tasks.</div>}
        </Card>

        <Card variant="yellow" shadow>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
            <AlertTriangle size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Deferred Tasks</span>
          </div>
          {deferred.length > 0 ? deferred.slice(0, 5).map((dt: DeferredTask, i: number) => (
            <div key={i} style={{ padding: "8px 0", borderBottom: "1px solid #E9E4D8" }}>
              <div style={{ fontSize: 13, color: "#111111" }}>{dt.title}</div>
              <div style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", marginTop: 2 }}>
                Appeared in {dt.appeared_in_last_n_runs} runs · {dt.reason}
              </div>
            </div>
          )) : <div style={{ color: "#7A7A7A", fontSize: 12 }}>No deferred tasks detected.</div>}
        </Card>
      </div>

      <Card variant="blue" shadow>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Zap size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Ranked Tasks</span>
          </div>
          {ranked.length > 0 && (
            <button onClick={async () => {
              const ids = ranked.map(r => r.id);
              try {
                await reorderTasks(ids);
                toast.success("Order saved");
              } catch { toast.error("Failed to save order"); }
            }} style={{ background: "none", border: "1px solid #E9E4D8", padding: "4px 10px", borderRadius: 8, fontSize: 10, cursor: "pointer", color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>
              Save Order
            </button>
          )}
        </div>
        {ranked.length > 0 ? (
          <RankedTaskList tasks={ranked} onReorder={setRanked} />
        ) : (
          <div style={{ color: "#7A7A7A", fontSize: 12 }}>Run the pipeline to rank tasks.</div>
        )}
      </Card>
    </div>
  );
}

function RankedTaskItem({ task, index, moveItem }: { task: RankedTask; index: number; moveItem: (dragIndex: number, hoverIndex: number) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const [{ isDragging }, drag] = useDrag({ type: "RANKED_TASK", item: { index }, collect: (m) => ({ isDragging: m.isDragging() }) });
  const [, drop] = useDrop({ accept: "RANKED_TASK", hover: (item: { index: number }) => { if (item.index !== index) { moveItem(item.index, index); item.index = index; } } });
  drag(drop(ref));

  return (
    <div ref={ref} style={{ opacity: isDragging ? 0.4 : 1, display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "1px solid #E9E4D8", cursor: "grab" }}>
      <GripVertical size={14} style={{ color: "#B0A8A0", flexShrink: 0 }} />
      <div style={{ width: 28, height: 28, borderRadius: 8, background: "#F6F2E9", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 600, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", flexShrink: 0 }}>
        {index + 1}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, color: "#111111", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{task.title}</div>
        <div style={{ display: "flex", gap: 8, marginTop: 2, fontSize: 10, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>
          Score: {task.score.toFixed(2)}
        </div>
      </div>
      <SourceBadge source={task.source || task.source_type} />
      <PriorityPill level={(task.priority ?? "P3") as any} />
      <StatusPill status={task.status || "open"} />
    </div>
  );
}

function RankedTaskList({ tasks, onReorder }: { tasks: RankedTask[]; onReorder: (tasks: RankedTask[]) => void }) {
  const moveItem = (dragIndex: number, hoverIndex: number) => {
    const copy = [...tasks];
    const [removed] = copy.splice(dragIndex, 1);
    copy.splice(hoverIndex, 0, removed);
    onReorder(copy.map((t, i) => ({ ...t, rank: i + 1 })));
  };

  return (
    <div>
      {tasks.map((task, i) => (
        <RankedTaskItem key={task.id} task={task} index={i} moveItem={moveItem} />
      ))}
    </div>
  );
}

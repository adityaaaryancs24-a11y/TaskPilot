import { useRef } from "react";
import { useDrag, useDrop } from "react-dnd";
import { GripVertical } from "lucide-react";
import { SourceBadge } from "./SourceBadge";
import { PriorityPill } from "./PriorityPill";

const ITEM_TYPE = "TASK";

function DraggableItem({ task, index, moveItem, onEdit }: { task: any; index: number; moveItem: (dragIndex: number, hoverIndex: number) => void; onEdit?: (task: any) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const [{ isDragging }, drag] = useDrag({ type: ITEM_TYPE, item: { index }, collect: (monitor) => ({ isDragging: monitor.isDragging() }) });
  const [, drop] = useDrop({ accept: ITEM_TYPE, hover: (item: { index: number }) => { if (item.index !== index) { moveItem(item.index, index); item.index = index; } } });
  drag(drop(ref));

  return (
    <div ref={ref} style={{ opacity: isDragging ? 0.5 : 1, display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", background: "#FFFFFF", border: "1px solid #E9E4D8", borderRadius: 12, cursor: "grab", transition: "opacity 0.15s" }}>
      <GripVertical className="w-3.5 h-3.5" style={{ color: "#B0A8A0", flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontSize: 12, fontWeight: 500, margin: 0, color: "#111111", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{task.title}</p>
        <div style={{ display: "flex", gap: 4, marginTop: 2 }}>
          <SourceBadge source={task.source || task.source_type} />
          <PriorityPill level={(task.priority ?? "P3") as any} size="xs" />
        </div>
      </div>
      <span style={{ fontSize: 10, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>#{index + 1}</span>
    </div>
  );
}

export function DraggableTaskList({ tasks, onReorder, onEdit }: { tasks: any[]; onReorder: (tasks: any[]) => void; onEdit?: (task: any) => void }) {
  const moveItem = (dragIndex: number, hoverIndex: number) => {
    const copy = [...tasks];
    const [removed] = copy.splice(dragIndex, 1);
    copy.splice(hoverIndex, 0, removed);
    onReorder(copy);
  };

  if (tasks.length === 0) {
    return <div style={{ textAlign: "center", padding: 20, color: "#7A7A7A", fontSize: 12 }}>No tasks to reorder.</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {tasks.map((task, i) => (
        <DraggableItem key={task.id} task={task} index={i} moveItem={moveItem} onEdit={onEdit} />
      ))}
    </div>
  );
}

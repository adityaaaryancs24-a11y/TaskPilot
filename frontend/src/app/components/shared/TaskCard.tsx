import { useState } from "react";
import { Edit2, Save, X, Trash2 } from "lucide-react";
import { SourceBadge } from "./SourceBadge";
import { PriorityPill } from "./PriorityPill";
import { StatusToggle } from "./StatusToggle";
import { updateTask, deleteTask, Task, TaskStatus, Priority } from "../../api/taskpilot";
import { toast } from "sonner";

export function TaskCard({ task, onUpdate, onDelete }: { task: Task; onUpdate?: () => void; onDelete?: () => void }) {
  const [isEditing, setIsEditing] = useState(false);
  const [edited, setEdited] = useState({ title: task.title, description: task.description || "", priority: task.priority || "P2", status: task.status || "open", deadline: task.deadline || "" });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateTask(task.id, {
        title: edited.title,
        description: edited.description || null,
        priority: edited.priority as Priority,
        status: edited.status as TaskStatus,
        deadline: edited.deadline || null,
      });
      toast.success("Task updated");
      setIsEditing(false);
      onUpdate?.();
    } catch { toast.error("Failed to update"); }
    finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!confirm("Delete this task?")) return;
    setDeleting(true);
    try {
      await deleteTask(task.id);
      toast.success("Task deleted");
      onDelete?.();
    } catch { toast.error("Failed to delete"); }
    finally { setDeleting(false); }
  };

  const handleStatusChange = async (newStatus: string) => {
    try {
      await updateTask(task.id, { status: newStatus as TaskStatus });
      toast.success(`Task ${newStatus === "done" ? "completed" : "moved to " + newStatus}`);
      onUpdate?.();
    } catch { toast.error("Failed to update status"); }
  };

  if (isEditing) {
    return (
      <div className="bg-white rounded-3xl border border-[#F97316] p-4 shadow-md">
        <div className="space-y-3">
          <input type="text" value={edited.title} onChange={(e) => setEdited({ ...edited, title: e.target.value })}
            className="w-full px-3 py-2 border border-[#E9E4D8] rounded-xl focus:outline-none focus:border-[#F97316] text-sm" placeholder="Task title" />
          <textarea value={edited.description} onChange={(e) => setEdited({ ...edited, description: e.target.value })}
            className="w-full px-3 py-2 border border-[#E9E4D8] rounded-xl focus:outline-none focus:border-[#F97316] resize-none text-sm" placeholder="Description" rows={2} />
          <div className="flex gap-3 flex-wrap">
            <select value={edited.priority} onChange={(e) => setEdited({ ...edited, priority: e.target.value })}
              className="px-3 py-2 border border-[#E9E4D8] rounded-xl focus:outline-none focus:border-[#F97316] text-sm">
              <option value="P0">P0 - Critical</option>
              <option value="P1">P1 - High</option>
              <option value="P2">P2 - Medium</option>
              <option value="P3">P3 - Low</option>
            </select>
            <select value={edited.status} onChange={(e) => setEdited({ ...edited, status: e.target.value })}
              className="px-3 py-2 border border-[#E9E4D8] rounded-xl focus:outline-none focus:border-[#F97316] text-sm">
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="done">Done</option>
              <option value="blocked">Blocked</option>
              <option value="deferred">Deferred</option>
            </select>
            <input type="date" value={edited.deadline?.split("T")[0] || ""} onChange={(e) => setEdited({ ...edited, deadline: e.target.value })}
              className="px-3 py-2 border border-[#E9E4D8] rounded-xl focus:outline-none focus:border-[#F97316] text-sm" />
          </div>
        </div>
        <div className="flex gap-2 mt-3">
          <button onClick={handleSave} disabled={saving || !edited.title.trim()}
            className="px-4 py-2 bg-[#F97316] text-white rounded-xl hover:opacity-80 transition-opacity flex items-center gap-2 disabled:opacity-50 text-sm">
            <Save className="w-4 h-4" /> {saving ? "Saving..." : "Save"}
          </button>
          <button onClick={() => setIsEditing(false)}
            className="px-4 py-2 bg-[#F6F2E9] text-[#7A7A7A] rounded-xl hover:bg-[#E9E4D8] transition-colors flex items-center gap-2 text-sm">
            <X className="w-4 h-4" /> Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-3xl border border-[#E9E4D8] p-4 hover:shadow-md transition-shadow group">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <SourceBadge source={task.source || task.source_type} />
            <PriorityPill level={(task.priority ?? "P3") as any} />
            <StatusToggle taskId={task.id} currentStatus={task.status || "open"} onStatusChange={handleStatusChange} size="sm" />
          </div>
          <h4 className="font-medium text-[#111111] text-sm leading-snug">{task.title}</h4>
          {task.description && <p className="text-xs text-[#7A7A7A] mt-1 line-clamp-2">{task.description}</p>}
          {task.deadline && <p className="text-[10px] text-[#7A7A7A] mt-1.5 font-mono">Due: {new Date(task.deadline).toLocaleDateString()}</p>}
        </div>
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2 flex-shrink-0">
          <button onClick={() => setIsEditing(true)} className="p-1.5 rounded-lg hover:bg-[#F6F2E9] transition-colors" title="Edit">
            <Edit2 className="w-3.5 h-3.5 text-[#7A7A7A]" />
          </button>
          <button onClick={handleDelete} disabled={deleting} className="p-1.5 rounded-lg hover:bg-[#F7C5E6] transition-colors" title="Delete">
            <Trash2 className="w-3.5 h-3.5 text-[#7A7A7A]" />
          </button>
        </div>
      </div>
    </div>
  );
}

import { useState } from "react";
import { Plus, X } from "lucide-react";
import { createTask, Priority, TaskStatus } from "../../api/taskpilot";
import { toast } from "sonner";

export function CreateTaskModal({ onCreated }: { onCreated?: () => void }) {
  const [isOpen, setIsOpen] = useState(false);
  const [data, setData] = useState({ title: "", description: "", priority: "P2", deadline: "" });
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!data.title.trim()) return;
    setCreating(true);
    try {
      await createTask({
        title: data.title,
        description: data.description || undefined,
        priority: data.priority as Priority,
        status: "open" as TaskStatus,
        deadline: data.deadline || null,
      });
      toast.success("Task created");
      setData({ title: "", description: "", priority: "P2", deadline: "" });
      setIsOpen(false);
      onCreated?.();
    } catch { toast.error("Failed to create"); }
    finally { setCreating(false); }
  };

  return (
    <>
      <button onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 px-4 py-2 bg-[#F97316] text-white rounded-2xl hover:opacity-80 transition-opacity text-sm">
        <Plus className="w-4 h-4" /> New Task
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20" onClick={() => setIsOpen(false)}>
          <div className="bg-white rounded-3xl border border-[#E9E4D8] p-6 max-w-lg w-full mx-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-[#111111]">Create New Task</h3>
              <button onClick={() => setIsOpen(false)} className="p-1 rounded-lg hover:bg-[#F6F2E9]"><X className="w-4 h-4" /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-[#111111]">Title *</label>
                <input type="text" value={data.title} onChange={(e) => setData({ ...data, title: e.target.value })}
                  className="w-full mt-1 px-3 py-2 border border-[#E9E4D8] rounded-xl focus:outline-none focus:border-[#F97316] text-sm" placeholder="Enter task title" />
              </div>
              <div>
                <label className="text-xs font-medium text-[#111111]">Description</label>
                <textarea value={data.description} onChange={(e) => setData({ ...data, description: e.target.value })}
                  className="w-full mt-1 px-3 py-2 border border-[#E9E4D8] rounded-xl focus:outline-none focus:border-[#F97316] resize-none text-sm" rows={3} placeholder="Optional description" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-[#111111]">Priority</label>
                  <select value={data.priority} onChange={(e) => setData({ ...data, priority: e.target.value })}
                    className="w-full mt-1 px-3 py-2 border border-[#E9E4D8] rounded-xl focus:outline-none focus:border-[#F97316] text-sm">
                    <option value="P0">P0 - Critical</option>
                    <option value="P1">P1 - High</option>
                    <option value="P2">P2 - Medium</option>
                    <option value="P3">P3 - Low</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-[#111111]">Deadline</label>
                  <input type="date" value={data.deadline} onChange={(e) => setData({ ...data, deadline: e.target.value })}
                    className="w-full mt-1 px-3 py-2 border border-[#E9E4D8] rounded-xl focus:outline-none focus:border-[#F97316] text-sm" />
                </div>
              </div>
              <p className="text-xs text-[#7A7A7A]">Task will be automatically prioritized in your plan.</p>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setIsOpen(false)} className="flex-1 px-4 py-2 bg-[#F6F2E9] text-[#7A7A7A] rounded-xl hover:bg-[#E9E4D8] transition-colors text-sm">Cancel</button>
              <button onClick={handleCreate} disabled={!data.title.trim() || creating}
                className="flex-1 px-4 py-2 bg-[#F97316] text-white rounded-xl hover:opacity-80 transition-opacity disabled:opacity-50 text-sm">
                {creating ? "Creating..." : "Create Task"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

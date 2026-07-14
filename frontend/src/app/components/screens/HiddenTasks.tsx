import { useEffect, useState } from "react";
import { Sparkles, RefreshCw, FileText, AlertCircle, CheckCircle, Plus, X, Pencil } from "lucide-react";
import { Card } from "../shared/Card";
import { getRecentExtractions, injectTask, convertHiddenTask, ExtractionItem } from "../../api/taskpilot";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "#BFD78D" : pct >= 60 ? "#F5D66E" : "#F7C5E6";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 6, background: "#E9E4D8", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 3, transition: "width 0.5s" }} />
      </div>
      <span style={{ color: "#0D0D0D", fontSize: 11, fontWeight: 600, fontFamily: "'IBM Plex Mono', monospace", minWidth: 36, textAlign: "right" }}>{pct}%</span>
    </div>
  );
}

function ConvertDialog({ item, open, onOpenChange, onConverted }: { item: ExtractionItem; open: boolean; onOpenChange: (open: boolean) => void; onConverted: (id: string) => void }) {
  const [title, setTitle] = useState(item.title);
  const [priority, setPriority] = useState(item.priority || "P3");
  const [converting, setConverting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setTitle(item.title);
      setPriority(item.priority || "P3");
      setError("");
    }
  }, [open, item]);

  const handleConvert = async () => {
    if (!title.trim()) { setError("Title is required"); return; }
    setConverting(true);
    setError("");
    try {
      await convertHiddenTask({
        task_id: item.task_id,
        title: title.trim(),
        priority: priority as any,
      });
      onConverted(item.task_id);
      onOpenChange(false);
    } catch (err) {
      setError("Failed to convert. Try again.");
      console.error(err);
    }
    finally { setConverting(false); }
  };

  const handleApproveDirect = async () => {
    setConverting(true);
    try {
      await injectTask({
        title: item.title,
        description: item.raw_text?.slice(0, 500),
        source_type: item.source_type || "email",
        priority: item.priority || undefined,
        deadline: item.deadline || undefined,
      });
      onConverted(item.task_id);
      onOpenChange(false);
    } catch (err) { console.error(err); }
    finally { setConverting(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent style={{ background: "#FFFDF8", border: "1px solid #E9E4D8", borderRadius: 20, maxWidth: 440, padding: 24 }}>
        <DialogHeader>
          <DialogTitle style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 16 }}>Convert to Task</DialogTitle>
          <DialogDescription style={{ fontSize: 12, color: "#7A7A7A", marginTop: 4 }}>
            Review and edit the task before adding it to your tracked tasks.
          </DialogDescription>
        </DialogHeader>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 8 }}>
          <div>
            <label style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 4, display: "block" }}>Title</label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Task title" style={{ borderRadius: 10, border: "1px solid #E9E4D8", fontSize: 13 }} />
          </div>
          <div>
            <label style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 4, display: "block" }}>Priority</label>
            <div style={{ display: "flex", gap: 6 }}>
              {["P1", "P2", "P3"].map((p) => (
                <button key={p} onClick={() => setPriority(p)}
                  style={{
                    flex: 1, padding: "6px 0", borderRadius: 10, fontSize: 12, fontFamily: "'IBM Plex Mono', monospace", cursor: "pointer",
                    background: priority === p ? (p === "P1" ? "#F7C5E6" : p === "P2" ? "#F5D66E" : "#BFD78D") : "transparent",
                    border: priority === p ? "none" : "1px solid #E9E4D8",
                    color: priority === p ? "#111111" : "#7A7A7A",
                    transition: "all 0.15s",
                  }}>
                  {p}
                </button>
              ))}
            </div>
          </div>
          {item.raw_text && (
            <div>
              <label style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 4, display: "block" }}>Source Text</label>
              <div style={{ background: "#F6F2E9", borderRadius: 10, padding: "8px 12px", fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", lineHeight: 1.5, maxHeight: 80, overflow: "auto" }}>
                {item.raw_text.slice(0, 300)}
              </div>
            </div>
          )}
          {error && <div style={{ color: "#E86A6A", fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>{error}</div>}
        </div>
        <DialogFooter style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16 }}>
          <Button variant="outline" onClick={() => onOpenChange(false)} style={{ borderRadius: 10, fontSize: 12, border: "1px solid #E9E4D8" }}>
            Cancel
          </Button>
          <Button onClick={handleApproveDirect} disabled={converting} variant="secondary" style={{ borderRadius: 10, fontSize: 12, background: "#BFD78D", color: "#111111", border: "none" }}>
            <CheckCircle size={12} /> {converting ? "Adding..." : "Quick Approve"}
          </Button>
          <Button onClick={handleConvert} disabled={converting} style={{ borderRadius: 10, fontSize: 12, background: "#0D0D0D", color: "#FFFFFF", border: "none" }}>
            <Plus size={12} /> {converting ? "Converting..." : "Convert with Edits"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function HiddenTaskCard({ item, onApproved }: { item: ExtractionItem; onApproved: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false);
  const [approving, setApproving] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);

  const handleApprove = async () => {
    setApproving(true);
    try {
      await injectTask({
        title: item.title,
        description: item.raw_text?.slice(0, 500),
        source_type: item.source_type || "email",
        priority: item.priority || undefined,
        deadline: item.deadline || undefined,
      });
      onApproved(item.task_id);
    } catch (err) { console.error(err); }
    finally { setApproving(false); }
  };

  return (
    <Card variant="purple" shadow style={{ overflow: "hidden" }}>
      <div style={{ display: "flex", gap: 16 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
            <FileText size={14} color="#7A7A7A" />
            <span style={{ fontSize: 12, color: "#7A7A7A", fontWeight: 500 }}>
              {item.source_type === "email" ? "📧" : item.source_type === "transcript" ? "📝" : "🔗"} From: {item.source || item.source_type}
            </span>
          </div>
          <div style={{ marginBottom: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 500, color: "#111111" }}>{item.title}</span>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
            <span style={{ color: "#7A7A7A", fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>{item.task_id}</span>
          </div>
          <ConfidenceBar value={item.confidence || 0} />
        </div>
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <button onClick={handleApprove} disabled={approving}
          style={{ background: "#BFD78D", color: "#0D0D0D", border: "none", padding: "6px 14px", borderRadius: 10, fontSize: 11, fontWeight: 600, cursor: approving ? "wait" : "pointer", fontFamily: "'IBM Plex Mono', monospace", opacity: approving ? 0.7 : 1 }}>
          <CheckCircle size={12} style={{ marginRight: 4, display: "inline" }} /> {approving ? "Approving..." : "Approve"}
        </button>
        <button onClick={() => setDialogOpen(true)}
          style={{ background: "#F7C5E6", color: "#111111", border: "none", padding: "6px 14px", borderRadius: 10, fontSize: 11, fontWeight: 600, cursor: "pointer", fontFamily: "'IBM Plex Mono', monospace" }}>
          <Pencil size={12} style={{ marginRight: 4, display: "inline" }} /> Convert to Task
        </button>
        <button onClick={() => setExpanded(!expanded)} style={{ background: "none", border: "1px solid #E9E4D8", padding: "6px 14px", borderRadius: 10, fontSize: 11, color: "#7A7A7A", cursor: "pointer", fontFamily: "'IBM Plex Mono', monospace" }}>
          {expanded ? "Hide Source" : "View Source"}
        </button>
      </div>
      {expanded && (
        <div style={{ marginTop: 12, borderTop: "1px solid #E9E4D8", paddingTop: 12 }}>
          <div style={{ background: "#F6F2E9", borderRadius: 12, padding: "10px 14px", fontSize: 12, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", lineHeight: 1.6, maxHeight: 120, overflow: "auto" }}>
            {item.raw_text?.split("\n").slice(0, 10).map((l: string, i: number) => <div key={i}>{l || "\u00A0"}</div>)}
          </div>
        </div>
      )}
      <ConvertDialog item={item} open={dialogOpen} onOpenChange={setDialogOpen} onConverted={onApproved} />
    </Card>
  );
}

export function HiddenTasks() {
  const [extractions, setExtractions] = useState<ExtractionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const data = await getRecentExtractions();
      setExtractions(data.extractions || []);
      setTotal(data.total || 0);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  const handleApproved = (taskId: string) => {
    setExtractions(prev => prev.filter(e => e.task_id !== taskId));
    setTotal(prev => Math.max(0, prev - 1));
  };

  const highConf = extractions.filter(e => (e.confidence || 0) >= 0.7).length;
  const pending = extractions.filter(e => (e.confidence || 0) < 0.7).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <h2 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
          <Sparkles size={20} /> Hidden Tasks Found
        </h2>
        <p style={{ color: "#7A7A7A", fontSize: 13, marginTop: 4 }}>
          AI-extracted action items from emails, meetings, and unstructured sources
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
        <Card variant="green" shadow>
          <div style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 }}>Total Found</div>
          <div style={{ fontSize: 28, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif" }}>{total}</div>
        </Card>
        <Card variant="blue" shadow>
          <div style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 }}>High Confidence</div>
          <div style={{ fontSize: 28, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif" }}>{highConf}</div>
        </Card>
        <Card variant="yellow" shadow>
          <div style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 }}>Pending Review</div>
          <div style={{ fontSize: 28, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif" }}>{pending}</div>
        </Card>
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={fetchData} style={{ background: "#0D0D0D", color: "#FFFFFF", border: "none", padding: "10px 20px", borderRadius: 12, fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontFamily: "'IBM Plex Mono', monospace" }}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", color: "#7A7A7A", padding: 40, fontSize: 13 }}>Loading hidden tasks...</div>
      ) : extractions.length === 0 ? (
        <Card style={{ textAlign: "center", padding: 40 }}>
          <AlertCircle size={24} style={{ margin: "0 auto 12px", opacity: 0.4 }} />
          <p style={{ color: "#7A7A7A", fontSize: 13, margin: 0 }}>No hidden tasks found. Run the pipeline to extract tasks from emails and meetings.</p>
        </Card>
      ) : (
        extractions.map((item: ExtractionItem) => <HiddenTaskCard key={item.task_id} item={item} onApproved={handleApproved} />)
      )}
    </div>
  );
}

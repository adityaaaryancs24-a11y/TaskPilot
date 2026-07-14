import { useState } from "react";

function derivePreference(task: any): string {
  const title = (task.title || "").toLowerCase();
  const src = (task.source_type || "").toLowerCase();
  if (["security", "audit", "token", "vulnerability"].some((k) => title.includes(k))) return "prefer_security";
  if (["ui", "dashboard", "safari", "render", "chart"].some((k) => title.includes(k))) return "prefer_ui_bugs";
  if (["database", "migration", "api", "sync", "websocket"].some((k) => title.includes(k))) return "prefer_backend";
  if (["memory", "leak", "latency", "performance"].some((k) => title.includes(k))) return "prefer_performance";
  if (["refactor", "cleanup", "docs"].some((k) => title.includes(k))) return "prefer_refactors";
  if (["github", "jira", "slack", "connector"].some((k) => title.includes(k))) return "prefer_integrations";
  return `prefer_${src}`;
}

export function FeedbackButton({ task, compact }: { task: any; compact?: boolean }) {
  const [sent, setSent] = useState(false);

  const handleUpvote = async () => {
    if (sent) return;
    const preference = derivePreference(task);
    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_id: task.id, action: "upvote", preference }),
      });
      setSent(true);
      setTimeout(() => setSent(false), 2000);
    } catch {}
  };

  return (
    <button
      onClick={handleUpvote}
      title="Upvote this task type"
      style={{
        background: sent ? "#0D0D0D" : "none",
        border: sent ? "none" : "1px solid #E9E4D8",
        cursor: "pointer",
        color: sent ? "#FFFFFF" : "#7A7A7A",
        padding: compact ? "3px 8px" : "4px 10px",
        borderRadius: 8, fontSize: compact ? 10 : 11, fontWeight: 500,
        fontFamily: "'IBM Plex Mono', monospace",
        transition: "all 0.2s",
      }}
    >
      {sent ? "Learned!" : "Teach"}
    </button>
  );
}

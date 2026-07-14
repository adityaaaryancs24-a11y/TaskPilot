import { useState } from "react";
import { ChevronDown, GitMerge, Info } from "lucide-react";
import { Card } from "./Card";
import { SourceBadge } from "./SourceBadge";
import { PriorityPill } from "./PriorityPill";
import { StatusPill } from "./StatusPill";
import { SparkleIcon } from "./SparkleIcon";
import type { DedupGroup } from "@/app/api/taskpilot";

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "#BFD78D" : pct >= 60 ? "#F5D66E" : "#F7C5E6";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span style={{ fontSize: 11, color: "#7A7A7A", whiteSpace: "nowrap" }}>Match confidence</span>
      <div style={{ flex: 1, height: 6, borderRadius: 3, background: "#E9E4D8", overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", borderRadius: 3, background: color, transition: "width 0.5s" }} />
      </div>
      <span style={{ fontSize: 11, color: "#0D0D0D", fontWeight: 600, fontFamily: "'IBM Plex Mono', monospace", minWidth: 36, textAlign: "right" }}>{pct}%</span>
    </div>
  );
}

function SubTaskCard({ task }: { task: DedupGroup["tasks"][number] }) {
  return (
    <div style={{ borderRadius: 10, border: "1px solid #E9E4D8", background: "#F6F2E9", padding: "10px 14px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <SourceBadge source={task.source} />
        <span style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>{task.id}</span>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
          {task.priority && <PriorityPill level={task.priority} />}
          <StatusPill status={task.status || "open"} />
        </div>
      </div>
      <p style={{ margin: 0, fontSize: 13, color: "#111111", lineHeight: 1.4 }}>{task.title}</p>
      {task.deadline && (
        <p style={{ margin: "4px 0 0", fontSize: 11, color: "#7A7A7A" }}>
          Due {task.deadline}{task.owner ? ` · ${task.owner}` : ""}
        </p>
      )}
    </div>
  );
}

type MergedTaskCardProps = {
  group: DedupGroup;
  defaultExpanded?: boolean;
};

export function MergedTaskCard({ group, defaultExpanded = false }: MergedTaskCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const uniqueSources = [...new Set(group.tasks.map((t) => t.source))];

  return (
    <Card shadow role="region" aria-label={`Merged from ${group.merged_count} sources`}>
      <button onClick={() => setExpanded((v) => !v)}
        style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", background: "none", border: "none", padding: 0, cursor: "pointer", textAlign: "left" }}
        aria-expanded={expanded}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{
            display: "flex", alignItems: "center", justifyContent: "center",
            width: 28, height: 28, borderRadius: 8,
            background: expanded ? "#DCC7F7" : "#F6F2E9",
            color: expanded ? "#0D0D0D" : "#7A7A7A",
            transition: "all 0.15s",
          }}>
            <GitMerge size={14} />
          </span>
          <span style={{ fontSize: 13, fontWeight: 500, color: "#111111" }}>
            Merged from <span style={{ color: "#0D0D0D", fontWeight: 600 }}>{group.merged_count} source{group.merged_count !== 1 ? "s" : ""}</span>
          </span>
        </div>
        <ChevronDown size={15} color="#7A7A7A"
          style={{ transition: "transform 0.15s", transform: expanded ? "rotate(0)" : "rotate(-90deg)" }} />
      </button>

      <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap" }}>
          {uniqueSources.map((src) => <SourceBadge key={src} source={src} />)}
        </div>
        <ConfidenceBar value={group.match_confidence} />
      </div>

      {expanded && (
        <div style={{ marginTop: 12, borderTop: "1px solid #E9E4D8", paddingTop: 12 }}>
          <div style={{ display: "flex", gap: 6, padding: "10px 0", fontSize: 13, color: "#7A7A7A", lineHeight: 1.5 }}>
            <Info size={14} style={{ flexShrink: 0, marginTop: 2 }} />
            <p style={{ margin: 0 }}>{group.reasoning}</p>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 4 }}>
            <p style={{ margin: 0, fontSize: 11, fontWeight: 600, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase", letterSpacing: "0.04em" }}>Merged tasks</p>
            {group.tasks.map((task) => <SubTaskCard key={task.id} task={task} />)}
          </div>
        </div>
      )}
    </Card>
  );
}

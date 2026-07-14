import { SparkleIcon } from "./SparkleIcon";
import { SourceBadge } from "./SourceBadge";
import { PriorityPill } from "./PriorityPill";
import { StatusPill } from "./StatusPill";
import { Card } from "./Card";
import type { ExtractionItem } from "@/app/api/taskpilot";

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "#BFD78D" : pct >= 60 ? "#F5D66E" : "#F7C5E6";
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      color: "#0D0D0D", fontSize: 11, fontWeight: 500,
      padding: "4px 12px", borderRadius: 8,
      background: color, fontFamily: "'IBM Plex Mono', monospace",
    }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#0D0D0D", display: "inline-block" }} />
      {pct}% confidence
    </span>
  );
}

function RawSourcePanel({ raw_text }: { raw_text: string }) {
  const lines = raw_text.split("\n").slice(0, 20);
  return (
    <div style={{ flex: 1, minWidth: 0, borderRadius: 12, overflow: "hidden", display: "flex", flexDirection: "column", background: "#F6F2E9" }}>
      <div style={{ padding: "8px 14px", fontSize: 11, fontWeight: 600, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase", letterSpacing: "0.04em", background: "#E9E4D8" }}>
        Raw source
      </div>
      <div style={{ padding: "12px 14px", overflow: "auto", flex: 1 }}>
        {lines.map((line, i) => (
          <div key={i} style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, lineHeight: 1.6, color: "#7A7A7A", whiteSpace: "pre-wrap", wordBreak: "break-word", opacity: line.trim() ? 1 : 0.3 }}>
            {line || "\u00A0"}
          </div>
        ))}
      </div>
    </div>
  );
}

function ExtractedTaskPanel({ item }: { item: ExtractionItem }) {
  return (
    <div style={{ flex: 1, minWidth: 0, borderRadius: 12, overflow: "hidden", display: "flex", flexDirection: "column", background: "#FFFFFF", border: "1px solid #E9E4D8" }}>
      <div style={{ padding: "8px 14px", borderBottom: "1px solid #E9E4D8", display: "flex", alignItems: "center", gap: 6, fontSize: 11, fontWeight: 600, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase", letterSpacing: "0.04em", background: "#F6F2E9" }}>
        <SparkleIcon size={12} />
        AI-Extracted task
      </div>
      <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 12, flex: 1 }}>
        <div>
          <div style={{ color: "#7A7A7A", fontSize: 11, marginBottom: 2 }}>Title</div>
          <div style={{ color: "#111111", fontSize: 14, fontWeight: 500, lineHeight: 1.4 }}>{item.title}</div>
        </div>
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          {item.priority && (
            <div>
              <div style={{ color: "#7A7A7A", fontSize: 11, marginBottom: 3 }}>Priority</div>
              <PriorityPill level={item.priority} />
            </div>
          )}
          {item.deadline && (
            <div>
              <div style={{ color: "#7A7A7A", fontSize: 11, marginBottom: 3 }}>Due date</div>
              <span style={{ color: "#111111", fontSize: 13 }}>{item.deadline}</span>
            </div>
          )}
          <div>
            <div style={{ color: "#7A7A7A", fontSize: 11, marginBottom: 3 }}>Status</div>
            <StatusPill status={item.status || "open"} />
          </div>
        </div>
        <div>
          <div style={{ color: "#7A7A7A", fontSize: 11, marginBottom: 3 }}>Source</div>
          <SourceBadge source={item.source} />
        </div>
        {item.confidence != null && (
          <div>
            <div style={{ color: "#7A7A7A", fontSize: 11, marginBottom: 4 }}>Confidence</div>
            <ConfidenceBadge value={item.confidence} />
          </div>
        )}
        {item.source_sentence && (
          <div>
            <div style={{ color: "#7A7A7A", fontSize: 11, marginBottom: 2 }}>Source sentence</div>
            <div style={{ color: "#7A7A7A", fontSize: 12, fontStyle: "italic", lineHeight: 1.5, padding: "8px 10px", background: "#F6F2E9", borderRadius: 10 }}>
              &ldquo;{item.source_sentence}&rdquo;
            </div>
          </div>
        )}
        <div style={{ marginTop: "auto", paddingTop: 10, borderTop: "1px solid #E9E4D8" }}>
          <a href={`/tasks?task=${item.task_id}`} style={{ color: "#0D0D0D", fontSize: 12, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 4, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 500 }}>
            Trace to source &rarr;
          </a>
        </div>
      </div>
    </div>
  );
}

type ExtractionVisualizationProps = {
  item: ExtractionItem;
};

export function ExtractionVisualization({ item }: ExtractionVisualizationProps) {
  return (
    <Card shadow role="region" aria-label="Extraction visualization">
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
        <SparkleIcon size={13} />
        <span style={{ color: "#0D0D0D", fontSize: 12, fontWeight: 500 }}>Extraction</span>
        <span style={{ color: "#7A7A7A", fontSize: 12, fontFamily: "'IBM Plex Mono', monospace", marginLeft: "auto" }}>{item.task_id}</span>
      </div>
      <div style={{ display: "flex", gap: 12 }}>
        <RawSourcePanel raw_text={item.raw_text} />
        <ExtractedTaskPanel item={item} />
      </div>
    </Card>
  );
}

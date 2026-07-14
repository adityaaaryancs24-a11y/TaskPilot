import { useEffect, useState } from "react";
import { Sparkles, RefreshCw, AlertCircle } from "lucide-react";
import { AppHeader } from "../shared/AppHeader";
import { SourceBadge } from "../shared/SourceBadge";
import { PriorityPill } from "../shared/PriorityPill";
import { SparkleIcon } from "../shared/SparkleIcon";
import { getRecentExtractions } from "../../api/taskpilot";

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "#16A34A" : pct >= 60 ? "#D97706" : "#DC2626";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 4, background: "#E5E5E5", overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, transition: "width 0.5s ease" }} />
      </div>
      <span style={{ color, fontSize: 10, fontWeight: 600, fontFamily: "'IBM Plex Mono', monospace", minWidth: 32, textAlign: "right" }}>{pct}%</span>
    </div>
  );
}

function SourcePanel({ raw_text, source_sentence }: { raw_text: string; source_sentence?: string | null }) {
  const lines = raw_text.split("\n").slice(0, 15);
  return (
    <div style={{ border: "1px solid #D9D9D9", overflow: "hidden", background: "#F8F8F6" }}>
      <div style={{ padding: "6px 12px", borderBottom: "1px solid #D9D9D9", fontSize: 10, fontWeight: 600, color: "#7A7A7A", letterSpacing: "0.06em", textTransform: "uppercase", background: "#F0F0EE", display: "flex", alignItems: "center", gap: 6, fontFamily: "'IBM Plex Mono', monospace" }}>
        Source Text
      </div>
      <div style={{ padding: "10px 12px", maxHeight: 200, overflow: "auto" }}>
        {lines.map((line, i) => (
          <div key={i} style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 11, lineHeight: 1.6,
            color: "#7A7A7A",
            whiteSpace: "pre-wrap", wordBreak: "break-word",
          }}>
            {line || "\u00A0"}
          </div>
        ))}
      </div>
    </div>
  );
}

function ExtractionItemCard({ item }: { item: any }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={{ border: "1px solid #D9D9D9", overflow: "hidden", background: "#FFFFFF" }}>
      <div style={{ display: "flex", gap: 12, padding: "14px 16px" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
            <SparkleIcon size={12} />
            <span style={{ fontSize: 13, fontWeight: 500, color: "#111111" }}>{item.title}</span>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
            <SourceBadge source={item.source} />
            {item.priority && <PriorityPill level={item.priority} />}
            <span style={{ fontSize: 10, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>{item.task_id}</span>
          </div>
          <div style={{ display: "flex", gap: 16, fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>
            <span>Status: {item.status || "open"}</span>
            {item.deadline && <span>Due: {new Date(item.deadline).toLocaleDateString()}</span>}
            <span>Grounded: {item.grounded ? "Yes" : "No"}</span>
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6, minWidth: 140 }}>
          <ConfidenceBar value={item.confidence || 0} />
          <button onClick={() => setExpanded(!expanded)}
            style={{ background: "none", border: "1px solid #D9D9D9", padding: "4px 10px", color: "#7A7A7A", fontSize: 10, cursor: "pointer", fontFamily: "'IBM Plex Mono', monospace" }}>
            {expanded ? "Hide source" : "View source"}
          </button>
        </div>
      </div>
      {expanded && (
        <div style={{ padding: "0 16px 14px 16px", borderTop: "1px solid #D9D9D9", paddingTop: 10 }}>
          <SourcePanel raw_text={item.raw_text} source_sentence={item.source_sentence} />
          {item.source_sentence && (
            <div style={{ marginTop: 8, padding: "8px 10px", border: "1px solid #D9D9D9", fontSize: 11, fontStyle: "italic", color: "#7A7A7A", background: "#F8F8F6" }}>
              Source sentence: "{item.source_sentence}"
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ExtractionScreen() {
  const [extractions, setExtractions] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const data = await getRecentExtractions();
      setExtractions(data.extractions || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error("Failed to fetch extractions:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const highConf = extractions.filter(e => (e.confidence || 0) >= 0.7).length;
  const medConf = extractions.filter(e => (e.confidence || 0) >= 0.4 && (e.confidence || 0) < 0.7).length;
  const lowConf = extractions.filter(e => (e.confidence || 0) < 0.4).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <AppHeader />
      <main style={{ flex: 1, overflow: "auto", padding: "24px 28px", display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
              <Sparkles size={18} color="#F97316" /> Extraction Visualization
            </h2>
            <p style={{ color: "#7A7A7A", fontSize: 12, marginTop: 2 }}>
              See how AI extracts structured tasks from unstructured text
            </p>
          </div>
          <button onClick={fetchData}
            style={{ background: "none", border: "1px solid #D9D9D9", padding: "8px 14px", color: "#7A7A7A", fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontFamily: "'IBM Plex Mono', monospace" }}>
            <RefreshCw size={13} /> Refresh
          </button>
        </div>

        {/* Stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          <div style={{ border: "1px solid #D9D9D9", padding: "14px 16px", background: "#FFFFFF" }}>
            <div style={{ color: "#7A7A7A", fontSize: 10, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6, fontFamily: "'IBM Plex Mono', monospace" }}>Total Extractions</div>
            <div style={{ color: "#111111", fontSize: 22, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif" }}>{total}</div>
          </div>
          <div style={{ border: "1px solid #D9D9D9", padding: "14px 16px", background: "#FFFFFF" }}>
            <div style={{ color: "#7A7A7A", fontSize: 10, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6, fontFamily: "'IBM Plex Mono', monospace" }}>High Confidence (≥70%)</div>
            <div style={{ color: "#16A34A", fontSize: 22, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif" }}>{highConf}</div>
          </div>
          <div style={{ border: "1px solid #D9D9D9", padding: "14px 16px", background: "#FFFFFF" }}>
            <div style={{ color: "#7A7A7A", fontSize: 10, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6, fontFamily: "'IBM Plex Mono', monospace" }}>Medium (40-70%)</div>
            <div style={{ color: "#D97706", fontSize: 22, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif" }}>{medConf}</div>
          </div>
          <div style={{ border: "1px solid #D9D9D9", padding: "14px 16px", background: "#FFFFFF" }}>
            <div style={{ color: "#7A7A7A", fontSize: 10, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6, fontFamily: "'IBM Plex Mono', monospace" }}>Low (&lt;40%)</div>
            <div style={{ color: "#DC2626", fontSize: 22, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif" }}>{lowConf}</div>
          </div>
        </div>

        {/* Extraction list */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {loading ? (
            <div style={{ textAlign: "center", color: "#7A7A7A", padding: 40, fontSize: 13 }}>Loading extractions...</div>
          ) : extractions.length === 0 ? (
            <div style={{ textAlign: "center", color: "#7A7A7A", padding: 40, fontSize: 13 }}>
              <AlertCircle size={24} style={{ margin: "0 auto 12px", opacity: 0.4 }} />
              No extractions available. Run the pipeline to see AI-extracted tasks.
            </div>
          ) : (
            extractions.map((item: any) => (
              <ExtractionItemCard key={item.task_id} item={item} />
            ))
          )}
        </div>
      </main>
    </div>
  );
}

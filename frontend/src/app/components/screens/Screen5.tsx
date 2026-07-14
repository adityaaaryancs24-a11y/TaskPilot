import { useEffect, useState } from "react";
import { Copy } from "lucide-react";
import { AppHeader } from "../shared/AppHeader";
import { StatusPill } from "../shared/StatusPill";
import { SparkleIcon } from "../shared/SparkleIcon";
import { getWeeklySummary, WeeklySummaryResponse } from "../../api/taskpilot";

export function Screen5() {
  const [summary, setSummary] = useState<WeeklySummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    getWeeklySummary()
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <AppHeader />
      <main style={{ flex: 1, overflow: "auto", padding: "28px" }}>
        <div style={{ marginBottom: 24 }}>
          <div style={{ color: "#7A7A7A", fontSize: 12, marginBottom: 4, fontFamily: "'IBM Plex Mono', monospace" }}>Week of</div>
          <h2 style={{ margin: 0 }}>
            {new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" })} – Current
          </h2>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 24 }}>
          {[
            { label: "Tasks tracked", value: loading ? "--" : (summary ? "Live" : "0"), sub: "Live from pipeline" },
            { label: "Sources", value: "6", sub: "connected" },
            { label: "LLM extractions", value: loading ? "--" : (summary ? "Active" : "0"), sub: "per pipeline run" },
            { label: "Alerts generated", value: loading ? "--" : (summary ? "Active" : "0"), sub: "auto-detected" },
          ].map((m) => (
            <div key={m.label} style={{ border: "1px solid #D9D9D9", padding: "16px 18px", background: "#FFFFFF" }}>
              <div style={{ color: "#7A7A7A", fontSize: 11, marginBottom: 8, fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase", letterSpacing: "0.04em" }}>{m.label}</div>
              <div style={{ color: "#111111", fontSize: 28, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif", lineHeight: 1, marginBottom: 6 }}>{m.value}</div>
              <div style={{ color: "#7A7A7A", fontSize: 11 }}>{m.sub}</div>
            </div>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20, marginBottom: 20 }}>
          <div style={{ border: "1px solid #D9D9D9", padding: "20px", background: "#FFFFFF" }}>
            <div style={{ color: "#7A7A7A", fontSize: 12, fontWeight: 500, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 16, fontFamily: "'IBM Plex Mono', monospace" }}>
              Weekly Overview
            </div>
            <p style={{ color: "#7A7A7A", fontSize: 13, lineHeight: 1.6 }}>
              Weekly completion data and per-day metrics will appear here once pipeline history accumulates.
            </p>
          </div>

          <div style={{ border: "1px solid #D9D9D9", padding: "16px 18px", background: "#FFFFFF" }}>
            <div style={{ color: "#7A7A7A", fontSize: 12, fontWeight: 500, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 14, fontFamily: "'IBM Plex Mono', monospace" }}>
              Pipeline Status
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                <div style={{ width: 28, height: 28, border: "1px solid #D9D9D9", display: "flex", alignItems: "center", justifyContent: "center", color: "#7A7A7A", fontSize: 11, fontWeight: 600, flexShrink: 0, fontFamily: "'IBM Plex Mono', monospace" }}>
                  TP
                </div>
                <div>
                  <div style={{ color: "#111111", fontSize: 12, marginBottom: 3 }}>Pipeline</div>
                  <div style={{ color: "#7A7A7A", fontSize: 11, lineHeight: 1.4, marginBottom: 4 }}>Ingest → Extract → Prioritize → Plan</div>
                  <StatusPill status="Live" />
                </div>
              </div>
            </div>
          </div>
        </div>

        {loading && (
          <div style={{ color: "#7A7A7A", fontSize: 13, textAlign: "center", padding: 20 }}>
            Loading weekly summary...
          </div>
        )}

        {summary?.summary && (
          <div style={{ border: "1px solid #D9D9D9", padding: "20px", background: "#FFFFFF" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <div>
                <div style={{ color: "#111111", fontSize: 14, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Weekly Summary</div>
                <div style={{ color: "#7A7A7A", fontSize: 12, marginTop: 2, display: "flex", gap: 6, alignItems: "center" }}>
                  <SparkleIcon size={11} /> AI-generated
                </div>
              </div>
              <button onClick={() => setCopied(true)}
                style={{ background: "none", border: "1px solid #D9D9D9", padding: "7px 14px", color: copied ? "#F97316" : "#7A7A7A", fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontFamily: "'IBM Plex Mono', monospace" }}>
                <Copy size={12} /> {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            <pre style={{ color: "#7A7A7A", fontSize: 12, lineHeight: 1.7, whiteSpace: "pre-wrap", margin: 0, fontFamily: "'Inter', sans-serif" }}>
              {summary.summary}
            </pre>
          </div>
        )}

        {!summary && !loading && (
          <div style={{ border: "1px solid #D9D9D9", padding: "20px", background: "#FFFFFF" }}>
            <p style={{ color: "#7A7A7A", fontSize: 13 }}>No weekly summary available yet. Run the pipeline to generate one.</p>
          </div>
        )}
      </main>
    </div>
  );
}

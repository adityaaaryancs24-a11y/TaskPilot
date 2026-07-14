import { useEffect, useMemo, useState } from "react";
import { GitMerge, Sparkles, RefreshCw, AlertCircle, CheckCircle, HelpCircle } from "lucide-react";
import { Card } from "../shared/Card";
import { MergedTaskCard } from "../shared/MergedTaskCard";
import { getDedupGroups, DedupGroup } from "../../api/taskpilot";

const CONFIDENCE_CUTOFFS = [
  { label: "High", min: 0.8, color: "#BFD78D", icon: CheckCircle },
  { label: "Medium", min: 0.5, color: "#F5D66E", icon: HelpCircle },
  { label: "Needs Review", min: 0, color: "#F7C5E6", icon: AlertCircle },
];

export function DedupGroups() {
  const [groups, setGroups] = useState<DedupGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterConfidence, setFilterConfidence] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const data = await getDedupGroups();
      setGroups(data.groups || []);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  const categorized = useMemo(() => {
    return CONFIDENCE_CUTOFFS.map(({ label, min, color, icon: Icon }) => {
      const filtered = min === 0.8
        ? groups.filter(g => g.match_confidence >= 0.8)
        : min === 0.5
          ? groups.filter(g => g.match_confidence >= 0.5 && g.match_confidence < 0.8)
          : groups.filter(g => g.match_confidence < 0.5);
      return { label, min, color, icon: Icon, groups: filtered, count: filtered.length };
    });
  }, [groups]);

  const displayed = useMemo(() => {
    if (!filterConfidence) return groups;
    if (filterConfidence === "High") return groups.filter(g => g.match_confidence >= 0.8);
    if (filterConfidence === "Medium") return groups.filter(g => g.match_confidence >= 0.5 && g.match_confidence < 0.8);
    return groups.filter(g => g.match_confidence < 0.5);
  }, [groups, filterConfidence]);

  const totalMerged = groups.reduce((s, g) => s + g.merged_count, 0);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <GitMerge size={20} /> Dedup Groups
          </h2>
          <p style={{ color: "#7A7A7A", fontSize: 13, marginTop: 4 }}>
            {loading ? "Loading..." : `${groups.length} groups · ${totalMerged} merged tasks`}
          </p>
        </div>
        <button onClick={fetchData}
          style={{ background: "#0D0D0D", color: "#FFFFFF", border: "none", padding: "10px 20px", borderRadius: 12, fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontFamily: "'IBM Plex Mono', monospace" }}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
        {categorized.map(({ label, color, icon: Icon, count }) => (
          <Card key={label} variant={label === "High" ? "green" : label === "Medium" ? "yellow" : "pink"} shadow>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <div style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</div>
              <Icon size={16} color={color} />
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif" }}>{count}</div>
            <div style={{ fontSize: 12, color: "#7A7A7A", marginTop: 2 }}>
              {count === 1 ? "1 group" : `${count} groups`}
            </div>
          </Card>
        ))}
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {[{ label: "All", value: null }, { label: "High", value: "High" }, { label: "Medium", value: "Medium" }, { label: "Needs Review", value: "Needs Review" }].map(({ label, value }) => (
          <button key={label} onClick={() => setFilterConfidence(value)}
            style={{
              background: filterConfidence === value ? "#0D0D0D" : "transparent",
              color: filterConfidence === value ? "#FFFFFF" : "#7A7A7A",
              border: filterConfidence === value ? "none" : "1px solid #E9E4D8",
              padding: "6px 14px", borderRadius: 10, fontSize: 12, cursor: "pointer",
              fontFamily: "'IBM Plex Mono', monospace", transition: "all 0.15s",
            }}>
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ textAlign: "center", color: "#7A7A7A", padding: 40, fontSize: 13 }}>Loading dedup groups...</div>
      ) : displayed.length === 0 ? (
        <Card style={{ textAlign: "center", padding: 40 }}>
          <Sparkles size={24} style={{ margin: "0 auto 12px", opacity: 0.4 }} />
          <p style={{ color: "#7A7A7A", fontSize: 13, margin: 0 }}>No deduplication groups found. Run the pipeline to detect cross-source duplicates.</p>
        </Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {displayed.map((group) => (
            <MergedTaskCard key={group.id || group.tasks.map(t => t.id).join(",")} group={group} />
          ))}
        </div>
      )}
    </div>
  );
}

import { useEffect, useState, useCallback, useMemo } from "react";
import { BarChart3, TrendingUp, Activity, Users, RefreshCw, Clock, Zap, Copy, Check, Cpu, Database, GitBranch } from "lucide-react";
import { Card } from "../shared/Card";
import { getDashboard, getWeeklySummary, getTeamMetrics, getMetrics, WebSocketEvent } from "../../api/taskpilot";
import { useWebSocket } from "../../hooks/useWebSocket";
import { BarChart, Bar, PieChart, Pie, Cell, ComposedChart, AreaChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

const TOOLTIP_STYLE = { contentStyle: { background: "#FFFDF8", border: "1px solid #E9E4D8", borderRadius: 12, fontSize: 12 } };

const BOLD_COLORS = ["#E86AA8", "#D4A020", "#6BBF6E", "#4A8FE4", "#9B6FD8", "#E88040"];
const CHART_GREEN = "#5AB05E";
const CHART_BLUE = "#3C7DD9";
const CHART_PINK = "#D94F8A";
const CHART_GRAY = "#D0C8BC";
const CHART_PURPLE = "#8B5CF6";
const CHART_GOLD = "#C89520";
const CHART_ORANGE = "#D9702A";

function KpiCard({ icon, label, value, sub, variant = "default" }: { icon: React.ReactNode; label: string; value: string; sub: string; variant?: string }) {
  return (
    <Card variant={variant as any} shadow>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
        <span style={{ fontSize: 10, color: "#7A7A7A", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.04em", fontFamily: "'IBM Plex Mono', monospace" }}>{label}</span>
        {icon}
      </div>
      <div style={{ fontSize: 24, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif", lineHeight: 1.1 }}>{value}</div>
      <div style={{ fontSize: 11, color: "#7A7A7A", marginTop: 2 }}>{sub}</div>
    </Card>
  );
}

function StatRow({ label, value, highlight }: { label: string; value: string | number; highlight?: boolean }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "4px 0", borderBottom: "1px solid #F0EBE0" }}>
      <span style={{ fontSize: 12, color: "#7A7A7A" }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: highlight ? 700 : 500, color: highlight ? "#111111" : "#111111", fontFamily: "'IBM Plex Mono', monospace" }}>{value}</span>
    </div>
  );
}

export function Reports() {
  const [db, setDb] = useState<any>(null);
  const [weekly, setWeekly] = useState<string>("");
  const [team, setTeam] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [d, w, t, m] = await Promise.all([
        getDashboard().catch(() => null),
        getWeeklySummary().catch(() => null),
        getTeamMetrics().catch(() => null),
        getMetrics().catch(() => null),
      ]);
      setDb(d);
      setWeekly(w?.summary || "");
      setTeam(t);
      setMetrics(m);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  const handleWsEvent = useCallback((event: WebSocketEvent) => {
    if (event.event === "plan_updated") fetchData();
    if (event.event === "system_status") {
      const s = event.data as any;
      if (s?.task_count) fetchData();
    }
  }, []);

  useWebSocket(handleWsEvent);

  const velocity = db?.team_velocity?.daily_counts ?? [];
  const peakPatterns = db?.completion_patterns?.peak_completion_patterns ?? [];
  const ingestionVolume = metrics?.ingestion_volume ?? [];
  const llmUsage = metrics?.llm_usage ?? [];
  const syncLatency = metrics?.sync_latency ?? [];
  const teams = team?.teams ?? {};
  const rankedTasks = db?.plan?.ranked_tasks ?? [];
  const [copied, setCopied] = useState(false);

  const completed7d = velocity.reduce((s: number, v: any) => s + (v.completed || 0), 0);
  const totalTasks = metrics?.task_count ?? rankedTasks.length ?? 0;
  const activeAlerts = db?.plan?.alerts?.length ?? 0;
  const blockedCount = db?.plan?.blocked?.length ?? 0;
  const inProgressCount = totalTasks - blockedCount - completed7d;
  const topPriority = db?.plan?.top_priorities?.[0];

  const standupMetrics = useMemo(() => [
    { label: "Tasks Tracked", value: totalTasks },
    { label: "Completed (7d)", value: completed7d, highlight: true },
    { label: "In Progress", value: Math.max(0, inProgressCount) },
    { label: "Blocked", value: blockedCount },
    ...(activeAlerts > 0 ? [{ label: "Active Alerts", value: activeAlerts, highlight: true }] : []),
    ...(topPriority ? [{ label: "Top Priority Score", value: topPriority.score?.toFixed(1) ?? "--", highlight: true }] : []),
  ], [totalTasks, completed7d, inProgressCount, blockedCount, activeAlerts, topPriority]);

  const handleCopyStandup = async () => {
    const dateStr = new Date().toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
    let blurb = `Standup Update — ${dateStr}\n\n`;
    blurb += `Tasks tracked: ${totalTasks}\n`;
    blurb += `Completed (7d): ${completed7d}\n`;
    blurb += `In progress: ${Math.max(0, inProgressCount)}\n`;
    blurb += `Blocked: ${blockedCount}\n`;
    if (activeAlerts > 0) blurb += `Active alerts: ${activeAlerts}\n`;
    if (topPriority) blurb += `\nTop priority: ${topPriority.title} (Score: ${topPriority.score})\n`;
    blurb += `\nGenerated at ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    try {
      await navigator.clipboard.writeText(blurb);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  const chartData = useMemo(() => velocity.map((v: any) => ({
    date: v.day?.slice(0, 3) || "",
    completed: v.completed || 0,
    total: v.total || 0,
    rate: v.total > 0 ? Math.round((v.completed / v.total) * 100) : 0,
  })), [velocity]);

  const sourceData = useMemo(() => {
    const counts: Record<string, number> = {};
    rankedTasks.forEach((t: any) => {
      const src = t.source_type || t.source || "unknown";
      counts[src] = (counts[src] || 0) + 1;
    });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [rankedTasks]);

  const llmChartData = useMemo(() => llmUsage.slice(0, 8).reverse().map((u: any) => ({
    name: u.step_name?.split("_").slice(0, 2).join(" ") || u.step_name || "LLM",
    tokens: u.tokens_used || 0,
    duration: u.duration_ms ? Math.round(u.duration_ms) : 0,
  })), [llmUsage]);

  const ingestionChartData = useMemo(() => ingestionVolume.slice(0, 7).reverse().map((v: any) => ({
    date: v.timestamp?.slice(5, 10) || "",
    count: v.count || 0,
  })), [ingestionVolume]);

  const syncChartData = useMemo(() => syncLatency.slice(0, 8).reverse().map((s: any) => ({
    name: s.step_name?.replace("sync_", "").slice(0, 12) || "sync",
    ms: s.duration_ms ? Math.round(s.duration_ms) : 0,
  })), [syncLatency]);

  const teamChartData = useMemo(() => Object.entries(teams).map(([name, data]: [string, any]) => ({
    name: name.slice(0, 12),
    total: data.total_tasks || 0,
    done: data.done || 0,
    blocked: data.blocked || 0,
  })), [teams]);

  const weeklyHighlights = useMemo(() => {
    if (!weekly) return [];
    const lines = weekly.split("\n").filter(l => l.trim());
    return lines.slice(0, 6).map(l => l.replace(/^[#*\-]+/, "").trim()).filter(Boolean);
  }, [weekly]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <BarChart3 size={20} /> Reports
          </h2>
          <p style={{ color: "#7A7A7A", fontSize: 13, marginTop: 4 }}>
            {loading ? "Loading..." : `${metrics?.task_count ?? 0} tasks · ${Object.keys(teams).length} teams · ${velocity.length}d velocity`}
          </p>
        </div>
        <button onClick={fetchData} style={{ background: "#0D0D0D", color: "#FFFFFF", border: "none", padding: "10px 20px", borderRadius: 12, fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontFamily: "'IBM Plex Mono', monospace" }}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
        <KpiCard icon={<Database size={16} color="#7A7A7A" />} label="Total Tasks" value={String(totalTasks)} sub="Across all sources" variant="green" />
        <KpiCard icon={<Cpu size={16} color="#7A7A7A" />} label="Avg Latency" value={metrics?.api_latency?.avg_latency_ms ? `${metrics.api_latency.avg_latency_ms.toFixed(0)}ms` : "--"} sub="Last hour API calls" variant="blue" />
        <KpiCard icon={<Activity size={16} color="#7A7A7A" />} label="API Calls" value={String(metrics?.api_latency?.total_calls ?? 0)} sub="In the last hour" variant="pink" />
        <KpiCard icon={<Users size={16} color="#7A7A7A" />} label="Teams" value={String(Object.keys(teams).length || "--")} sub={`${teamChartData.reduce((s, t) => s + t.total, 0)} total tasks`} variant="yellow" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <Card variant="purple" shadow style={{ maxHeight: 280, overflow: "auto" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
            <Zap size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Weekly Summary</span>
          </div>
          {weeklyHighlights.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {weeklyHighlights.map((line, i) => (
                <div key={i} style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                  <span style={{ color: CHART_PURPLE, fontSize: 14, lineHeight: 1.4 }}>•</span>
                  <span style={{ fontSize: 12, color: "#555555", lineHeight: 1.5 }}>{line.slice(0, 200)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ fontSize: 12, color: "#7A7A7A", lineHeight: 1.6, margin: 0, whiteSpace: "pre-wrap" }}>
              {weekly.slice(0, 600) || "No weekly summary available."}
            </p>
          )}
        </Card>

        <Card shadow>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <Copy size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Standup Blurb</span>
            </div>
            <button onClick={handleCopyStandup}
              style={{ background: copied ? CHART_GREEN : "#0D0D0D", color: "#FFFFFF", border: "none", padding: "6px 12px", borderRadius: 8, fontSize: 10, cursor: "pointer", display: "flex", alignItems: "center", gap: 4, fontFamily: "'IBM Plex Mono', monospace", transition: "all 0.2s" }}>
              {copied ? <Check size={10} /> : <Copy size={10} />}
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
          <div style={{ background: "#F6F2E9", borderRadius: 12, padding: "12px 14px", maxHeight: 200, overflow: "auto" }}>
            <div style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif", color: "#111111", marginBottom: 8 }}>
              {new Date().toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {standupMetrics.map((m) => (
                <StatRow key={m.label} label={m.label} value={m.value} highlight={m.highlight} />
              ))}
            </div>
            {topPriority && (
              <div style={{ marginTop: 8, padding: "6px 10px", background: "#FFFDF8", borderRadius: 8, border: "1px solid #E9E4D8" }}>
                <div style={{ fontSize: 10, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 2 }}>TOP PRIORITY</div>
                <div style={{ fontSize: 12, fontWeight: 500, color: "#111111" }}>{topPriority.title}</div>
              </div>
            )}
            <div style={{ fontSize: 9, color: "#B0A8A0", marginTop: 6, fontFamily: "'IBM Plex Mono', monospace" }}>
              Generated at {new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </div>
          </div>
        </Card>
      </div>

      {chartData.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <Card shadow>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
              <TrendingUp size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Completion Rate</span>
            </div>
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E0D8CC" />
                  <XAxis dataKey="date" stroke="#7A7A7A" tick={{ fontSize: 11 }} />
                  <YAxis yAxisId="left" stroke="#7A7A7A" tick={{ fontSize: 11 }} />
                  <YAxis yAxisId="right" orientation="right" stroke="#7A7A7A" tick={{ fontSize: 11 }} unit="%" domain={[0, 100]} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Legend />
                  <Bar yAxisId="left" dataKey="completed" fill={CHART_GREEN} radius={[6, 6, 0, 0]} name="Completed" barSize={22} />
                  <Bar yAxisId="left" dataKey="total" fill={CHART_GRAY} radius={[6, 6, 0, 0]} name="Total" barSize={22} />
                  <Line yAxisId="right" type="monotone" dataKey="rate" stroke={CHART_PINK} strokeWidth={3} dot={{ fill: CHART_PINK, r: 4 }} name="Rate %" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card shadow>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
              <Activity size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Productivity Trend</span>
            </div>
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E0D8CC" />
                  <XAxis dataKey="date" stroke="#7A7A7A" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#7A7A7A" tick={{ fontSize: 11 }} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Legend />
                  <Area type="monotone" dataKey="completed" stroke={CHART_GREEN} fill={CHART_GREEN} fillOpacity={0.3} strokeWidth={2.5} name="Completed" />
                  <Area type="monotone" dataKey="total" stroke={CHART_BLUE} fill={CHART_BLUE} fillOpacity={0.15} strokeWidth={2.5} name="Total" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      )}

      {(sourceData.length > 0 || ingestionChartData.length > 0) && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          {sourceData.length > 0 && (
            <Card shadow>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
                <GitBranch size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Source Distribution</span>
              </div>
              <div style={{ width: "100%", height: 240 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={sourceData} cx="50%" cy="50%" labelLine={false} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} outerRadius={80} dataKey="value">
                      {sourceData.map((_: any, i: number) => <Cell key={i} fill={BOLD_COLORS[i % BOLD_COLORS.length]} />)}
                    </Pie>
                    <Tooltip {...TOOLTIP_STYLE} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}
          {ingestionChartData.length > 0 && (
            <Card shadow>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
                <Database size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Ingestion Volume</span>
              </div>
              <div style={{ width: "100%", height: 240 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={ingestionChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E0D8CC" />
                    <XAxis dataKey="date" stroke="#7A7A7A" tick={{ fontSize: 10 }} />
                    <YAxis stroke="#7A7A7A" tick={{ fontSize: 10 }} />
                    <Tooltip {...TOOLTIP_STYLE} />
                    <Bar dataKey="count" fill={CHART_BLUE} radius={[6, 6, 0, 0]} name="Tasks" barSize={32} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}
        </div>
      )}

      {llmChartData.length > 0 && (
        <Card shadow>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
            <Cpu size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>LLM Usage (Tokens)</span>
          </div>
          <div style={{ width: "100%", height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={llmChartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#E0D8CC" />
                <XAxis type="number" stroke="#7A7A7A" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="name" stroke="#7A7A7A" tick={{ fontSize: 9 }} width={80} />
                <Tooltip {...TOOLTIP_STYLE} />
                <Bar dataKey="tokens" fill={CHART_PURPLE} radius={[0, 6, 6, 0]} name="Tokens" barSize={18} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {peakPatterns.length > 0 && (
        <Card variant="yellow" shadow>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
            <Clock size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Peak Completion Times</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
            {peakPatterns.slice(0, 8).map((p: any, i: number) => {
              const maxCount = Math.max(...peakPatterns.map((x: any) => x.count));
              const intensity = maxCount > 0 ? p.count / maxCount : 0;
              const bg = intensity > 0.7 ? "#E86AA8" : intensity > 0.4 ? "#F5A623" : "#F6F2E9";
              const textColor = intensity > 0.4 ? "#FFFFFF" : "#7A7A7A";
              return (
                <div key={i} style={{ background: bg, padding: "10px 8px", borderRadius: 10, textAlign: "center" }}>
                  <div style={{ fontSize: 11, color: textColor, fontFamily: "'IBM Plex Mono', monospace" }}>
                    {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][p.day]}
                  </div>
                  <div style={{ fontSize: 15, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif", color: intensity > 0.4 ? "#FFFFFF" : "#111111" }}>{p.hour}:00</div>
                  <div style={{ fontSize: 10, color: textColor, marginTop: 2 }}>{p.count} done</div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {syncChartData.length > 0 && (
        <Card shadow>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
            <Activity size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Sync Latency (ms)</span>
          </div>
          <div style={{ width: "100%", height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={syncChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E0D8CC" />
                <XAxis dataKey="name" stroke="#7A7A7A" tick={{ fontSize: 10 }} />
                <YAxis stroke="#7A7A7A" tick={{ fontSize: 10 }} />
                <Tooltip {...TOOLTIP_STYLE} />
                <Bar dataKey="ms" fill={CHART_ORANGE} radius={[6, 6, 0, 0]} name="Duration (ms)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <Card variant="blue" shadow>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
            <Users size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Team Breakdown</span>
          </div>
          {teamChartData.length > 0 ? (
            <div style={{ width: "100%", height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={teamChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E0D8CC" />
                  <XAxis dataKey="name" stroke="#7A7A7A" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#7A7A7A" tick={{ fontSize: 10 }} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Bar dataKey="total" fill={CHART_BLUE} radius={[6, 6, 0, 0]} name="Total" />
                  <Bar dataKey="done" fill={CHART_GREEN} radius={[6, 6, 0, 0]} name="Done" />
                  <Bar dataKey="blocked" fill={CHART_PINK} radius={[6, 6, 0, 0]} name="Blocked" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div style={{ fontSize: 12, color: "#7A7A7A" }}>No team data available.</div>
          )}
        </Card>
        <Card variant="pink" shadow>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
            <Cpu size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>System Health</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <div style={{ background: "#F6F2E9", borderRadius: 12, padding: "12px" }}>
              <div style={{ fontSize: 10, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 4 }}>PLAN STATUS</div>
              <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif", color: metrics?.has_plan ? CHART_GREEN : "#7A7A7A" }}>{metrics?.has_plan ? "Active" : "None"}</div>
            </div>
            <div style={{ background: "#F6F2E9", borderRadius: 12, padding: "12px" }}>
              <div style={{ fontSize: 10, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 4 }}>WS CHANNELS</div>
              <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif" }}>{Object.keys(metrics?.websocket_health?.channels ?? {}).length}</div>
            </div>
            <div style={{ background: "#F6F2E9", borderRadius: 12, padding: "12px" }}>
              <div style={{ fontSize: 10, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 4 }}>TOTAL TASKS</div>
              <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif" }}>{metrics?.task_count ?? 0}</div>
            </div>
            <div style={{ background: "#F6F2E9", borderRadius: 12, padding: "12px" }}>
              <div style={{ fontSize: 10, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 4 }}>AVG LATENCY</div>
              <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif" }}>{metrics?.api_latency?.avg_latency_ms ? `${metrics.api_latency.avg_latency_ms.toFixed(0)}ms` : "--"}</div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import {
  Zap, Bell, RefreshCw, Clock, Calendar, AlertTriangle,
  BarChart3, MessageSquare, CheckCircle2, Circle, TrendingUp,
  Activity, ArrowUpRight, Sparkles, ChevronRight
} from "lucide-react";
import { Card } from "../shared/Card";
import { PriorityPill } from "../shared/PriorityPill";
import { SourceBadge } from "../shared/SourceBadge";
import { AIRationale } from "../shared/AIRationale";
import { FeedbackButton } from "../shared/FeedbackButton";
import { TaskCard } from "../shared/TaskCard";
import { CreateTaskModal } from "../shared/CreateTaskModal";
import {
  getPlan,
  refreshPlan,
  injectTask,
  getDashboard,
  getCalendarToday,
  DailyPlan,
  WebSocketEvent,
  CalendarEvent,
  Task
} from "../../api/taskpilot";
import { useWebSocket } from "../../hooks/useWebSocket";

// ── Typing animation hook ────────────────────────────────────────────────────
function useTyping(phrases: string[], speed = 55, pause = 2200) {
  const [display, setDisplay] = useState("");
  const [phraseIdx, setPhraseIdx] = useState(0);
  const [charIdx, setCharIdx] = useState(0);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const current = phrases[phraseIdx];
    const delay = deleting ? speed / 2 : speed;

    const t = setTimeout(() => {
      if (!deleting) {
        if (charIdx < current.length) {
          setDisplay(current.slice(0, charIdx + 1));
          setCharIdx(c => c + 1);
        } else {
          setTimeout(() => setDeleting(true), pause);
        }
      } else {
        if (charIdx > 0) {
          setDisplay(current.slice(0, charIdx - 1));
          setCharIdx(c => c - 1);
        } else {
          setDeleting(false);
          setPhraseIdx(i => (i + 1) % phrases.length);
        }
      }
    }, delay);

    return () => clearTimeout(t);
  }, [charIdx, deleting, phraseIdx, phrases, speed, pause]);

  return display;
}

// ── Live clock ───────────────────────────────────────────────────────────────
function LiveClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, color: "#7A7A7A", letterSpacing: "0.04em" }}>
      {now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
    </span>
  );
}

// ── Animated counter ─────────────────────────────────────────────────────────
function AnimatedNumber({ target, duration = 900 }: { target: number; duration?: number }) {
  const [val, setVal] = useState(0);
  const start = useRef<number | null>(null);
  const raf = useRef<number>(0);

  useEffect(() => {
    start.current = null;
    const animate = (ts: number) => {
      if (start.current === null) start.current = ts;
      const progress = Math.min((ts - start.current) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setVal(Math.round(eased * target));
      if (progress < 1) raf.current = requestAnimationFrame(animate);
    };
    raf.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf.current);
  }, [target, duration]);

  return <>{val}</>;
}

// ── KPI card ─────────────────────────────────────────────────────────────────
function KPI({
  icon, label, value, sub, variant = "blue", trend, numeric = false
}: {
  icon: React.ReactNode; label: string; value: string | number;
  sub: string; variant?: string; trend?: number; numeric?: boolean;
}) {
  const num = typeof value === "number" ? value : parseFloat(String(value));
  const isNum = !isNaN(num) && numeric;

  return (
    <div style={{
      background: variantBg(variant), border: `1px solid ${variantBorder(variant)}`,
      borderRadius: 20, padding: "20px 22px", boxShadow: "0 4px 24px rgba(0,0,0,0.05)",
      position: "relative", overflow: "hidden", transition: "transform 0.2s, box-shadow 0.2s",
      cursor: "default",
    }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLDivElement).style.transform = "translateY(-2px)";
        (e.currentTarget as HTMLDivElement).style.boxShadow = "0 8px 32px rgba(0,0,0,0.09)";
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
        (e.currentTarget as HTMLDivElement).style.boxShadow = "0 4px 24px rgba(0,0,0,0.05)";
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10, alignItems: "center" }}>
        <span style={{ fontSize: 10, color: "#7A7A7A", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", fontFamily: "'IBM Plex Mono', monospace" }}>
          {label}
        </span>
        <span style={{ opacity: 0.5 }}>{icon}</span>
      </div>
      <div style={{ fontSize: 32, fontWeight: 800, fontFamily: "'Space Grotesk', sans-serif", lineHeight: 1, color: "#0D0D0D" }}>
        {isNum ? <AnimatedNumber target={num} /> : value}
      </div>
      <div style={{ fontSize: 12, color: "#7A7A7A", marginTop: 5, display: "flex", alignItems: "center", gap: 4 }}>
        {sub}
        {trend !== undefined && (
          <span style={{ color: trend >= 0 ? "#22863a" : "#d73a49", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" }}>
            {trend >= 0 ? "↑" : "↓"}{Math.abs(trend)}%
          </span>
        )}
      </div>
    </div>
  );
}

function variantBg(v: string) {
  const m: Record<string, string> = { pink: "#F7C5E6", yellow: "#F5D66E", green: "#BFD78D", blue: "#C9D8FF", purple: "#DCC7F7", orange: "#FAD6B3" };
  return m[v] || "#FFFFFF";
}
function variantBorder(v: string) {
  const m: Record<string, string> = { pink: "#F0A8D6", yellow: "#E8C84A", green: "#A8C870", blue: "#A8C0F0", purple: "#C8A8E8", orange: "#F0C090" };
  return m[v] || "#E9E4D8";
}

// ── Pulse dot ─────────────────────────────────────────────────────────────────
function PulseDot({ color = "#22863a" }: { color?: string }) {
  return (
    <span style={{ position: "relative", display: "inline-flex", width: 8, height: 8, flexShrink: 0 }}>
      <span style={{
        position: "absolute", inset: 0, borderRadius: "50%", background: color,
        animation: "ping 1.4s cubic-bezier(0,0,0.2,1) infinite", opacity: 0.6,
      }} />
      <span style={{ borderRadius: "50%", background: color, width: 8, height: 8, position: "relative" }} />
      <style>{`@keyframes ping { 0%{transform:scale(1);opacity:0.7} 75%,100%{transform:scale(2.2);opacity:0} }`}</style>
    </span>
  );
}

// ── Activity item ─────────────────────────────────────────────────────────────
function ActivityItem({ icon, text, time, accent }: { icon: React.ReactNode; text: string; time: string; accent: string }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "8px 0", borderBottom: "1px solid rgba(0,0,0,0.05)" }}>
      <div style={{ width: 28, height: 28, borderRadius: "50%", background: accent, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1 }}>
        {icon}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, color: "#111111", lineHeight: 1.5, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{text}</div>
        <div style={{ fontSize: 10, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", marginTop: 2 }}>{time}</div>
      </div>
    </div>
  );
}

// ── Score bar ──────────────────────────────────────────────────────────────────
function ScoreBar({ label, value, max = 100, color }: { label: string; value: number; max?: number; color: string }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
        <span style={{ fontSize: 10, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>{label}</span>
        <span style={{ fontSize: 10, color: "#0D0D0D", fontFamily: "'IBM Plex Mono', monospace", fontWeight: 600 }}>{value}</span>
      </div>
      <div style={{ height: 4, background: "rgba(0,0,0,0.07)", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 4, transition: "width 1s cubic-bezier(0.4,0,0.2,1)" }} />
      </div>
    </div>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────────────────
export function Dashboard() {
  const [plan, setPlan] = useState<DailyPlan | null>(null);
  const [dashboard, setDashboard] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [injecting, setInjecting] = useState(false);
  const [calendarEvents, setCalendarEvents] = useState<CalendarEvent[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [narrativeAlert, setNarrativeAlert] = useState<string | null>(null);
  const [narrativeDismissed, setNarrativeDismissed] = useState(false);
  const [activityLog, setActivityLog] = useState<{ icon: React.ReactNode; text: string; time: string; accent: string }[]>([]);

  const typedText = useTyping([
    "Ranking your tasks by impact…",
    "Monitoring 6 live integrations…",
    "Surfacing hidden blockers with AI…",
    "Scheduling your focus blocks…",
    "Deduplicating across Jira, Slack & GitHub…",
  ]);

  const handleWsEvent = useCallback((event: WebSocketEvent) => {
    if (event.event === "plan_updated" || event.event === "priorities_updated") {
      const p = event.data as DailyPlan;
      setPlan(p);
      setAlerts(p?.alerts || []);
      addActivity(<TrendingUp size={12} color="#0D0D0D" />, "AI plan refreshed — priorities updated", "#BFD78D");
    }
    if (event.event === "alerts_updated") {
      setAlerts(Array.isArray(event.data) ? event.data as any[] : []);
      addActivity(<Bell size={12} color="#0D0D0D" />, "Alert state updated", "#FAD6B3");
    }
    if (event.event === "narrative_alert") {
      setNarrativeAlert(String(event.data));
      setNarrativeDismissed(false);
    }
  }, []);

  useWebSocket(handleWsEvent);

  function addActivity(icon: React.ReactNode, text: string, accent: string) {
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setActivityLog(prev => [{ icon, text, time, accent }, ...prev].slice(0, 8));
  }

  const refresh = useCallback(async (showSpinner = false) => {
    if (showSpinner) setRefreshing(true);
    else setLoading(true);
    try {
      const [p, d, cal] = await Promise.all([
        getPlan(),
        getDashboard().catch(() => null),
        getCalendarToday().catch(() => ({ events: [] })),
      ]);
      setPlan(p);
      setDashboard(d);
      setCalendarEvents(cal.events || []);
      setAlerts(p?.alerts || []);
      if (showSpinner) {
        addActivity(<Sparkles size={12} color="#0D0D0D" />, "Plan generated — tasks re-ranked", "#DCC7F7");
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { refresh(); }, []);

  const top3 = plan?.top_priorities ?? [];
  const allRanked = plan?.ranked_tasks ?? [];
  const rest = useMemo(() => {
    if (!plan) return [];
    return [...(plan.do_next ?? []), ...(plan.deferred ?? []), ...(plan.blocked ?? [])];
  }, [plan]);

  const deferredTasks = plan?.deferred_tasks_detected ?? dashboard?.deferred_tasks ?? [];
  const timeBlocks = plan?.time_blocked_plan?.time_blocks ?? [];
  const focusHours = timeBlocks.length > 0
    ? timeBlocks.reduce((acc: number, tb: any) => acc + (new Date(tb.end).getTime() - new Date(tb.start).getTime()) / 3600000, 0).toFixed(1)
    : "0.0";

  const h = new Date().getHours();
  const greeting = h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";

  const handleGeneratePlan = async () => {
    setRefreshing(true);
    try {
      const p = await refreshPlan();
      setPlan(p);
      setAlerts(p?.alerts || []);
      addActivity(<Sparkles size={12} color="#0D0D0D" />, "Plan generated — tasks re-ranked", "#DCC7F7");
    } catch { }
    finally { setRefreshing(false); }
  };
  const handleInjectP1 = async () => {
    setInjecting(true);
  
    try {
      const updatedPlan = await injectTask({
        title: "P1 Production Outage - Login Service Down",
        description: "Users cannot authenticate.",
        source_type: "injected",
        priority: "P1",
        deadline: new Date(Date.now() + 3600000).toISOString(),
      });
  
      setPlan(updatedPlan);
      setAlerts(updatedPlan?.alerts || []);
  
      addActivity(
        <AlertTriangle size={12} color="#0D0D0D" />,
        "Critical P1 outage injected",
        "#F7C5E6"
      );
    } catch (err) {
      console.error(err);
    } finally {
      setInjecting(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>

      {/* ── Header ── */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
            <PulseDot color="#22863a" />
            <span style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", fontWeight: 500 }}>LIVE</span>
            <LiveClock />
          </div>
          <h2 style={{ margin: 0, fontFamily: "'Space Grotesk', sans-serif", fontSize: 26, fontWeight: 800, color: "#0D0D0D", lineHeight: 1.2 }}>
            {greeting}.
          </h2>
          <div style={{ marginTop: 5, fontSize: 13, color: "#7A7A7A", minHeight: 20, display: "flex", alignItems: "center", gap: 6 }}>
            <Sparkles size={12} color="#DCC7F7" />
            <span style={{ fontFamily: "'IBM Plex Mono', monospace" }}>
              {loading ? "Loading your workspace…" : typedText}
              <span style={{ borderRight: "2px solid #0D0D0D", marginLeft: 1, animation: "blink 0.9s step-end infinite" }} />
            </span>
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>

  <button
    onClick={handleGeneratePlan}
    disabled={refreshing}
    style={{
      background: "#0D0D0D",
      color: "#FFFFFF",
      border: "none",
      padding: "10px 20px",
      borderRadius: 14,
      fontSize: 12,
      cursor: refreshing ? "not-allowed" : "pointer",
      display: "flex",
      alignItems: "center",
      gap: 7,
      fontFamily: "'IBM Plex Mono', monospace",
      fontWeight: 500,
      opacity: refreshing ? 0.7 : 1,
      transition: "opacity 0.2s, transform 0.15s",
    }}
    onMouseEnter={e =>
      !refreshing &&
      ((e.currentTarget as HTMLButtonElement).style.transform =
        "scale(1.03)")
    }
    onMouseLeave={e =>
      ((e.currentTarget as HTMLButtonElement).style.transform =
        "scale(1)")
    }
  >
    <RefreshCw
      size={13}
      style={{
        animation: refreshing
          ? "spin 0.8s linear infinite"
          : "none",
      }}
    />
    {refreshing ? "Generating…" : "Generate Plan"}
  </button>

  <button
    onClick={handleInjectP1}
    disabled={injecting}
    style={{
      background: "#F7C5E6",
      color: "#0D0D0D",
      border: "1px solid #F0A8D6",
      padding: "10px 20px",
      borderRadius: 14,
      fontSize: 12,
      cursor: injecting ? "not-allowed" : "pointer",
      fontFamily: "'IBM Plex Mono', monospace",
      fontWeight: 500,
      opacity: injecting ? 0.7 : 1,
      transition: "all 0.2s",
    }}
  >
    {injecting ? "Injecting..." : "Inject P1 Outage"}
  </button>

  <CreateTaskModal onCreated={() => refresh(true)} />
</div>
      </div>

      <style>{`
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes spin  { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        @keyframes fadeUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
      `}</style>

      {/* ── Narrative alert ── */}
      {narrativeAlert && !narrativeDismissed && (
        <div style={{
          display: "flex", alignItems: "flex-start", gap: 10, padding: "12px 16px",
          background: "#FAD6B3", border: "1px solid #F0C090", borderRadius: 14,
          fontSize: 12, color: "#111111", animation: "fadeUp 0.3s ease",
        }}>
          <MessageSquare size={14} style={{ color: "#F97316", flexShrink: 0, marginTop: 1 }} />
          <div style={{ flex: 1 }}>{narrativeAlert}</div>
          <button onClick={() => setNarrativeDismissed(true)} style={{ background: "none", border: "none", cursor: "pointer", color: "#7A7A7A", fontSize: 16, padding: 0, lineHeight: 1 }}>×</button>
        </div>
      )}

      {/* ── KPI Row ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
        <KPI
          icon={<BarChart3 size={16} />} label="Active Tasks"
          value={allRanked.length} sub="tracked across sources" variant="blue"
          trend={allRanked.length > 0 ? 12 : undefined} numeric
        />
        <KPI
          icon={<AlertTriangle size={16} />} label="Top Score"
          value={top3[0] ? top3[0].score : "--"}
          sub={top3[0]?.title?.slice(0, 22) || "No tasks yet"} variant="pink"
          numeric={!!top3[0]}
        />
        <KPI
          icon={<Zap size={16} />} label="AI-Surfaced"
          value={deferredTasks.length} sub="hidden tasks found" variant="green"
          numeric
        />
        <KPI
          icon={<Clock size={16} />} label="Focus Hours"
          value={focusHours} sub={`${timeBlocks.length} blocks today`} variant="yellow"
        />
      </div>

      {/* ── Main layout ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 310px", gap: 18, alignItems: "start" }}>

        {/* ── Left column ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

          {/* Top Priorities */}
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
              <div style={{ color: "#7A7A7A", fontSize: 11, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", fontFamily: "'IBM Plex Mono', monospace", display: "flex", alignItems: "center", gap: 6 }}>
                <Zap size={11} /> Top Priorities Today
              </div>
              {top3.length > 0 && (
                <span style={{ fontSize: 10, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>
                  AI-ranked · {new Date(plan?.generated_at ?? "").toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              )}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {loading && (
                <>
                  {[1, 2, 3].map(i => (
                    <div key={i} style={{ height: 90, borderRadius: 18, background: "#F0EDE4", animation: "pulse 1.5s ease-in-out infinite" }}>
                      <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}`}</style>
                    </div>
                  ))}
                </>
              )}
              {!loading && top3.length === 0 && (
                <div style={{ padding: "28px 24px", background: "#F8F5EE", border: "1px dashed #D0C9B8", borderRadius: 18, textAlign: "center" }}>
                  <Sparkles size={24} color="#DCC7F7" style={{ marginBottom: 10 }} />
                  <div style={{ fontSize: 13, color: "#7A7A7A", marginBottom: 12 }}>No priorities ranked yet.</div>
                  <button onClick={handleGeneratePlan} style={{ background: "#0D0D0D", color: "#fff", border: "none", padding: "8px 18px", borderRadius: 10, fontSize: 12, cursor: "pointer", fontFamily: "'IBM Plex Mono', monospace" }}>
                    Generate your first plan →
                  </button>
                </div>
              )}
              {top3.map((task: any, i: number) => {
                const variantMap = ["pink", "yellow", "blue"];
                const variant = variantMap[i] ?? "blue";
                return (
                  <div key={task.id} style={{
                    background: variantBg(variant), border: `1px solid ${variantBorder(variant)}`,
                    borderRadius: 20, padding: "18px 20px",
                    boxShadow: "0 2px 16px rgba(0,0,0,0.05)",
                    animation: `fadeUp ${0.15 + i * 0.08}s ease both`,
                    transition: "transform 0.2s, box-shadow 0.2s",
                  }}
                    onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.transform = "translateY(-2px)"; (e.currentTarget as HTMLDivElement).style.boxShadow = "0 8px 28px rgba(0,0,0,0.09)"; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)"; (e.currentTarget as HTMLDivElement).style.boxShadow = "0 2px 16px rgba(0,0,0,0.05)"; }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, flexWrap: "wrap" }}>
                          <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 22, fontWeight: 800, color: "#0D0D0D", opacity: 0.2, lineHeight: 1 }}>#{i + 1}</span>
                          <SourceBadge source={task.source || task.source_type} />
                          <span style={{ fontSize: 10, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>{task.id}</span>
                        </div>
                        <div style={{ color: "#111111", fontSize: 14, fontWeight: 600, lineHeight: 1.45 }}>{task.title}</div>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 5, flexShrink: 0 }}>
                        <PriorityPill level={(task.priority ?? "P3") as any} />
                        <FeedbackButton task={task} compact />
                        {task.deadline && (
                          <span style={{ color: "#7A7A7A", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" }}>
                            {new Date(task.deadline).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </span>
                        )}
                      </div>
                    </div>

                    {task.score_breakdown && Object.keys(task.score_breakdown).length > 0 && (
                      <div style={{ marginTop: 12 }}>
                        {Object.entries(task.score_breakdown).slice(0, 3).map(([k, v]) => (
                          <ScoreBar key={k} label={k.replace(/_/g, " ")} value={Number(v)} max={100} color="#0D0D0D" />
                        ))}
                      </div>
                    )}

                    {task.rationale && (
                      <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid rgba(0,0,0,0.08)" }}>
                        <AIRationale text={task.rationale} />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Do Next */}
          {rest.length > 0 && (
            <div>
              <div style={{ color: "#7A7A7A", fontSize: 11, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 10, fontFamily: "'IBM Plex Mono', monospace", display: "flex", alignItems: "center", gap: 6 }}>
                <ChevronRight size={11} /> Up Next ({rest.length})
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {rest.map((task: any) => (
                  <TaskCard key={task.id} task={task as Task} onUpdate={() => refresh(true)} />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Right column ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

          {/* Alerts */}
          <div style={{
            background: alerts.length > 0 ? "#FAD6B3" : "#F8F5EE",
            border: `1px solid ${alerts.length > 0 ? "#F0C090" : "#E9E4D8"}`,
            borderRadius: 20, padding: "18px 20px",
            boxShadow: "0 2px 12px rgba(0,0,0,0.04)",
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Bell size={12} />
                <span style={{ fontSize: 11, fontWeight: 600, fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase", letterSpacing: "0.04em" }}>Alerts</span>
              </div>
              {alerts.length > 0 && (
                <span style={{ background: "#F97316", color: "#fff", borderRadius: 20, fontSize: 10, fontWeight: 700, padding: "2px 7px", fontFamily: "'IBM Plex Mono', monospace" }}>
                  {alerts.length}
                </span>
              )}
            </div>
            {alerts.length > 0 ? (
              alerts.slice(0, 5).map((a: any, i: number) => (
                <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "7px 0", borderBottom: i < alerts.slice(0, 5).length - 1 ? "1px solid rgba(0,0,0,0.06)" : "none" }}>
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: a.severity === "critical" ? "#F7C5E6" : a.severity === "warning" ? "#F5D66E" : "#BFD78D", flexShrink: 0, marginTop: 4 }} />
                  <span style={{ fontSize: 12, color: "#111111", lineHeight: 1.45 }}>{a.message}</span>
                </div>
              ))
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 12, color: "#7A7A7A" }}>
                <CheckCircle2 size={13} color="#BFD78D" /> All clear — no active alerts.
              </div>
            )}
          </div>

          {/* Calendar */}
          <div style={{ background: "#FFFFFF", border: "1px solid #E9E4D8", borderRadius: 20, padding: "18px 20px", boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}>
            <div style={{ fontSize: 11, fontWeight: 600, fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
              <Calendar size={11} /> Today's Schedule
            </div>
            {calendarEvents.length > 0 ? (
              calendarEvents.slice(0, 4).map((ev, i) => (
                <div key={ev.event_id} style={{ display: "flex", gap: 8, alignItems: "center", padding: "7px 0", borderBottom: i < 3 ? "1px solid #F0EDE4" : "none" }}>
                  <div style={{ width: 3, height: 28, borderRadius: 2, background: i === 0 ? "#DCC7F7" : i === 1 ? "#C9D8FF" : "#BFD78D", flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, color: "#111111", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{ev.title}</div>
                    {!ev.is_all_day && (
                      <div style={{ fontSize: 10, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", marginTop: 1 }}>
                        {new Date(ev.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div style={{ fontSize: 12, color: "#7A7A7A", display: "flex", alignItems: "center", gap: 6 }}>
                <Circle size={12} style={{ opacity: 0.4 }} /> No events scheduled today.
              </div>
            )}
          </div>

          {/* Live activity feed */}
          <div style={{ background: "#F8F5EE", border: "1px solid #E9E4D8", borderRadius: 20, padding: "18px 20px", boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}>
            <div style={{ fontSize: 11, fontWeight: 600, fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 10, display: "flex", alignItems: "center", gap: 6 }}>
              <Activity size={11} /> Activity
              <PulseDot color="#22863a" />
            </div>
            {activityLog.length === 0 ? (
              <div style={{ fontSize: 12, color: "#7A7A7A" }}>Waiting for events…</div>
            ) : (
              activityLog.map((a, i) => (
                <ActivityItem key={i} icon={a.icon} text={a.text} time={a.time} accent={a.accent} />
              ))
            )}
          </div>

          {/* Quick stats */}
          {plan && (
            <div style={{ background: "#C9D8FF", border: "1px solid #A8C0F0", borderRadius: 20, padding: "18px 20px" }}>
              <div style={{ fontSize: 11, fontWeight: 600, fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
                <TrendingUp size={11} /> Pipeline Stats
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {[
                  { label: "Blocked", value: plan.blocked?.length ?? 0, icon: <AlertTriangle size={11} /> },
                  { label: "Deferred", value: plan.deferred?.length ?? 0, icon: <Clock size={11} /> },
                  { label: "Do Next", value: plan.do_next?.length ?? 0, icon: <ArrowUpRight size={11} /> },
                  { label: "Time Blocks", value: timeBlocks.length, icon: <Calendar size={11} /> },
                ].map(({ label, value, icon }) => (
                  <div key={label} style={{ background: "rgba(255,255,255,0.45)", borderRadius: 12, padding: "10px 12px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 4, color: "#7A7A7A", marginBottom: 4 }}>
                      {icon}
                      <span style={{ fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" }}>{label}</span>
                    </div>
                    <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 22, fontWeight: 800, color: "#0D0D0D" }}>
                      <AnimatedNumber target={value} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
} 
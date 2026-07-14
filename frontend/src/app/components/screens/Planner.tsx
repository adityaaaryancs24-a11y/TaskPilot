import { useEffect, useState, useCallback, useMemo } from "react";
import { Clock, Calendar, RefreshCw, ChevronLeft, ChevronRight } from "lucide-react";
import { Card } from "../shared/Card";
import { PriorityPill } from "../shared/PriorityPill";
import { getPlan, getCalendarToday, DailyPlan, CalendarEvent, WebSocketEvent } from "../../api/taskpilot";
import { useWebSocket } from "../../hooks/useWebSocket";

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function Planner() {
  const [plan, setPlan] = useState<DailyPlan | null>(null);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [weekOffset, setWeekOffset] = useState(0);

  const refresh = async () => {
    setLoading(true);
    try {
      const [p, cal] = await Promise.all([
        getPlan(),
        getCalendarToday().catch(() => ({ events: [] })),
      ]);
      setPlan(p);
      setEvents(cal.events || []);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  useEffect(() => { refresh(); }, []);

  const handleWsEvent = useCallback((event: WebSocketEvent) => {
    if (event.event === "plan_updated") setPlan(event.data as DailyPlan);
  }, []);

  useWebSocket(handleWsEvent);

  const timeBlocks = plan?.time_blocked_plan?.time_blocks ?? [];
  const allRanked = plan?.ranked_tasks ?? [];

  const weekDays = useMemo(() => {
    const now = new Date();
    const mondayOffset = weekOffset * 7 + (now.getDay() === 0 ? -6 : 1 - now.getDay());
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() + mondayOffset + i);
      return {
        name: DAY_NAMES[d.getDay()],
        date: d.getDate(),
        month: d.toLocaleDateString("en-US", { month: "short" }),
        fullDate: d,
        isToday: d.toDateString() === now.toDateString(),
        dateStr: d.toISOString().split("T")[0],
      };
    });
  }, [weekOffset]);

  const getTasksForDay = useCallback((dateStr: string) => {
    return allRanked.filter((t: any) => {
      if (!t.deadline) return false;
      const taskDate = new Date(t.deadline).toISOString().split("T")[0];
      return taskDate === dateStr;
    });
  }, [allRanked]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <Calendar size={20} /> AI Planner
          </h2>
          <p style={{ color: "#7A7A7A", fontSize: 13, marginTop: 4 }}>
            {loading ? "Loading..." : `${timeBlocks.length} time blocks · ${events.length} events`}
          </p>
        </div>
        <button onClick={() => refresh()} style={{ background: "#0D0D0D", color: "#FFFFFF", border: "none", padding: "10px 20px", borderRadius: 12, fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontFamily: "'IBM Plex Mono', monospace" }}>
          <RefreshCw size={13} /> Replan
        </button>
      </div>

      <Card variant="pink" shadow>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
          <Clock size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Today's Plan</span>
        </div>
        {timeBlocks.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {timeBlocks.map((tb: any, i: number) => {
              const colors = ["#F7C5E6", "#F5D66E", "#C9D8FF", "#BFD78D", "#DCC7F7", "#FAD6B3"];
              return (
                <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                  <div style={{ minWidth: 55, textAlign: "right" }}>
                    <span style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>
                      {new Date(tb.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <div style={{ width: 2, height: "auto", background: "#E9E4D8", alignSelf: "stretch", margin: "2px 0" }} />
                  <div style={{
                    flex: 1, padding: "8px 12px", borderRadius: 12,
                    background: colors[i % colors.length],
                  }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: "#111111" }}>{tb.title}</div>
                    <div style={{ display: "flex", gap: 8, marginTop: 4, fontSize: 10, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>
                      {tb.slot_type === "deep_work" && <span style={{ fontWeight: 600 }}>Deep Work</span>}
                      {tb.priority && <PriorityPill level={tb.priority as any} />}
                      <span>Score: {tb.score}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ color: "#7A7A7A", fontSize: 12 }}>{loading ? "Loading..." : "Run the pipeline to generate your daily plan."}</div>
        )}
      </Card>

      <Card variant="blue" shadow>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Calendar size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>This Week</span>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button onClick={() => setWeekOffset(w => w - 1)}
              style={{ background: "none", border: "1px solid #E9E4D8", padding: "6px 10px", borderRadius: 10, cursor: "pointer", display: "flex", alignItems: "center", color: "#7A7A7A" }}>
              <ChevronLeft size={14} />
            </button>
            <button onClick={() => setWeekOffset(0)}
              style={{
                background: weekOffset === 0 ? "#0D0D0D" : "none",
                border: weekOffset === 0 ? "none" : "1px solid #E9E4D8",
                color: weekOffset === 0 ? "#FFFFFF" : "#7A7A7A",
                padding: "6px 12px", borderRadius: 10, fontSize: 11, cursor: "pointer",
                fontFamily: "'IBM Plex Mono', monospace", transition: "all 0.15s",
              }}>
              Today
            </button>
            <button onClick={() => setWeekOffset(w => w + 1)}
              style={{ background: "none", border: "1px solid #E9E4D8", padding: "6px 10px", borderRadius: 10, cursor: "pointer", display: "flex", alignItems: "center", color: "#7A7A7A" }}>
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 8 }}>
          {weekDays.map((day) => {
            const dayTasks = getTasksForDay(day.dateStr);
            return (
              <div key={day.dateStr} style={{
                textAlign: "center", padding: "8px 4px", borderRadius: 14,
                background: day.isToday ? "#0D0D0D" : "#F6F2E9",
                minHeight: 100, display: "flex", flexDirection: "column",
              }}>
                <div style={{ fontSize: 10, color: day.isToday ? "#FFFFFF" : "#7A7A7A", marginBottom: 2, fontFamily: "'IBM Plex Mono', monospace" }}>{day.name}</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: day.isToday ? "#FFFFFF" : "#111111", marginBottom: 2 }}>{day.date}</div>
                <div style={{ fontSize: 8, color: day.isToday ? "rgba(255,255,255,0.5)" : "#B0A8A0", marginBottom: 6, fontFamily: "'IBM Plex Mono', monospace" }}>{day.month}</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 3, flex: 1 }}>
                  {dayTasks.slice(0, 4).map((t: any) => (
                    <div key={t.id} style={{
                      background: day.isToday ? "rgba(255,255,255,0.15)" : "#FFFFFF",
                      border: `1px solid ${day.isToday ? "rgba(255,255,255,0.1)" : "#E9E4D8"}`,
                      borderRadius: 6, padding: "3px 5px", fontSize: 9,
                      color: day.isToday ? "#FFFFFF" : "#111111",
                      textAlign: "left", lineHeight: 1.3, overflow: "hidden",
                      textOverflow: "ellipsis", whiteSpace: "nowrap",
                    }}>
                      {t.title?.length > 16 ? t.title.slice(0, 14) + "..." : t.title}
                    </div>
                  ))}
                  {dayTasks.length > 4 && (
                    <div style={{ fontSize: 8, color: day.isToday ? "rgba(255,255,255,0.6)" : "#B0A8A0", fontFamily: "'IBM Plex Mono', monospace" }}>
                      +{dayTasks.length - 4} more
                    </div>
                  )}
                  {dayTasks.length === 0 && (
                    <div style={{ fontSize: 8, color: day.isToday ? "rgba(255,255,255,0.4)" : "#B0A8A0", fontStyle: "italic", marginTop: "auto" }}>
                      No tasks
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <Card variant="yellow" shadow>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
          <Clock size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Upcoming Events</span>
        </div>
        {events.length > 0 ? events.slice(0, 5).map((ev) => (
          <div key={ev.event_id} style={{ display: "flex", gap: 6, padding: "6px 0", borderBottom: "1px solid #E9E4D8", fontSize: 12, color: "#7A7A7A" }}>
            <div style={{ width: 3, borderRadius: 2, background: "#C9D8FF" }} />
            <div>
              <div style={{ color: "#111111", fontWeight: 500 }}>{ev.title}</div>
              <div style={{ fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" }}>
                {new Date(ev.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {new Date(ev.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          </div>
        )) : <div style={{ color: "#7A7A7A", fontSize: 12 }}>No upcoming events.</div>}
      </Card>
    </div>
  );
}

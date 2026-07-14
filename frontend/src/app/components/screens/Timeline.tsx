import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Calendar } from "lucide-react";
import { Card } from "../shared/Card";
import { PriorityPill } from "../shared/PriorityPill";
import { SourceBadge } from "../shared/SourceBadge";
import { getTasks, getCalendarToday, CalendarEvent } from "../../api/taskpilot";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export function Timeline() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const now = new Date();
  const [month, setMonth] = useState(now.getMonth());
  const [year, setYear] = useState(now.getFullYear());

  useEffect(() => {
    Promise.all([
      getTasks().catch(() => ({ tasks: [] })),
      getCalendarToday().catch(() => ({ events: [] })),
    ]).then(([t, cal]) => {
      setTasks(t.tasks || []);
      setEvents(cal.events || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const today = now.getDate();
  const isCurrentMonth = now.getMonth() === month && now.getFullYear() === year;

  const days: (number | null)[] = [];
  for (let i = 0; i < firstDay; i++) days.push(null);
  for (let d = 1; d <= daysInMonth; d++) days.push(d);

  const todayTasks = tasks.filter(t => t.deadline && new Date(t.deadline).getDate() === today && new Date(t.deadline).getMonth() === now.getMonth());

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <h2 style={{ margin: 0 }}>Timeline</h2>
        <p style={{ color: "#7A7A7A", fontSize: 13, marginTop: 4 }}>
          {loading ? "Loading..." : `${tasks.length} tasks · ${events.length} events today`}
        </p>
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button onClick={() => { if (month === 0) { setMonth(11); setYear(y => y - 1); } else setMonth(m => m - 1); }}
            style={{ background: "none", border: "1px solid #E9E4D8", borderRadius: 10, padding: "6px 10px", cursor: "pointer" }}>
            <ArrowLeft size={14} />
          </button>
          <h3 style={{ margin: 0, fontSize: 18 }}>{MONTHS[month]} {year}</h3>
          <button onClick={() => { if (month === 11) { setMonth(0); setYear(y => y + 1); } else setMonth(m => m + 1); }}
            style={{ background: "none", border: "1px solid #E9E4D8", borderRadius: 10, padding: "6px 10px", cursor: "pointer" }}>
            <ArrowRight size={14} />
          </button>
        </div>
        <button onClick={() => { setMonth(now.getMonth()); setYear(now.getFullYear()); }}
          style={{ background: "#0D0D0D", color: "#FFFFFF", border: "none", padding: "8px 16px", borderRadius: 10, fontSize: 12, cursor: "pointer", fontFamily: "'IBM Plex Mono', monospace" }}>
          Today
        </button>
      </div>

      <Card shadow>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 4 }}>
          {DAYS.map(d => (
            <div key={d} style={{ textAlign: "center", fontSize: 11, color: "#7A7A7A", fontWeight: 500, padding: "8px 0", fontFamily: "'IBM Plex Mono', monospace" }}>{d}</div>
          ))}
          {days.map((d, i) => {
            const isToday = isCurrentMonth && d === today;
            return (
              <div key={i} style={{
                textAlign: "center", padding: "8px 4px", borderRadius: 10,
                background: isToday ? "#0D0D0D" : "transparent",
                color: isToday ? "#FFFFFF" : d ? "#111111" : "transparent",
                fontWeight: isToday ? 600 : 400,
                fontSize: 14, cursor: d ? "pointer" : "default",
                position: "relative",
              }}>
                {d}
              </div>
            );
          })}
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <Card variant="blue" shadow>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
            <Calendar size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Today's Tasks</span>
          </div>
          {todayTasks.length > 0 ? todayTasks.map((task: any) => (
            <div key={task.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "1px solid #E9E4D8" }}>
              <span style={{ color: "#7A7A7A", fontSize: 11, fontFamily: "'IBM Plex Mono', monospace", minWidth: 50 }}>
                {task.deadline ? new Date(task.deadline).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ""}
              </span>
              <span style={{ flex: 1, fontSize: 13, color: "#111111" }}>{task.title}</span>
              <SourceBadge source={task.source || task.source_type} />
              <PriorityPill level={(task.priority ?? "P3") as any} />
            </div>
          )) : <div style={{ color: "#7A7A7A", fontSize: 12 }}>No tasks due today.</div>}
        </Card>

        <Card variant="yellow" shadow>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
            <Calendar size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Today's Events</span>
          </div>
          {events.length > 0 ? events.map((ev) => (
            <div key={ev.event_id} style={{ display: "flex", gap: 6, padding: "8px 0", borderBottom: "1px solid #E9E4D8", fontSize: 12, color: "#7A7A7A" }}>
              <div style={{ width: 3, borderRadius: 2, background: "#C9D8FF" }} />
              <div>
                <div style={{ color: "#111111", fontWeight: 500, fontSize: 13 }}>{ev.title}</div>
                <div style={{ fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" }}>
                  {new Date(ev.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {new Date(ev.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          )) : <div style={{ color: "#7A7A7A", fontSize: 12 }}>No events today.</div>}
        </Card>
      </div>
    </div>
  );
}

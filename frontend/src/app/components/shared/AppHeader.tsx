import { useNavigate, useLocation } from "react-router";
import {
  LayoutDashboard, ListTodo, MessageSquare, Plug,
  BarChart2, Activity, Sparkles, Settings, SparkleIcon
} from "lucide-react";
import { LogoMark } from "./LogoMark";

const NAV_ITEMS = [
  { path: "/daily-plan", label: "Plan", icon: LayoutDashboard },
  { path: "/tasks", label: "Tasks", icon: ListTodo },
  { path: "/assistant", label: "Chat", icon: MessageSquare },
  { path: "/sources", label: "Sources", icon: Plug },
  { path: "/weekly-summary", label: "Weekly", icon: BarChart2 },
  { path: "/extractions", label: "Extractions", icon: Sparkles },
  { path: "/traces", label: "Traces", icon: Activity },
] as const;

export function AppHeader({ planTime }: { planTime?: string }) {
  const navigate = useNavigate();
  const location = useLocation();
  const isLanding = location.pathname === "/";

  if (isLanding) return null;

  return (
    <div
      style={{
        height: 52,
        borderBottom: "1px solid #D9D9D9",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 24px",
        background: "#FFFFFF",
        flexShrink: 0,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
        <button
          onClick={() => navigate("/daily-plan")}
          style={{
            display: "flex", alignItems: "center", gap: 8,
            background: "none", border: "none", cursor: "pointer", padding: 0,
          }}
        >
          <LogoMark size={20} />
          <span style={{ color: "#111111", fontWeight: 700, fontSize: 14, fontFamily: "'Space Grotesk', sans-serif", letterSpacing: "-0.02em" }}>
            TaskPilot
          </span>
        </button>

        <nav style={{ display: "flex", gap: 2 }}>
          {NAV_ITEMS.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "6px 12px",
                  background: isActive ? "#F8F8F6" : "transparent",
                  border: "none",
                  cursor: "pointer",
                  color: isActive ? "#111111" : "#7A7A7A",
                  fontSize: 12,
                  fontWeight: isActive ? 600 : 400,
                  fontFamily: "'Inter', sans-serif",
                  transition: "all 0.15s",
                }}
              >
                <Icon size={14} />
                {item.label}
              </button>
            );
          })}
        </nav>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {planTime && (
          <span
            style={{
              background: "#F8F8F6",
              color: "#7A7A7A",
              fontSize: 11,
              fontFamily: "'IBM Plex Mono', monospace",
              padding: "4px 10px",
              border: "1px solid #D9D9D9",
            }}
          >
            {planTime}
          </span>
        )}
        <button
          onClick={() => navigate("/settings")}
          style={{
            background: "none", border: "none", cursor: "pointer",
            color: location.pathname === "/settings" ? "#111111" : "#7A7A7A",
            padding: "6px",
            display: "flex", alignItems: "center",
          }}
        >
          <Settings size={16} />
        </button>
        <div
          style={{
            width: 30, height: 30,
            background: "#F8F8F6",
            display: "flex", alignItems: "center", justifyContent: "center",
            border: "1px solid #D9D9D9",
            color: "#7A7A7A",
            fontSize: 12, fontWeight: 600,
            fontFamily: "'IBM Plex Mono', monospace",
            cursor: "default",
          }}
        >
          A
        </div>
      </div>
    </div>
  );
}

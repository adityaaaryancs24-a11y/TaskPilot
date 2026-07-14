import { ReactNode, useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { Bot } from "lucide-react";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";
import { RightPanel } from "./RightPanel";
import { LayoutProvider, useLayout } from "./LayoutContext";

const NAV_SHORTCUTS: Record<string, string> = {
  "gd": "/dashboard", "gi": "/inbox", "gp": "/planner",
  "gt": "/timeline", "gh": "/hidden", "gdd": "/dedup-groups",
  "gpr": "/priorities", "gde": "/dependencies", "gr": "/reports",
  "gc": "/chat", "gn": "/notifications", "gs": "/settings",
  "gx": "/traces",
};

function useKeyboardShortcuts() {
  const navigate = useNavigate();
  const { togglePanel } = useLayout();
  let buffer = "";

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "k") { e.preventDefault(); navigate("/chat"); return; }
      if (e.ctrlKey && e.key === "b") { e.preventDefault(); togglePanel(); return; }
      buffer += e.key.toLowerCase();
      if (buffer.length > 3) buffer = buffer.slice(-3);
      for (const [shortcut, path] of Object.entries(NAV_SHORTCUTS)) {
        if (buffer.endsWith(shortcut)) {
          navigate(path);
          buffer = "";
          break;
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);
}

function FloatingAIBtn() {
  const { panelOpen, togglePanel } = useLayout();
  if (panelOpen) return null;
  return (
    <button onClick={togglePanel}
      style={{
        position: "absolute", bottom: 20, right: 20,
        width: 44, height: 44, borderRadius: 14,
        background: "#0D0D0D", border: "none",
        display: "flex", alignItems: "center", justifyContent: "center",
        cursor: "pointer", boxShadow: "0 4px 16px rgba(0,0,0,0.2)",
        zIndex: 100,
      }}>
      <Bot size={20} color="#FFFFFF" />
    </button>
  );
}

function LayoutInner({ children }: { children: ReactNode }) {
  useKeyboardShortcuts();
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window !== "undefined") return (localStorage.getItem("theme") as "light" | "dark") || "light";
    return "light";
  });

  useEffect(() => {
    if (theme === "dark") document.documentElement.classList.add("dark");
    else document.documentElement.classList.remove("dark");
  }, [theme]);

  return (
    <DndProvider backend={HTML5Backend}>
      <div style={{
        display: "flex", height: "100%", width: "100%",
        overflow: "hidden", background: "var(--bg-primary, #F6F2E9)", position: "relative",
      }}>
        <Sidebar />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <TopNav />
          <main style={{ flex: 1, overflow: "auto", display: "flex" }}>
            <div style={{ flex: 1, overflow: "auto", padding: "24px 28px" }}>
              {children}
            </div>
            <RightPanel />
          </main>
        </div>
        <FloatingAIBtn />
      </div>
    </DndProvider>
  );
}

export function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <LayoutProvider>
      <LayoutInner>{children}</LayoutInner>
    </LayoutProvider>
  );
}

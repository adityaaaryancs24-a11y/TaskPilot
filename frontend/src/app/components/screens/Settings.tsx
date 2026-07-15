import { useEffect, useState, useCallback } from "react";
import { Settings2, User, Shield, Bell, Palette, Key, Smartphone, Sun, Moon, Keyboard } from "lucide-react";
import { Card } from "../shared/Card";
import { getMemoryPreferences, getHealth, WebSocketEvent } from "../../api/taskpilot";
import { useWebSocket } from "../../hooks/useWebSocket";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const SETTINGS_SECTIONS = [
  { id: "profile", label: "Profile", icon: User },
  { id: "preferences", label: "Preferences", icon: Palette },
  { id: "integrations", label: "Integrations", icon: Key },
  { id: "theme", label: "Theme", icon: Sun },
  { id: "shortcuts", label: "Shortcuts", icon: Keyboard },
  { id: "notifications", label: "Notifications", icon: Bell, disabled: true },
  { id: "security", label: "Security", icon: Shield, disabled: true },
  { id: "api", label: "API Keys", icon: Key, disabled: true },
  { id: "devices", label: "Devices", icon: Smartphone, disabled: true },
];

export function Settings() {
  const [activeSection, setActiveSection] = useState(() => {
  const params = new URLSearchParams(window.location.search);
  return params.get("tab") || "preferences";
});
  const [prefs, setPrefs] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);
  const [health, setHealth] = useState<any>(null);
  const [githubStatus, setGithubStatus] = useState<{ connected: boolean; github_login?: string }>({ connected: false });

  const refreshGithubStatus = useCallback(() => {
    fetch(`${API_BASE}/auth/github/status`)
      .then(r => r.json())
      .then(setGithubStatus)
      .catch(() => {});
  }, []);

  useEffect(() => {
    getMemoryPreferences()
      .then(data => setPrefs(data.preferences || {}))
      .catch(() => {})
      .finally(() => setLoading(false));
    getHealth().then(h => setHealth(h)).catch(() => {});
  }, []);

  useEffect(() => {
    refreshGithubStatus();
  }, [refreshGithubStatus]);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <h2 style={{ margin: 0 }}>Settings</h2>
        <p style={{ color: "#7A7A7A", fontSize: 13, marginTop: 4 }}>Manage your account and preferences</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 16 }}>
        <Card shadow style={{ padding: 8 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {SETTINGS_SECTIONS.map(section => {
              const Icon = section.icon;
              return (
                <button key={section.id} onClick={() => !section.disabled && setActiveSection(section.id)}
                  style={{
                    display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", borderRadius: 10,
                    background: activeSection === section.id ? "#0D0D0D" : "transparent",
                    color: section.disabled ? "#B0A8A0" : activeSection === section.id ? "#FFFFFF" : "#111111",
                    border: "none", fontSize: 13, cursor: section.disabled ? "not-allowed" : "pointer",
                    fontFamily: "'Inter', sans-serif", transition: "all 0.15s",
                  }}>
                  <Icon size={16} />
                  <span>{section.label}</span>
                  {section.disabled && <span style={{ fontSize: 9, color: "#B0A8A0", fontFamily: "'IBM Plex Mono', monospace" }}>Soon</span>}
                </button>
              );
            })}
          </div>
        </Card>

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {activeSection === "preferences" && (
            <>
              <Card variant="blue" shadow>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
                  <Palette size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>AI Preferences</span>
                </div>
                {loading ? (
                  <div style={{ color: "#7A7A7A", fontSize: 12 }}>Loading preferences...</div>
                ) : Object.keys(prefs).length === 0 ? (
                  <div style={{ color: "#7A7A7A", fontSize: 12 }}>No preferences stored yet. The AI will learn your preferences over time as you provide feedback on tasks.</div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    {Object.entries(prefs).map(([key, val]) => (
                      <div key={key} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #E9E4D8", fontSize: 13 }}>
                        <span style={{ color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", fontSize: 12 }}>{key}</span>
                        <span style={{ color: "#111111", fontWeight: 500 }}>{val}</span>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              <Card variant="yellow" shadow>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
                  <Bell size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>System Status</span>
                </div>
                <div style={{ fontSize: 12, color: "#7A7A7A" }}>
                  <div>Version: <strong>{health?.version ?? "--"}</strong></div>
                  <div>Uptime: <strong>{health?.uptime_seconds ? `${Math.round(health.uptime_seconds / 60)} min` : "--"}</strong></div>
                  <div>Tasks: <strong>{health?.task_count ?? 0}</strong></div>
                  <div>DB: <strong style={{ color: health?.database_connected ? "#BFD78D" : "#F7C5E6" }}>{health?.database_connected ? "Connected" : "Disconnected"}</strong></div>
                  <div>Redis: <strong style={{ color: health?.redis_connected ? "#BFD78D" : "#F7C5E6" }}>{health?.redis_connected ? "Connected" : "Disconnected"}</strong></div>
                </div>
              </Card>

              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                <button onClick={handleSave}
                  style={{ background: "#0D0D0D", color: "#FFFFFF", border: "none", padding: "10px 24px", borderRadius: 12, fontSize: 12, cursor: "pointer", fontFamily: "'IBM Plex Mono', monospace" }}>
                  {saved ? "✓ Saved" : "Save Preferences"}
                </button>
              </div>
            </>
          )}

          {activeSection === "integrations" && (
            <Card variant="blue" shadow>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
                <Key size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Connected Apps</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0" }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: "#111111" }}>GitHub</div>
                  <div style={{ fontSize: 12, color: "#7A7A7A" }}>
                    {githubStatus.connected ? `Connected as @${githubStatus.github_login}` : "Not connected"}
                  </div>
                </div>
                {githubStatus.connected ? (
                  <button
                    onClick={() => {
                      fetch(`${API_BASE}/auth/github/disconnect`, { method: "POST" }).then(refreshGithubStatus);
                    }}
                    style={{ background: "#F6F2E9", color: "#111111", border: "1px solid #E9E4D8", padding: "8px 16px", borderRadius: 10, fontSize: 12, cursor: "pointer", fontFamily: "'IBM Plex Mono', monospace" }}>
                    Disconnect
                  </button>
                ) : (
                  <a href={`${API_BASE}/auth/github/login`}
                    style={{ background: "#0D0D0D", color: "#FFFFFF", textDecoration: "none", padding: "8px 16px", borderRadius: 10, fontSize: 12, fontFamily: "'IBM Plex Mono', monospace" }}>
                    Connect GitHub
                  </a>
                )}
              </div>
            </Card>
          )}

          {activeSection === "theme" && (
            <Card variant="orange" shadow>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
                <Palette size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Appearance</span>
              </div>
              <div style={{ display: "flex", gap: 12 }}>
                {(["light", "dark"] as const).map((t) => {
                  const active = document.documentElement.classList.contains("dark") ? "dark" : "light";
                  return (
                    <button key={t} onClick={() => {
                      if (t === "dark") document.documentElement.classList.add("dark");
                      else document.documentElement.classList.remove("dark");
                      localStorage.setItem("theme", t);
                    }}
                      style={{
                        flex: 1, padding: "16px", borderRadius: 14, cursor: "pointer", textAlign: "center",
                        border: active === t ? "2px solid #F97316" : "1px solid #E9E4D8",
                        background: active === t ? "#F6F2E9" : "#FFFFFF", transition: "all 0.15s",
                      }}>
                      {t === "light" ? <Sun className="w-6 h-6 mx-auto mb-2" style={{ color: "#F97316" }} /> : <Moon className="w-6 h-6 mx-auto mb-2" style={{ color: "#F97316" }} />}
                      <div style={{ fontSize: 13, fontWeight: 600, color: "#111111", textTransform: "capitalize" }}>{t}</div>
                      <div style={{ fontSize: 11, color: "#7A7A7A", marginTop: 2 }}>{t === "light" ? "Warm pastel theme" : "Dark mode"}</div>
                    </button>
                  );
                })}
              </div>
            </Card>
          )}

          {activeSection === "shortcuts" && (
            <Card variant="blue" shadow>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
                <Keyboard size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Keyboard Shortcuts</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {[
                  { keys: "Ctrl+K", action: "Open AI Chat" },
                  { keys: "Ctrl+B", action: "Toggle AI Assistant panel" },
                  { keys: "G then D", action: "Go to Dashboard" },
                  { keys: "G then I", action: "Go to Inbox" },
                  { keys: "G then P", action: "Go to Planner" },
                  { keys: "G then T", action: "Go to Timeline" },
                  { keys: "G then H", action: "Go to Hidden Tasks" },
                  { keys: "G then R", action: "Go to Reports" },
                  { keys: "G then C", action: "Go to Chat" },
                  { keys: "G then N", action: "Go to Notifications" },
                  { keys: "G then S", action: "Go to Settings" },
                  { keys: "G then X", action: "Go to Pipeline Traces" },
                ].map((s, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: i < 11 ? "1px solid #E9E4D8" : "none" }}>
                    <span style={{ fontSize: 12, color: "#7A7A7A" }}>{s.action}</span>
                    <kbd style={{ fontSize: 11, padding: "2px 8px", background: "#F6F2E9", borderRadius: 6, border: "1px solid #E9E4D8", fontFamily: "'IBM Plex Mono', monospace" }}>{s.keys}</kbd>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {activeSection === "profile" && (
            <Card shadow>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
                <User size={14} /> <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Profile</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                  <div style={{ width: 56, height: 56, borderRadius: 16, background: "#C9D8FF", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, fontWeight: 600, color: "#0D0D0D" }}>SA</div>
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 600, color: "#111111" }}>TaskPilot User</div>
                    <div style={{ fontSize: 12, color: "#7A7A7A" }}>user@taskpilot.local</div>
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  {[
                    { label: "Display Name", value: "Default User" },
                    { label: "Email", value: "user@taskpilot.local" },
                    { label: "Timezone", value: Intl.DateTimeFormat().resolvedOptions().timeZone },
                    { label: "Role", value: "User" },
                  ].map((f, i) => (
                    <div key={i}>
                      <div style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 4 }}>{f.label}</div>
                      <input defaultValue={f.value}
                        style={{ width: "100%", padding: "8px 10px", borderRadius: 10, border: "1px solid #E9E4D8", background: "#F6F2E9", fontSize: 13, color: "#111111", fontFamily: "'Inter', sans-serif", outline: "none" }} />
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

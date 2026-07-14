import { useState, useEffect } from "react";
import { Send, Sparkles, PanelRightClose, Loader2 } from "lucide-react";
import { useLayout } from "./LayoutContext";
import { getPlan, chat, ChatResponse } from "../../api/taskpilot";

const SUGGESTIONS = [
  "What should I do next?",
  "Summarize today",
  "Show blockers",
  "Any urgent tasks?",
];

export function RightPanel() {
  const [input, setInput] = useState("");
  const { panelOpen, togglePanel } = useLayout();
  const [greeting, setGreeting] = useState("Ask me anything about your tasks.");
  const [messages, setMessages] = useState<{ role: "assistant" | "user"; text: string }[]>([
    { role: "assistant", text: greeting },
  ]);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (!panelOpen) return;
    getPlan().then(p => {
      const h = new Date().getHours();
      const timeGreeting = h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
      const count = p.ranked_tasks?.length ?? 0;
      const top = p.top_priorities?.[0];
      const msg = top
        ? `${timeGreeting}! You have ${count} tasks. Your top priority is "${top.title}".`
        : `${timeGreeting}! You have ${count} tasks tracked.`;
      setGreeting(msg);
      setMessages([{ role: "assistant", text: msg }]);
    }).catch(() => {
      setMessages([{ role: "assistant", text: greeting }]);
    });
  }, [panelOpen]);

  const handleSend = async () => {
    const q = input.trim();
    if (!q || sending) return;
    setMessages(prev => [...prev, { role: "user", text: q }]);
    setInput("");
    setSending(true);
    try {
      const res: ChatResponse = await chat(q);
      setMessages(prev => [...prev, { role: "assistant", text: res.answer }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", text: "Sorry, I couldn't process that request." }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div style={{
      width: panelOpen ? 340 : 0, flexShrink: 0, height: "100%",
      overflow: "hidden", transition: "width 0.25s ease",
      borderLeft: panelOpen ? "1px solid #E9E4D8" : "none",
      background: "#FFFDF8",
    }}>
      <div style={{
        width: 340, height: "100%",
        display: "flex", flexDirection: "column",
        overflow: "hidden",
      }}>
      <div style={{
        padding: "16px 18px", borderBottom: "1px solid #E9E4D8",
        display: "flex", alignItems: "center", gap: 8,
      }}>
        <Sparkles size={16} color="#0D0D0D" />
        <span style={{ fontWeight: 600, fontSize: 14, fontFamily: "'Space Grotesk', sans-serif", flex: 1 }}>
          AI Assistant
        </span>
        <button onClick={togglePanel}
          style={{ background: "none", border: "none", cursor: "pointer", color: "#7A7A7A", display: "flex", padding: 0 }}>
          <PanelRightClose size={15} />
        </button>
      </div>

      <div style={{
        flex: 1, overflow: "auto", padding: "16px 18px",
        display: "flex", flexDirection: "column", gap: 8,
      }}>
        {messages.map((m, i) => (
          <div key={i} style={{
            padding: "10px 14px", borderRadius: 14,
            background: m.role === "assistant" ? "#C9D8FF" : "#E9E4D8",
            maxWidth: "90%", alignSelf: m.role === "assistant" ? "flex-start" : "flex-end",
          }}>
            <span style={{ fontSize: 13, color: "#111111", lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
              {m.text}
            </span>
          </div>
        ))}
        {sending && (
          <div style={{ padding: "10px 14px", alignSelf: "flex-start" }}>
            <Loader2 size={16} color="#7A7A7A" style={{ animation: "spin 1s linear infinite" }} />
          </div>
        )}

        <div style={{
          display: "flex", flexDirection: "column", gap: 4, marginTop: 16,
        }}>
          <span style={{ fontSize: 11, color: "#B0A8A0", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Suggestions
          </span>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => { setInput(s); }}
              style={{
                background: "none", border: "1px solid #E9E4D8",
                borderRadius: 10, padding: "8px 12px",
                fontSize: 12, color: "#7A7A7A", cursor: "pointer",
                textAlign: "left", fontFamily: "'Inter', sans-serif",
              }}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div style={{
        padding: "12px 14px", borderTop: "1px solid #E9E4D8",
        display: "flex", alignItems: "center", gap: 8,
      }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask me anything..."
          style={{
            flex: 1, border: "1px solid #E9E4D8", borderRadius: 12,
            padding: "10px 12px", fontSize: 13, outline: "none",
            background: "#FFFFFF", color: "#111111",
          }}
        />
        <button onClick={handleSend} disabled={sending || !input.trim()}
          style={{
            width: 36, height: 36, borderRadius: 10,
            background: input.trim() && !sending ? "#0D0D0D" : "#E9E4D8",
            border: "none",
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: input.trim() && !sending ? "pointer" : "not-allowed",
            flexShrink: 0,
          }}>
          {sending ? <Loader2 size={14} color="#FFFFFF" /> : <Send size={14} color={input.trim() ? "#FFFFFF" : "#B0A8A0"} />}
        </button>
      </div>
      </div>
    </div>
  );
}

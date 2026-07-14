import { useState } from "react";
import { Send } from "lucide-react";
import { AppHeader } from "../shared/AppHeader";
import { SparkleIcon } from "../shared/SparkleIcon";
import { chat } from "../../api/taskpilot";

interface ChatMessage {
  role: "user" | "ai";
  content: string;
  citations?: string[];
}

export function Screen3() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);
    try {
      const resp = await chat(userMsg);
      setMessages(prev => [...prev, { role: "ai", content: resp.answer, citations: resp.referenced_task_ids }]);
    } catch {
      setMessages(prev => [...prev, { role: "ai", content: "I'm sorry, I couldn't process that request. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <AppHeader />
      <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", padding: 0 }}>
        <div style={{ padding: "20px 28px 16px", borderBottom: "1px solid #D9D9D9" }}>
          <h2 style={{ margin: 0 }}>Chat Assistant</h2>
          <p style={{ color: "#7A7A7A", fontSize: 12, marginTop: 4 }}>Ask anything about your tasks, priorities, or sources</p>
        </div>

        <div style={{ flex: 1, overflow: "auto", padding: "24px 28px", display: "flex", flexDirection: "column", gap: 16 }}>
          {messages.length === 0 && (
            <div style={{ textAlign: "center", color: "#7A7A7A", fontSize: 13, marginTop: 40 }}>
              <SparkleIcon size={20} color="#F97316" />
              <p style={{ marginTop: 12 }}>Ask me about your tasks, priorities, or any source.</p>
              <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 12, flexWrap: "wrap" }}>
                {["What's my #1 priority?", "Any blockers?", "Summarize recent emails"].map(q => (
                  <button key={q} onClick={() => { setInput(q); }}
                    style={{ background: "none", border: "1px solid #D9D9D9", padding: "5px 12px", color: "#7A7A7A", fontSize: 12, cursor: "pointer", fontFamily: "'IBM Plex Mono', monospace" }}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start", gap: 10, alignItems: "flex-start" }}>
              {msg.role === "ai" && (
                <div style={{ width: 30, height: 30, border: "1px solid #D9D9D9", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 2 }}>
                  <SparkleIcon size={14} />
                </div>
              )}
              <div style={{ maxWidth: msg.role === "user" ? 420 : 580, border: "1px solid #D9D9D9", padding: "12px 16px", background: msg.role === "ai" ? "#FFFFFF" : "#F8F8F6" }}>
                <span style={{ color: "#111111", fontSize: 13, lineHeight: 1.5 }}>{msg.content}</span>
                {msg.citations && msg.citations.length > 0 && (
                  <div style={{ marginTop: 8, color: "#7A7A7A", fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>
                    References: {msg.citations.join(", ")}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div style={{ display: "flex", justifyContent: "flex-start", gap: 10 }}>
              <div style={{ width: 30, height: 30, border: "1px solid #D9D9D9", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <SparkleIcon size={14} />
              </div>
              <div style={{ border: "1px solid #D9D9D9", padding: "12px 16px", background: "#FFFFFF" }}>
                <span style={{ color: "#7A7A7A", fontSize: 13, fontFamily: "'IBM Plex Mono', monospace" }}>Thinking...</span>
              </div>
            </div>
          )}
        </div>

        <div style={{ padding: "0 28px 24px" }}>
          <div style={{ display: "flex", alignItems: "center", border: "1px solid #D9D9D9", padding: "10px 14px", gap: 10, background: "#FFFFFF" }}>
            <input value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSend()}
              placeholder="Ask about your tasks, priorities, or any source…"
              style={{ flex: 1, background: "none", border: "none", outline: "none", color: "#111111", fontSize: 13, fontFamily: "'Inter', sans-serif" }} />
            <button onClick={handleSend}
              style={{ background: "#111111", border: "none", width: 32, height: 32, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flexShrink: 0 }}>
              <Send size={14} color="#FFFFFF" />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Sparkles, MessageSquare } from "lucide-react";
import { chat } from "../api/taskpilot";

export function ChatPage() {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([
    { role: "assistant", content: "Ask me anything about your tasks — priorities, blockers, summaries, or what to do next." }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const sendMessage = async () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: q }]);
    setLoading(true);
    try {
      const res = await chat(q);
      setMessages(prev => [...prev, { role: "assistant", content: res.answer }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, I encountered an error." }]);
    } finally { setLoading(false); }
  };

  const suggestions = ["What's my top priority?", "Summarize my emails", "What's blocking me?", "Show my plan for today"];

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", background: "#FFFFFF", borderRadius: 16, border: "1px solid #E9E4D8", overflow: "hidden" }}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid #E9E4D8", display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 32, height: 32, borderRadius: 10, background: "#F97316", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <MessageSquare className="w-4 h-4 text-white" />
        </div>
        <div>
          <h3 className="font-semibold" style={{ fontSize: 14, margin: 0 }}>AI Assistant</h3>
          <p className="text-xs" style={{ color: "#7A7A7A", margin: 0 }}>Full conversation with TaskPilot AI</p>
        </div>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "16px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ display: "flex", gap: 10, justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}>
            {msg.role === "assistant" && (
              <div style={{ width: 28, height: 28, borderRadius: 8, background: "#F6F2E9", border: "1px solid #E9E4D8", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <Bot className="w-3.5 h-3.5" style={{ color: "#7A7A7A" }} />
              </div>
            )}
            <div style={{ maxWidth: "75%", padding: "10px 14px", borderRadius: 16, fontSize: 13, lineHeight: 1.5, whiteSpace: "pre-wrap",
              background: msg.role === "user" ? "#F97316" : "#F6F2E9",
              color: msg.role === "user" ? "#FFFFFF" : "#111111",
            }}>
              {msg.content}
            </div>
            {msg.role === "user" && (
              <div style={{ width: 28, height: 28, borderRadius: 8, background: "#F97316", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <User className="w-3.5 h-3.5 text-white" />
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div style={{ display: "flex", gap: 10 }}>
            <div style={{ width: 28, height: 28, borderRadius: 8, background: "#F6F2E9", border: "1px solid #E9E4D8", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Bot className="w-3.5 h-3.5" style={{ color: "#7A7A7A" }} />
            </div>
            <div style={{ background: "#F6F2E9", padding: "10px 14px", borderRadius: 16 }}>
              <div style={{ display: "flex", gap: 3 }}>
                <span className="w-1.5 h-1.5 bg-[#7A7A7A] rounded-full animate-bounce" />
                <span className="w-1.5 h-1.5 bg-[#7A7A7A] rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 bg-[#7A7A7A] rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        {messages.length <= 1 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
            {suggestions.map((s) => (
              <button key={s} onClick={() => { setInput(s); }}
                style={{ padding: "6px 12px", background: "#F6F2E9", border: "1px solid #E9E4D8", borderRadius: 10, fontSize: 12, cursor: "pointer", color: "#7A7A7A", transition: "all 0.15s" }}>
                {s}
              </button>
            ))}
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div style={{ padding: "12px 20px", borderTop: "1px solid #E9E4D8", display: "flex", gap: 8 }}>
        <input type="text" value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Ask about your tasks..."
          style={{ flex: 1, padding: "8px 14px", border: "1px solid #E9E4D8", borderRadius: 12, fontSize: 13, outline: "none" }} />
        <button onClick={sendMessage} disabled={!input.trim() || loading}
          style={{ padding: "8px 16px", background: "#F97316", color: "#FFF", border: "none", borderRadius: 12, cursor: "pointer", opacity: !input.trim() || loading ? 0.5 : 1 }}>
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

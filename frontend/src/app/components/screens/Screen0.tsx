import { useState, useEffect, useRef } from "react";
import { ArrowRight, Sparkles, Zap, GitBranch, BarChart3, Puzzle, Inbox, CalendarRange } from "lucide-react";

// ── Typing animation ──────────────────────────────────────────────────────────
function useTyping(phrases: string[], speed = 52, pause = 2000) {
  const [display, setDisplay] = useState("");
  const [idx, setIdx] = useState(0);
  const [char, setChar] = useState(0);
  const [del, setDel] = useState(false);
  useEffect(() => {
    const cur = phrases[idx];
    const t = setTimeout(() => {
      if (!del) {
        if (char < cur.length) { setDisplay(cur.slice(0, char + 1)); setChar(c => c + 1); }
        else setTimeout(() => setDel(true), pause);
      } else {
        if (char > 0) { setDisplay(cur.slice(0, char - 1)); setChar(c => c - 1); }
        else { setDel(false); setIdx(i => (i + 1) % phrases.length); }
      }
    }, del ? speed / 2 : speed);
    return () => clearTimeout(t);
  }, [char, del, idx, phrases, speed, pause]);
  return display;
}

// ── Particle canvas ───────────────────────────────────────────────────────────
function ParticleField() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    const W = canvas.width = canvas.offsetWidth;
    const H = canvas.height = canvas.offsetHeight;
    const particles = Array.from({ length: 55 }, () => ({
      x: Math.random() * W, y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.3, vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 1.5 + 0.5, opacity: Math.random() * 0.4 + 0.1,
    }));
    let raf = 0;
    const draw = () => {
      ctx.clearRect(0, 0, W, H);
      particles.forEach(p => {
        p.x = (p.x + p.vx + W) % W;
        p.y = (p.y + p.vy + H) % H;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(13,13,13,${p.opacity})`;
        ctx.fill();
      });
      // draw connecting lines
      particles.forEach((a, i) => {
        particles.slice(i + 1).forEach(b => {
          const d = Math.hypot(a.x - b.x, a.y - b.y);
          if (d < 80) {
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.strokeStyle = `rgba(13,13,13,${0.06 * (1 - d / 80)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        });
      });
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, []);
  return <canvas ref={ref} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }} />;
}

// ── Live mini-dashboard preview ───────────────────────────────────────────────
function LivePreview() {
  const [tick, setTick] = useState(0);
  const [pulse, setPulse] = useState(false);
  useEffect(() => {
    const t = setInterval(() => {
      setTick(n => n + 1);
      setPulse(true);
      setTimeout(() => setPulse(false), 600);
    }, 2600);
    return () => clearInterval(t);
  }, []);

  const tasks = [
    { title: "Fix Payment API Bug", badge: "P1", color: "#F7C5E6", bar: 92, time: "Due in 2h", src: "JIRA" },
    { title: "Review PR #247 Auth", badge: "P2", color: "#C9D8FF", bar: 75, time: "Due in 4h", src: "GH" },
    { title: "Team sync prep", badge: "P3", color: "#BFD78D", bar: 54, time: "Due in 6h", src: "SLACK" },
  ];

  const kpis = [
    { label: "Active", value: 14 + (tick % 3), color: "#F7C5E6" },
    { label: "AI Score", value: 87 + (tick % 4), color: "#F5D66E" },
    { label: "Found", value: 2 + (tick % 2), color: "#BFD78D" },
    { label: "Hrs", value: "4.5", color: "#C9D8FF" },
  ];

  return (
    <div style={{
      background: "#FFFFFF", borderRadius: 24, border: "1px solid #E9E4D8",
      padding: 24, boxShadow: "0 20px 60px rgba(0,0,0,0.10)",
      position: "relative", overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#22863a", display: "inline-block", boxShadow: pulse ? "0 0 0 4px rgba(34,134,58,0.2)" : "none", transition: "box-shadow 0.4s" }} />
          <span style={{ fontSize: 11, fontFamily: "'IBM Plex Mono', monospace", color: "#7A7A7A", fontWeight: 600, letterSpacing: "0.06em" }}>LIVE · AI DASHBOARD</span>
        </div>
        <span style={{ fontSize: 11, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace" }}>{new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
      </div>

      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 8, marginBottom: 14 }}>
        {kpis.map(k => (
          <div key={k.label} style={{ background: k.color, borderRadius: 12, padding: "10px 12px", transition: "all 0.4s" }}>
            <div style={{ fontSize: 9, color: "#7A7A7A", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 3, textTransform: "uppercase", letterSpacing: "0.05em" }}>{k.label}</div>
            <div style={{ fontSize: 18, fontWeight: 800, fontFamily: "'Space Grotesk', sans-serif", color: "#0D0D0D" }}>{k.value}</div>
          </div>
        ))}
      </div>

      {/* Tasks */}
      <div style={{ fontSize: 9, fontFamily: "'IBM Plex Mono', monospace", color: "#B0A8A0", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 8 }}>⚡ TOP PRIORITIES · AI-RANKED</div>
      {tasks.map((t, i) => (
        <div key={t.title} style={{
          background: "#FAFAF8", border: "1px solid #F0EDE4", borderRadius: 14,
          padding: "11px 14px", marginBottom: i < 2 ? 7 : 0,
          opacity: pulse && i === 0 ? 0.85 : 1, transition: "opacity 0.3s",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
              <span style={{ background: t.color, fontSize: 9, fontWeight: 700, padding: "2px 6px", borderRadius: 6, fontFamily: "'IBM Plex Mono', monospace" }}>{t.badge}</span>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#111" }}>{t.title}</span>
            </div>
            <span style={{ fontSize: 9, color: "#B0A8A0", fontFamily: "'IBM Plex Mono', monospace" }}>{t.src}</span>
          </div>
          <div style={{ height: 3, background: "#F0EDE4", borderRadius: 3, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${t.bar + (tick % 3)}%`, background: "#0D0D0D", borderRadius: 3, transition: "width 1.2s cubic-bezier(0.4,0,0.2,1)" }} />
          </div>
          <div style={{ fontSize: 9, color: "#B0A8A0", marginTop: 4, fontFamily: "'IBM Plex Mono', monospace" }}>{t.time}</div>
        </div>
      ))}
    </div>
  );
}

// ── Floating badge ─────────────────────────────────────────────────────────────
function FloatBadge({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: "#FFFFFF", border: "1px solid #E9E4D8",
      borderRadius: 14, padding: "8px 14px", fontSize: 12,
      boxShadow: "0 4px 20px rgba(0,0,0,0.08)", fontWeight: 500,
      display: "flex", alignItems: "center", gap: 7, whiteSpace: "nowrap",
      ...style,
    }}>
      {children}
    </div>
  );
}

const FEATURES = [
  { icon: Inbox, label: "Unified Inbox", desc: "All tasks from Jira, GitHub, Slack and Outlook — one feed, no noise.", accent: "#F7C5E6" },
  { icon: Sparkles, label: "Hidden Task AI", desc: "Extracts action items from emails and meeting transcripts automatically.", accent: "#DCC7F7" },
  { icon: BarChart3, label: "AI Prioritization", desc: "Smart scores based on urgency, impact, dependencies and deadlines.", accent: "#C9D8FF" },
  { icon: GitBranch, label: "Dependency Graph", desc: "Visual map of task blockers — know what unblocks your team.", accent: "#BFD78D" },
  { icon: CalendarRange, label: "Smart Planner", desc: "Auto-generated daily plans with focus blocks and time estimates.", accent: "#F5D66E" },
  { icon: Puzzle, label: "Deep Integrations", desc: "Native connections to every tool your team already uses.", accent: "#FAD6B3" },
];

const STATS = [
  { value: "4.2h", label: "Saved per engineer / week" },
  { value: "87%", label: "Task prioritization accuracy" },
  { value: "6+", label: "Integrations out of the box" },
  { value: "< 5s", label: "To generate your daily plan" },
];

export function Screen0({ onStart }: { onStart: () => void }) {
  const typed = useTyping([
    "ranking your tasks by impact",
    "monitoring 6 live integrations",
    "surfacing hidden blockers",
    "scheduling your focus blocks",
    "deduplicating across Jira & GitHub",
  ]);

  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const el = document.querySelector(".landing-scroll") as HTMLElement;
    if (!el) return;
    const handler = () => setScrolled(el.scrollTop > 40);
    el.addEventListener("scroll", handler);
    return () => el.removeEventListener("scroll", handler);
  }, []);

  return (
    <div className="landing-scroll" style={{
      width: "100%", minHeight: "100%",
      background: "#F6F2E9", fontFamily: "'Inter', sans-serif",
      overflowY: "auto", overflowX: "hidden",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
        @keyframes fadeUp { from{opacity:0;transform:translateY(22px)} to{opacity:1;transform:translateY(0)} }
        @keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)} }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes badgeIn { from{opacity:0;transform:scale(0.85)} to{opacity:1;transform:scale(1)} }
        .feat-card:hover { transform: translateY(-4px); box-shadow: 0 12px 36px rgba(0,0,0,0.09)!important; }
        .feat-card { transition: transform 0.25s, box-shadow 0.25s; }
        .cta-primary:hover { background: #2a2a2a!important; transform: scale(1.03); }
        .cta-primary { transition: background 0.2s, transform 0.15s; }
        .cta-ghost:hover { background: #EEE9DC!important; }
        .cta-ghost { transition: background 0.2s; }
        .stat-item:hover .stat-value { transform: scale(1.06); }
        .stat-value { transition: transform 0.2s; display: inline-block; }
        .nav-blur { backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
      `}</style>

      {/* ── Nav ── */}
      <div className="nav-blur" style={{
        position: "sticky", top: 0, zIndex: 100,
        borderBottom: "1px solid rgba(233,228,216,0.7)",
        padding: "14px 40px",
        background: scrolled ? "rgba(246,242,233,0.88)" : "rgba(246,242,233,0.6)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        transition: "background 0.3s",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 34, height: 34, borderRadius: 10, background: "#0D0D0D",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Sparkles size={16} color="#FFFFFF" />
          </div>
          <span style={{ fontWeight: 700, fontSize: 18, fontFamily: "'Space Grotesk', sans-serif", color: "#0D0D0D" }}>TaskPilot</span>
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          {(["Features", "How it Works", "Stats"] as const).map(l => (
            <button key={l} style={{ background: "none", border: "none", padding: "8px 14px", fontSize: 13, color: "#7A7A7A", cursor: "pointer", borderRadius: 10, fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => (e.currentTarget.style.color = "#0D0D0D")}
              onMouseLeave={e => (e.currentTarget.style.color = "#7A7A7A")}
            >{l}</button>
          ))}
          <button className="cta-primary" onClick={onStart} style={{
            background: "#0D0D0D", color: "#FFFFFF", border: "none",
            padding: "10px 22px", borderRadius: 12, fontSize: 13, fontWeight: 600, cursor: "pointer",
            display: "flex", alignItems: "center", gap: 7, fontFamily: "'Space Grotesk', sans-serif",
          }}>
            Get Started <ArrowRight size={13} />
          </button>
        </div>
      </div>

      {/* ── Hero ── */}
      <div style={{ position: "relative", overflow: "hidden", padding: "80px 40px 60px", maxWidth: 1140, margin: "0 auto" }}>
        <ParticleField />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 440px", gap: 64, alignItems: "center", position: "relative", zIndex: 1 }}>
          {/* Left */}
          <div style={{ animation: "fadeUp 0.6s ease both" }}>
            <div style={{
              display: "inline-flex", alignItems: "center", gap: 8,
              background: "#0D0D0D", color: "#F6F2E9", borderRadius: 40,
              padding: "6px 16px", fontSize: 11, fontFamily: "'IBM Plex Mono', monospace",
              fontWeight: 500, marginBottom: 22, letterSpacing: "0.04em",
            }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#BFD78D", animation: "blink 1.4s step-end infinite" }} />
              AI IS CURRENTLY {typed}<span style={{ borderRight: "1.5px solid #F6F2E9", animation: "blink 0.9s step-end infinite", marginLeft: 1 }} />
            </div>

            <h1 style={{
              fontSize: 54, margin: "0 0 20px", lineHeight: 1.08,
              fontFamily: "'Space Grotesk', sans-serif", fontWeight: 800, color: "#0D0D0D",
              letterSpacing: "-0.02em",
            }}>
              Your AI Chief<br />
              <span style={{ color: "#0D0D0D", position: "relative" }}>
                of Staff
                <span style={{
                  position: "absolute", bottom: -2, left: 0, right: 0, height: 4,
                  background: "linear-gradient(90deg, #F7C5E6, #DCC7F7, #C9D8FF)",
                  borderRadius: 4,
                }} />
              </span>
              {" "}for Eng.
            </h1>

            <p style={{
              fontSize: 17, color: "#6A6A6A", lineHeight: 1.65,
              margin: "0 0 34px", maxWidth: 470,
            }}>
              TaskPilot unifies tasks from Jira, Slack, GitHub and email into one AI-powered dashboard — it prioritizes, plans, and surfaces what actually matters.
            </p>

            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <button className="cta-primary" onClick={onStart} style={{
                background: "#0D0D0D", color: "#FFFFFF", border: "none",
                padding: "15px 32px", borderRadius: 16, fontSize: 15, fontWeight: 700,
                cursor: "pointer", display: "flex", alignItems: "center", gap: 9,
                fontFamily: "'Space Grotesk', sans-serif",
              }}>
                Open Dashboard <ArrowRight size={16} />
              </button>
              <button className="cta-ghost" onClick={onStart} style={{
                background: "transparent", border: "1.5px solid #D4CEC2", borderRadius: 16,
                padding: "15px 28px", fontSize: 14, fontWeight: 500, cursor: "pointer",
                color: "#0D0D0D", fontFamily: "'Space Grotesk', sans-serif",
              }}>
                Watch Demo →
              </button>
            </div>

            {/* Trust signals */}
            <div style={{ marginTop: 32, display: "flex", gap: 16, flexWrap: "wrap" }}>
              {["✓ No credit card", "✓ Connects in 2 min", "✓ Works with your stack"].map(t => (
                <span key={t} style={{ fontSize: 12, color: "#8A8478", fontFamily: "'IBM Plex Mono', monospace" }}>{t}</span>
              ))}
            </div>
          </div>

          {/* Right: Live preview */}
          <div style={{ animation: "fadeUp 0.7s 0.15s ease both", position: "relative" }}>
            {/* Floating badges */}
            <FloatBadge style={{ position: "absolute", top: -20, right: -24, animation: "float 3.5s ease-in-out infinite", zIndex: 2 }}>
              <Zap size={13} color="#F97316" /> AI saved you 4.2h today
            </FloatBadge>
            <FloatBadge style={{ position: "absolute", bottom: 30, left: -36, animation: "float 4s 1s ease-in-out infinite", zIndex: 2 }}>
              <span style={{ width: 7, height: 7, background: "#22863a", borderRadius: "50%", flexShrink: 0 }} /> 6 sources synced
            </FloatBadge>
            <LivePreview />
          </div>
        </div>
      </div>

      {/* ── Stats strip ── */}
      <div style={{
        borderTop: "1px solid #E9E4D8", borderBottom: "1px solid #E9E4D8",
        background: "#FFFFFF", padding: "32px 40px",
      }}>
        <div style={{ maxWidth: 900, margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 0 }}>
          {STATS.map((s, i) => (
            <div key={s.label} className="stat-item" style={{
              textAlign: "center", padding: "0 24px",
              borderRight: i < 3 ? "1px solid #E9E4D8" : "none",
            }}>
              <div className="stat-value" style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 36, fontWeight: 800, color: "#0D0D0D", lineHeight: 1 }}>{s.value}</div>
              <div style={{ fontSize: 12, color: "#8A8478", marginTop: 6, fontFamily: "'IBM Plex Mono', monospace" }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Problem section ── */}
      <div style={{ padding: "72px 40px", maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 44 }}>
          <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#B0A8A0", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 12 }}>the problem</div>
          <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 38, fontWeight: 800, margin: "0 0 14px", color: "#0D0D0D", letterSpacing: "-0.01em" }}>Engineers lose 4+ hours a week</h2>
          <p style={{ color: "#8A8478", fontSize: 15, maxWidth: 460, margin: "0 auto" }}>just figuring out what to work on — not actually working.</p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
          {[
            { emoji: "🔄", label: "Context Switching", desc: "Jumping between 6+ tools to find what matters next.", color: "#F7C5E6" },
            { emoji: "👻", label: "Hidden Tasks", desc: "Action items buried in emails, Slack threads, and meeting notes.", color: "#DCC7F7" },
            { emoji: "⏰", label: "Missed Deadlines", desc: "No unified view of what's due and who's blocked.", color: "#FAD6B3" },
            { emoji: "🔌", label: "Tool Overload", desc: "Too many platforms, no single source of truth.", color: "#C9D8FF" },
          ].map((p, i) => (
            <div key={p.label} className="feat-card" style={{
              background: "#FFFFFF", borderRadius: 20, border: "1px solid #E9E4D8",
              padding: "28px 22px", animation: `fadeUp 0.5s ${0.1 * i}s ease both`,
            }}>
              <div style={{ fontSize: 32, marginBottom: 14 }}>{p.emoji}</div>
              <div style={{ height: 3, width: 32, borderRadius: 2, background: p.color, marginBottom: 14 }} />
              <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 7, fontFamily: "'Space Grotesk', sans-serif" }}>{p.label}</div>
              <div style={{ color: "#8A8478", fontSize: 13, lineHeight: 1.6 }}>{p.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Features ── */}
      <div style={{ padding: "0 40px 72px", maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 44 }}>
          <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#B0A8A0", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 12 }}>the solution</div>
          <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 38, fontWeight: 800, margin: "0 0 14px", color: "#0D0D0D", letterSpacing: "-0.01em" }}>Everything in one place</h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14 }}>
          {FEATURES.map((f, i) => {
            const Icon = f.icon;
            return (
              <div key={f.label} className="feat-card" style={{
                background: "#FFFFFF", borderRadius: 20, border: "1px solid #E9E4D8",
                padding: "28px 24px", animation: `fadeUp 0.5s ${0.08 * i}s ease both`,
              }}>
                <div style={{
                  width: 44, height: 44, borderRadius: 14, background: f.accent,
                  display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 18,
                }}>
                  <Icon size={20} color="#0D0D0D" />
                </div>
                <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8, fontFamily: "'Space Grotesk', sans-serif" }}>{f.label}</div>
                <div style={{ color: "#8A8478", fontSize: 13, lineHeight: 1.65 }}>{f.desc}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── How it works ── */}
      <div style={{ background: "#0D0D0D", padding: "72px 40px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 52 }}>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#5A5A5A", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 12 }}>how it works</div>
            <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 36, fontWeight: 800, margin: 0, color: "#F6F2E9", letterSpacing: "-0.01em" }}>From chaos to clarity in seconds</h2>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 0, position: "relative" }}>
            {/* connector line */}
            <div style={{ position: "absolute", top: 22, left: "12.5%", right: "12.5%", height: 1, background: "rgba(255,255,255,0.12)", zIndex: 0 }} />
            {[
              { step: "01", label: "Connect Sources", desc: "Link Jira, GitHub, Slack, Outlook in 2 minutes.", color: "#F7C5E6" },
              { step: "02", label: "AI Understands", desc: "Extracts and deduplicates tasks across all sources.", color: "#DCC7F7" },
              { step: "03", label: "Prioritizes", desc: "Scores every task by urgency, impact & dependencies.", color: "#C9D8FF" },
              { step: "04", label: "Plans Your Day", desc: "Generates a time-blocked plan, automatically.", color: "#BFD78D" },
            ].map((s, i) => (
              <div key={s.step} style={{ textAlign: "center", padding: "0 20px", position: "relative", zIndex: 1 }}>
                <div style={{
                  width: 44, height: 44, borderRadius: "50%", background: s.color,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  margin: "0 auto 16px",
                  fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700, fontSize: 13, color: "#0D0D0D",
                }}>{s.step}</div>
                <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8, color: "#F6F2E9", fontFamily: "'Space Grotesk', sans-serif" }}>{s.label}</div>
                <div style={{ color: "#6A6A6A", fontSize: 12, lineHeight: 1.6 }}>{s.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── CTA ── */}
      <div style={{ padding: "80px 40px", textAlign: "center" }}>
        <div style={{ maxWidth: 560, margin: "0 auto" }}>
          <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 42, fontWeight: 800, margin: "0 0 18px", color: "#0D0D0D", letterSpacing: "-0.02em", lineHeight: 1.1 }}>
            Stop guessing.<br />Start shipping.
          </h2>
          <p style={{ color: "#8A8478", fontSize: 15, margin: "0 0 36px", lineHeight: 1.6 }}>
            Your team's highest-impact task is waiting. Let AI find it.
          </p>
          <button className="cta-primary" onClick={onStart} style={{
            background: "#0D0D0D", color: "#FFFFFF", border: "none",
            padding: "18px 48px", borderRadius: 18, fontSize: 16, fontWeight: 700,
            cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 10,
            fontFamily: "'Space Grotesk', sans-serif",
          }}>
            Open Dashboard <ArrowRight size={17} />
          </button>
        </div>
      </div>

      {/* ── Footer ── */}
      <div style={{ borderTop: "1px solid #E9E4D8", padding: "24px 40px", display: "flex", justifyContent: "space-between", alignItems: "center", color: "#B0A8A0", fontSize: 12, fontFamily: "'IBM Plex Mono', monospace" }}>
        <span>© {new Date().getFullYear()} TaskPilot AI</span>
        <span>Built for engineers who deserve better tooling.</span>
      </div>
    </div>
  );
}
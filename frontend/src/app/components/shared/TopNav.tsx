import { useState } from "react";
import { Search, Bell, Settings } from "lucide-react";
import { useNavigate } from "react-router";
import { useLayout } from "./LayoutContext";

export function TopNav() {
  const navigate = useNavigate();
  const { togglePanel } = useLayout();
  const [searchVal, setSearchVal] = useState("");

  const handleSearch = () => {
    const q = searchVal.trim();
    if (!q) return;
    navigate(`/inbox?search=${encodeURIComponent(q)}`);
  };

  return (
    <div style={{
      height: 60, flexShrink: 0,
      display: "flex", alignItems: "center",
      gap: 12, padding: "0 16px",
      borderBottom: "1px solid #E9E4D8",
      background: "#F6F2E9",
    }}>
      <div style={{
        flex: 1, display: "flex", alignItems: "center", gap: 8,
        background: "#FFFFFF", borderRadius: 14, padding: "8px 14px",
        border: "1px solid #E9E4D8", maxWidth: 480,
      }}>
        <Search size={15} color="#B0A8A0" />
        <input
          value={searchVal}
          onChange={(e) => setSearchVal(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search tasks, emails, blockers..."
          style={{
            flex: 1, border: "none", outline: "none",
            background: "none", fontSize: 13, color: "#111111",
          }}
        />
      </div>

      <button
        onClick={() => navigate("/notifications")}
        style={{
          width: 36, height: 36, borderRadius: 10,
          border: "1px solid #E9E4D8", background: "#FFFFFF",
          display: "flex", alignItems: "center", justifyContent: "center",
          cursor: "pointer", position: "relative",
        }}
      >
        <Bell size={16} color="#7A7A7A" />
      </button>

      <button
        onClick={() => navigate("/settings")}
        style={{
          width: 36, height: 36, borderRadius: 10,
          border: "1px solid #E9E4D8", background: "#FFFFFF",
          display: "flex", alignItems: "center", justifyContent: "center",
          cursor: "pointer",
        }}
      >
        <Settings size={16} color="#7A7A7A" />
      </button>

      <div style={{
        width: 36, height: 36, borderRadius: 10,
        background: "#0D0D0D",
        display: "flex", alignItems: "center", justifyContent: "center",
        color: "#FFFFFF", fontSize: 13, fontWeight: 600,
        fontFamily: "'IBM Plex Mono', monospace", cursor: "default",
      }}>
        A
      </div>
    </div>
  );
}

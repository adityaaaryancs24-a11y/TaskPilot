const STATUS_MAP: Record<string, { bg: string; color: string }> = {
  "In Progress": { bg: "#C9D8FF", color: "#0D0D0D" },
  "Done": { bg: "#BFD78D", color: "#0D0D0D" },
  "Not started": { bg: "#E9E4D8", color: "#0D0D0D" },
  "open": { bg: "#E9E4D8", color: "#0D0D0D" },
  "in_progress": { bg: "#C9D8FF", color: "#0D0D0D" },
  "blocked": { bg: "#F7C5E6", color: "#0D0D0D" },
  "done": { bg: "#BFD78D", color: "#0D0D0D" },
};

export function StatusPill({ status }: { status: string }) {
  const s = STATUS_MAP[status] || { bg: "#E9E4D8", color: "#0D0D0D" };
  return (
    <span style={{
      background: s.bg, color: s.color,
      fontSize: 11, fontWeight: 500,
      padding: "3px 10px", borderRadius: 8,
      fontFamily: "'IBM Plex Mono', monospace",
    }}>
      {status}
    </span>
  );
}

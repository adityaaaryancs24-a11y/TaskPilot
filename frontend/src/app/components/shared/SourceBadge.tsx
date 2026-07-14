const SOURCE_COLORS: Record<string, string> = {
  jira: "#C9D8FF", Jira: "#C9D8FF",
  github: "#DCC7F7", GitHub: "#DCC7F7",
  slack: "#F7C5E6", Slack: "#F7C5E6",
  outlook: "#C9D8FF", Outlook: "#C9D8FF",
  email: "#C9D8FF", Email: "#C9D8FF",
  servicenow: "#BFD78D", ServiceNow: "#BFD78D",
  "meeting transcripts": "#FAD6B3", "Meeting Transcripts": "#FAD6B3",
  defect: "#F7C5E6", Defect: "#F7C5E6",
  injected: "#F5D66E", Injected: "#F5D66E",
};

export function SourceBadge({ source }: { source: string }) {
  const bg = SOURCE_COLORS[source] || "#E9E4D8";
  return (
    <span style={{
      background: bg, color: "#0D0D0D",
      fontSize: 11, fontWeight: 500,
      padding: "3px 10px", borderRadius: 8,
      display: "inline-flex", alignItems: "center", gap: 4,
      fontFamily: "'IBM Plex Mono', monospace",
    }}>
      {source}
    </span>
  );
}

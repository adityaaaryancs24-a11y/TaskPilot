import { useState, useEffect } from "react";
import { Network, Check, AlertCircle, Loader2 } from "lucide-react";
import { getA2aStatus } from "../../api/taskpilot";

export function A2AStatus() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const fetch = async () => {
      try {
        const data = await getA2aStatus();
        if (mounted) setStatus(data);
      } catch {}
      if (mounted) setLoading(false);
    };
    fetch();
    const interval = setInterval(fetch, 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  if (loading) return <div className="flex items-center gap-2 px-3 py-1.5 text-xs text-[#7A7A7A]"><Loader2 className="w-3 h-3 animate-spin" /> A2A...</div>;

  const isConnected = status?.status === "connected";

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs ${isConnected || status?.status === "standalone" ? "border-[#BFD78D] bg-[#BFD78D]/10" : "border-[#F7C5E6] bg-[#F7C5E6]/10"}`}>
      <Network className={`w-3 h-3 ${isConnected ? "text-[#BFD78D]" : "text-[#7A7A7A]"}`} />
      <span className="font-medium">{isConnected ? `A2A (${status.agents_connected})` : status?.status === "standalone" ? "A2A Ready" : "A2A Offline"}</span>
      {isConnected && <Check className="w-3 h-3 text-[#BFD78D]" />}
    </div>
  );
}

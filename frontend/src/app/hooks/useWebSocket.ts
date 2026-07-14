import { useEffect, useCallback } from "react";
import { subscribeWs, WebSocketEvent } from "../api/taskpilot";

export function useWebSocket(
  onEvent: (event: WebSocketEvent) => void,
  deps: unknown[] = [],
) {
  const handler = useCallback(onEvent, deps);

  useEffect(() => {
    return subscribeWs(handler);
  }, [handler]);
}

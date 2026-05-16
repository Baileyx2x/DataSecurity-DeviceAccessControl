import { useEffect, useRef } from "react";

export function useWebSocket(url: string, onMessage: (data: any) => void) {
  const ws = useRef<WebSocket | null>(null);
  useEffect(() => {
    ws.current = new WebSocket(url);
    ws.current.onmessage = e => onMessage(JSON.parse(e.data));
    return () => ws.current?.close();
  }, [url]);
}

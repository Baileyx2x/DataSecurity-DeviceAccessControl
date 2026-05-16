import { useEffect, useState, useRef } from "react";
import { Alert, Space } from "antd";

interface Event {
  type: string;
  data: Record<string, any>;
  ts: number;
}

// 开发模式下经过 Vite proxy,生产模式直连后端
const WS_URL = import.meta.env.DEV
  ? `ws://${window.location.host}/ws/realtime`
  : ((import.meta.env.VITE_WS_BASE ?? `ws://${window.location.host}/ws`) + "/realtime");

const LABELS: Record<string, string> = {
  "device.online": "设备上线",
  "device.offline": "设备离线",
  "alert.new": "告警触发",
  "device.blocked": "设备阻断",
  "device.unblocked": "阻断解除",
};

const COLORS: Record<string, "success" | "warning" | "error" | "info"> = {
  "device.online": "success",
  "device.offline": "warning",
  "alert.new": "error",
  "device.blocked": "error",
  "device.unblocked": "info",
};

export default function RealtimeBanner() {
  const [events, setEvents] = useState<Event[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;
    ws.onmessage = (e) => {
      try {
        const parsed = JSON.parse(e.data);
        if (parsed.type) {
          setEvents((prev) =>
            [{ type: parsed.type, data: parsed.data, ts: Date.now() }, ...prev].slice(0, 5)
          );
        }
      } catch {}
    };
    ws.onclose = () => {
      // 3 秒后自动重连
      setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.CLOSED) {
          window.location.reload();
        }
      }, 3000);
    };
    return () => ws.close();
  }, []);

  if (events.length === 0) return null;

  return (
    <Space direction="vertical" style={{ width: "100%", marginBottom: 16 }}>
      {events.map((evt, i) => (
        <Alert
          key={`${evt.ts}-${i}`}
          type={COLORS[evt.type] ?? "info"}
          message={
            <span>
              <strong>{LABELS[evt.type] ?? evt.type}</strong>
              {" — "}
              {evt.data.ip && `IP: ${evt.data.ip}`}
              {evt.data.mac && `  MAC: ${evt.data.mac}`}
              {evt.data.msg && `  ${evt.data.msg}`}
              {evt.data.reason && `  (${evt.data.reason})`}
            </span>
          }
          closable
          showIcon
        />
      ))}
    </Space>
  );
}

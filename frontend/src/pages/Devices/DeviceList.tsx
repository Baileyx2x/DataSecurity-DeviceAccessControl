import { useEffect, useRef, useState } from "react";
import { Table, Tag, Button, Space, message } from "antd";
import { listDevices, setWhitelist, setBlacklist, blockDevice, unblockDevice, Device } from "../../api/devices";
import DeviceDetail from "./DeviceDetail";
import { CATEGORY_COLOR, STATUS_COLOR, RISK_COLORS, RISK_NAMES } from "../../constants";

const POLL_INTERVAL_MS = 15_000;

export default function DeviceList() {
  const [data, setData] = useState<Device[]>([]);
  const [detailId, setDetailId] = useState<number>(0);
  const wsRef = useRef<WebSocket | null>(null);

  const load = () => listDevices().then(r => setData(r.data));

  // 初始加载 + 定时轮询
  useEffect(() => {
    load();
    const timer = setInterval(load, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, []);

  // WebSocket 实时更新
  useEffect(() => {
    const wsUrl = import.meta.env.DEV
      ? `ws://${window.location.host}/ws/realtime`
      : ((import.meta.env.VITE_WS_BASE ?? `ws://${window.location.host}/ws`) + "/realtime");
    let closed = false;
    const connect = () => {
      if (closed) return;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onmessage = (e) => {
        try {
          const evt = JSON.parse(e.data);
          if (evt.type === "device.online" || evt.type === "device.offline") {
            load();
          }
        } catch {}
      };
      ws.onclose = () => { if (!closed) setTimeout(connect, 5000); };
    };
    connect();
    return () => { closed = true; wsRef.current?.close(); };
  }, []);

  const columns = [
    { title: "名称",     dataIndex: "name" },
    { title: "IP",       dataIndex: "ip" },
    { title: "MAC",      dataIndex: "mac" },
    { title: "厂商",     dataIndex: "vendor" },
    { title: "主机名",   dataIndex: "hostname", render: (v: string) => v || "-" },
    { title: "分类",     dataIndex: "category",
      render: (v: string) => <Tag color={CATEGORY_COLOR[v] ?? "default"}>{v}</Tag>},
    { title: "状态",     dataIndex: "status",
      render: (v: string) => <Tag color={STATUS_COLOR[v] ?? "default"}>{v}</Tag>},
    { title: "风险",     dataIndex: "risk_level",
      render: (l: number) => <Tag color={RISK_COLORS[l]}>{RISK_NAMES[l]}</Tag>},
    { title: "操作",
      render: (_: any, r: Device) => (
        <Space>
          <Button size="small" type="link" onClick={() => setDetailId(r.id)}>详情</Button>
          <Button size="small" onClick={() => setWhitelist(r.id).then(load)}>白名单</Button>
          <Button size="small" danger onClick={() => setBlacklist(r.id).then(load)}>黑名单</Button>
          {r.status !== "blocked" ? (
            <Button size="small" onClick={() => blockDevice(r.id).then(() => { message.success("已阻断"); load(); }).catch((e) => message.error("阻断失败: " + (e?.response?.data?.detail ?? e.message)))}>阻断</Button>
          ) : (
            <Button size="small" type="primary" onClick={() => unblockDevice(r.id).then(() => { message.success("已放行"); load(); }).catch((e) => message.error("放行失败: " + (e?.response?.data?.detail ?? e.message)))}>取消阻断</Button>
          )}
        </Space>
      ),
    },
  ];
  return (
    <>
      <DeviceDetail deviceId={detailId} open={detailId > 0} onClose={() => { setDetailId(0); load(); }} />
      <Table rowKey="id" columns={columns} dataSource={data} />
    </>
  );
}

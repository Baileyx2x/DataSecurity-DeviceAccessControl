import { useEffect, useState } from "react";
import { Drawer, Descriptions, Tabs, Table, Tag, Spin } from "antd";
import { getDevice, getDeviceHistory, getDeviceAlerts, getDeviceAudit, Device } from "../../api/devices";
import { RISK_COLORS, RISK_NAMES, CATEGORY_COLOR, STATUS_COLOR, formatTime } from "../../constants";

interface Props {
  deviceId: number;
  open: boolean;
  onClose: () => void;
}

export default function DeviceDetail({ deviceId, open, onClose }: Props) {
  const [dev, setDev] = useState<Device | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);

  useEffect(() => {
    if (!deviceId) return;
    Promise.all([
      getDevice(deviceId),
      getDeviceHistory(deviceId),
      getDeviceAlerts(deviceId),
      getDeviceAudit(deviceId),
    ]).then(([d, h, a, aud]) => {
      setDev(d.data);
      setHistory(h.data);
      setAlerts(a.data);
      setAudit(aud.data);
    });
  }, [deviceId, open]);

  if (!dev) return <Drawer open={open} onClose={onClose}><Spin /></Drawer>;

  const info = (
    <Descriptions column={2} size="small" bordered>
      <Descriptions.Item label="MAC">{dev.mac}</Descriptions.Item>
      <Descriptions.Item label="IP">{dev.ip}</Descriptions.Item>
      <Descriptions.Item label="厂商">{dev.vendor || "-"}</Descriptions.Item>
      <Descriptions.Item label="主机名">{dev.hostname || "-"}</Descriptions.Item>
      <Descriptions.Item label="OS 推测">{dev.os_guess || "-"}</Descriptions.Item>
      <Descriptions.Item label="分类">
        <Tag color={CATEGORY_COLOR[dev.category] ?? "default"}>{dev.category}</Tag>
      </Descriptions.Item>
      <Descriptions.Item label="状态">
        <Tag color={STATUS_COLOR[dev.status] ?? "default"}>{dev.status}</Tag>
      </Descriptions.Item>
      <Descriptions.Item label="风险等级">
        <Tag color={RISK_COLORS[dev.risk_level]}>{RISK_NAMES[dev.risk_level]}</Tag>
      </Descriptions.Item>
      <Descriptions.Item label="首次发现">{formatTime(dev.first_seen)}</Descriptions.Item>
      <Descriptions.Item label="最近在线">{formatTime(dev.last_seen)}</Descriptions.Item>
      <Descriptions.Item label="告警数">{dev.alert_count ?? 0}</Descriptions.Item>
      <Descriptions.Item label="接入记录">{dev.access_count ?? 0}</Descriptions.Item>
    </Descriptions>
  );

  const historyTable = (
    <Table rowKey="id" size="small" dataSource={history} columns={[
      { title: "时间", dataIndex: "timestamp", width: 180, render: (v: string) => formatTime(v) },
      { title: "事件", dataIndex: "event_type" },
      { title: "IP", dataIndex: "ip" },
    ]} pagination={{ pageSize: 10 }} />
  );

  const alertsTable = (
    <Table rowKey="id" size="small" dataSource={alerts} columns={[
      { title: "时间", dataIndex: "created_at", width: 180, render: (v: string) => formatTime(v) },
      { title: "等级", dataIndex: "level", render: (l: number) => <Tag color={RISK_COLORS[l]}>{RISK_NAMES[l]}</Tag>, width: 70 },
      { title: "信息", dataIndex: "message" },
      { title: "状态", dataIndex: "status", width: 80 },
    ]} pagination={{ pageSize: 10 }} />
  );

  const auditTable = (
    <Table rowKey="id" size="small" dataSource={audit} columns={[
      { title: "时间", dataIndex: "timestamp", width: 180, render: (v: string) => formatTime(v) },
      { title: "操作者", dataIndex: "actor", width: 80 },
      { title: "动作", dataIndex: "action" },
      { title: "原因", dataIndex: "reason" },
    ]} pagination={{ pageSize: 10 }} />
  );

  return (
    <Drawer
      title={`设备详情 — ${dev.ip} (${dev.mac})`}
      open={open} onClose={onClose} width={720}
    >
      <Tabs defaultActiveKey="info" items={[
        { key: "info", label: "基本信息", children: info },
        { key: "history", label: `接入历史 (${history.length})`, children: historyTable },
        { key: "alerts", label: `告警 (${alerts.length})`, children: alertsTable },
        { key: "audit", label: `操作记录 (${audit.length})`, children: auditTable },
      ]} />
    </Drawer>
  );
}

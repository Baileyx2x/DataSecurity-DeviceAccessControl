import { useEffect, useState } from "react";
import { Drawer, Descriptions, Tabs, Table, Tag, Spin, TimePicker, InputNumber, Button, message, Space, Card } from "antd";
import { getDevice, getDeviceHistory, getDeviceAlerts, getDeviceAudit, setSchedule, limitBandwidth, unlimitBandwidth, Device } from "../../api/devices";
import { RISK_COLORS, RISK_NAMES, CATEGORY_COLOR, STATUS_COLOR, formatTime } from "../../constants";
import dayjs from "dayjs";

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
  const [schStart, setSchStart] = useState<dayjs.Dayjs | null>(null);
  const [schEnd, setSchEnd] = useState<dayjs.Dayjs | null>(null);
  const [schLoading, setSchLoading] = useState(false);
  const [qosDown, setQosDown] = useState<number | null>(null);
  const [qosUp, setQosUp] = useState<number | null>(null);
  const [qosLoading, setQosLoading] = useState(false);

  const loadDetail = () => {
    if (!deviceId) return;
    Promise.all([
      getDevice(deviceId),
      getDeviceHistory(deviceId),
      getDeviceAlerts(deviceId),
      getDeviceAudit(deviceId),
    ]).then(([d, h, a, aud]) => {
      const device = d.data as Device;
      setDev(device);
      setHistory(h.data);
      setAlerts(a.data);
      setAudit(aud.data);
      setSchStart(device.block_schedule_start ? dayjs(device.block_schedule_start, "HH:mm") : null);
      setSchEnd(device.block_schedule_end ? dayjs(device.block_schedule_end, "HH:mm") : null);
      setQosDown(device.qos_down_kbps ? device.qos_down_kbps / 1000 : null);
      setQosUp(device.qos_up_kbps ? device.qos_up_kbps / 1000 : null);
    });
  };

  useEffect(() => { loadDetail(); }, [deviceId, open]);

  const saveSchedule = () => {
    setSchLoading(true);
    const payload = {
      block_schedule_start: schStart ? schStart.format("HH:mm") : "",
      block_schedule_end: schEnd ? schEnd.format("HH:mm") : "",
    };
    setSchedule(deviceId, payload)
      .then(() => { message.success("上网时段已保存"); loadDetail(); })
      .catch(() => message.error("保存失败"))
      .finally(() => setSchLoading(false));
  };

  const saveQos = () => {
    setQosLoading(true);
    limitBandwidth(deviceId, (qosDown ?? 0) * 1000, (qosUp ?? 0) * 1000)
      .then(() => { message.success("带宽限制已生效"); loadDetail(); })
      .catch(() => message.error("限速失败,确保 Linux 上有 root 权限且 tc 可用"))
      .finally(() => setQosLoading(false));
  };

  const clearQos = () => {
    setQosLoading(true);
    unlimitBandwidth(deviceId)
      .then(() => { setQosDown(null); setQosUp(null); message.success("已取消限速"); loadDetail(); })
      .catch(() => message.error("取消失败"))
      .finally(() => setQosLoading(false));
  };

  if (!dev) return <Drawer open={open} onClose={onClose}><Spin /></Drawer>;

  const info = (
    <>
      <Card size="small" title="基本信息" style={{ marginBottom: 12 }}>
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
      </Card>

      {dev.status === "blocked" && (
        <Card size="small" title="阻断信息" style={{ marginBottom: 12 }}>
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="阻断原因">{dev.blocked_by || "-"}</Descriptions.Item>
            <Descriptions.Item label="阻断到期">{dev.blocked_until ? formatTime(dev.blocked_until) : "手动解除"}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      <Card size="small" title="上网时段限制" style={{ marginBottom: 12 }}>
        <Space>
          <TimePicker value={schStart} onChange={setSchStart} format="HH:mm" placeholder="起始" size="small" style={{ width: 100 }} />
          <span>—</span>
          <TimePicker value={schEnd} onChange={setSchEnd} format="HH:mm" placeholder="结束" size="small" style={{ width: 100 }} />
          <Button type="primary" size="small" loading={schLoading} onClick={saveSchedule}>保存</Button>
          {(dev.block_schedule_start || dev.block_schedule_end) && (
            <Button size="small" danger loading={schLoading} onClick={() => {
              setSchStart(null); setSchEnd(null);
              setSchedule(deviceId, { block_schedule_start: "", block_schedule_end: "" })
                .then(() => { message.success("已清除上网限制"); loadDetail(); })
                .catch(() => message.error("清除失败"))
                .finally(() => setSchLoading(false));
            }}>清除</Button>
          )}
        </Space>
        {(dev.block_schedule_start || dev.block_schedule_end) && (
          <div style={{ marginTop: 8, color: "#888" }}>
            当前时段: {dev.block_schedule_start} — {dev.block_schedule_end}
          </div>
        )}
      </Card>

      <Card size="small" title={
        dev.qos_down_kbps || dev.qos_up_kbps
          ? `带宽限制 (已生效: 下${(dev.qos_down_kbps ?? 0) / 1000}M / 上${(dev.qos_up_kbps ?? 0) / 1000}M)`
          : "带宽限制"
      } style={{ marginBottom: 12 }}>
        <Space>
          <span>下载 (Mbps)</span>
          <InputNumber value={qosDown} onChange={setQosDown} min={0} max={1000} step={1}
            placeholder="不限" size="small" style={{ width: 80 }} />
          <span>上传 (Mbps)</span>
          <InputNumber value={qosUp} onChange={setQosUp} min={0} max={1000} step={1}
            placeholder="不限" size="small" style={{ width: 80 }} />
          <Button type="primary" size="small" loading={qosLoading}
            disabled={!qosDown && !qosUp} onClick={saveQos}>应用</Button>
          {(dev.qos_down_kbps || dev.qos_up_kbps) && (
            <Button size="small" danger loading={qosLoading} onClick={clearQos}>取消限速</Button>
          )}
        </Space>
      </Card>
    </>
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

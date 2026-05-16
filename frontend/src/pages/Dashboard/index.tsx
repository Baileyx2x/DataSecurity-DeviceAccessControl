import { useEffect, useState } from "react";
import { Card, Row, Col, Statistic } from "antd";
import { listDevices } from "../../api/devices";
import { listAlerts } from "../../api/alerts";
import { listAudit } from "../../api/audit";
import { usePolling } from "../../hooks/usePolling";

export default function Dashboard() {
  const [stats, setStats] = useState({ total: 0, online: 0, blocked: 0, alerts: 0, audit: 0 });

  const load = () => {
    Promise.all([
      listDevices(),
      listAlerts("open"),
      listAudit(),
    ]).then(([devices, alerts, audit]) => {
      const ds = devices.data;
      setStats({
        total: ds.length,
        online: ds.filter((d: any) => d.status === "online").length,
        blocked: ds.filter((d: any) => d.status === "blocked").length,
        alerts: alerts.data.length,
        audit: audit.data.length,
      });
    });
  };

  usePolling(load, 5000);

  return (
    <Row gutter={16}>
      <Col span={6}><Card><Statistic title="设备总数" value={stats.total} /></Card></Col>
      <Col span={6}><Card><Statistic title="在线设备" value={stats.online} valueStyle={{ color: "#3f8600" }} /></Card></Col>
      <Col span={6}><Card><Statistic title="未处理告警" value={stats.alerts} valueStyle={{ color: stats.alerts > 0 ? "#cf1322" : undefined }} /></Card></Col>
      <Col span={6}><Card><Statistic title="阻断中" value={stats.blocked} valueStyle={{ color: stats.blocked > 0 ? "#cf1322" : undefined }} /></Card></Col>
    </Row>
  );
}

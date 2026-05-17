import { useEffect, useState } from "react";
import { Card, Row, Col, Statistic, Spin } from "antd";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { listDevices } from "../../api/devices";
import { listAlerts } from "../../api/alerts";
import { getTimeline } from "../../api/stats";
import { usePolling } from "../../hooks/usePolling";

export default function Dashboard() {
  const [stats, setStats] = useState({ total: 0, online: 0, blocked: 0, alerts: 0 });
  const [timeline, setTimeline] = useState<any[]>([]);

  const load = () => {
    Promise.all([listDevices(), listAlerts("open"), getTimeline()]).then(
      ([devices, alerts, tl]) => {
        const ds = devices.data;
        setStats({
          total: ds.length,
          online: ds.filter((d: any) => d.status === "online").length,
          blocked: ds.filter((d: any) => d.status === "blocked").length,
          alerts: alerts.data.length,
        });
        setTimeline(tl.data);
      }
    );
  };

  usePolling(load, 5000);

  return (
    <>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}><Card><Statistic title="设备总数" value={stats.total} /></Card></Col>
        <Col span={6}><Card><Statistic title="在线设备" value={stats.online} valueStyle={{ color: "#3f8600" }} /></Card></Col>
        <Col span={6}><Card><Statistic title="未处理告警" value={stats.alerts} valueStyle={{ color: stats.alerts > 0 ? "#cf1322" : undefined }} /></Card></Col>
        <Col span={6}><Card><Statistic title="阻断中" value={stats.blocked} valueStyle={{ color: stats.blocked > 0 ? "#cf1322" : undefined }} /></Card></Col>
      </Row>

      <Card title="24h 趋势">
        {timeline.length === 0 ? (
          <Spin />
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={timeline}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" fontSize={12} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="online" name="设备上线" stroke="#3f8600" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="alerts" name="告警" stroke="#cf1322" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card>
    </>
  );
}

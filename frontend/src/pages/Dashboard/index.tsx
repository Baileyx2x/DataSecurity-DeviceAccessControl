import { useEffect, useState } from "react";
import { Card, Row, Col, Statistic } from "antd";
import { listDevices } from "../../api/devices";

export default function Dashboard() {
  const [total, setTotal] = useState(0);
  const [online, setOnline] = useState(0);
  useEffect(() => {
    listDevices().then(r => {
      setTotal(r.data.length);
      setOnline(r.data.filter(d => d.status === "online").length);
    });
  }, []);
  return (
    <Row gutter={16}>
      <Col span={6}><Card><Statistic title="设备总数" value={total} /></Card></Col>
      <Col span={6}><Card><Statistic title="在线设备" value={online} /></Card></Col>
      <Col span={6}><Card><Statistic title="未处理告警" value={"-"} /></Card></Col>
      <Col span={6}><Card><Statistic title="阻断中" value={"-"} /></Card></Col>
    </Row>
  );
}

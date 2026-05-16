import { useEffect, useState } from "react";
import { Table, Tag, Button } from "antd";
import { listAlerts, ackAlert } from "../../api/alerts";

export default function Alerts() {
  const [rows, setRows] = useState<any[]>([]);
  const load = () => listAlerts().then(r => setRows(r.data));
  useEffect(() => { load(); }, []);
  const cols = [
    { title: "时间", dataIndex: "created_at" },
    { title: "设备", dataIndex: "device_id" },
    { title: "等级", dataIndex: "level",
      render: (l: number) => <Tag color={["blue","gold","orange","red"][l]}>{["低","中","高","严重"][l]}</Tag>},
    { title: "信息", dataIndex: "message" },
    { title: "状态", dataIndex: "status" },
    { title: "操作", render: (_: any, r: any) =>
      <Button size="small" onClick={() => ackAlert(r.id).then(load)}>确认</Button>},
  ];
  return <Table rowKey="id" columns={cols} dataSource={rows} />;
}

import { useEffect, useState } from "react";
import { Table } from "antd";
import { listAudit } from "../../api/audit";
import { formatTime } from "../../constants";

export default function Audit() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => { listAudit().then(r => setRows(r.data)); }, []);
  return <Table rowKey="id" dataSource={rows} columns={[
    { title: "时间", dataIndex: "timestamp", render: (v: string) => formatTime(v) },
    { title: "操作者", dataIndex: "actor" },
    { title: "动作", dataIndex: "action" },
    { title: "目标设备", dataIndex: "target_device_id" },
    { title: "原因", dataIndex: "reason" },
  ]} />;
}

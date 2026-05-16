import { useEffect, useState } from "react";
import { Table } from "antd";
import { listRules } from "../../api/rules";

export default function Rules() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => { listRules().then(r => setRows(r.data)); }, []);
  return <Table rowKey="id" dataSource={rows} columns={[
    { title: "名称", dataIndex: "name" },
    { title: "动作", dataIndex: "action" },
    { title: "等级", dataIndex: "level" },
    { title: "启用", dataIndex: "enabled", render: (v: boolean) => v ? "✅" : "—" },
    { title: "说明", dataIndex: "description" },
  ]} />;
}

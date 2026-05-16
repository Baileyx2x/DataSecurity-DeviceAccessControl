import { useEffect, useState } from "react";
import { Table, Tag, Button, Space, message } from "antd";
import { listDevices, setWhitelist, setBlacklist, blockDevice, unblockDevice, Device } from "../../api/devices";
import DeviceDetail from "./DeviceDetail";

export default function DeviceList() {
  const [data, setData] = useState<Device[]>([]);
  const [detailId, setDetailId] = useState<number>(0);
  const load = () => listDevices().then(r => setData(r.data));
  useEffect(() => { load(); }, []);

  const columns = [
    { title: "IP",       dataIndex: "ip" },
    { title: "MAC",      dataIndex: "mac" },
    { title: "厂商",     dataIndex: "vendor" },
    { title: "主机名",   dataIndex: "hostname", render: (v: string) => v || "-" },
    { title: "分类",     dataIndex: "category",
      render: (v: string) => <Tag color={v==="white"?"green":v==="black"?"red":"default"}>{v}</Tag>},
    { title: "状态",     dataIndex: "status",
      render: (v: string) => <Tag color={v==="online"?"green":v==="blocked"?"red":"default"}>{v}</Tag>},
    { title: "风险",     dataIndex: "risk_level",
      render: (l: number) => <Tag color={["blue","gold","orange","red"][l]}>{["低","中","高","严重"][l]}</Tag>},
    { title: "操作",
      render: (_: any, r: Device) => (
        <Space>
          <Button size="small" type="link" onClick={() => setDetailId(r.id)}>详情</Button>
          <Button size="small" onClick={() => setWhitelist(r.id).then(load)}>白名单</Button>
          <Button size="small" danger onClick={() => setBlacklist(r.id).then(load)}>黑名单</Button>
          {r.status !== "blocked" ? (
            <Button size="small" onClick={() => blockDevice(r.id).then(() => { message.success("已阻断"); load(); })}>阻断</Button>
          ) : (
            <Button size="small" type="primary" onClick={() => unblockDevice(r.id).then(() => { message.success("已放行"); load(); })}>取消阻断</Button>
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

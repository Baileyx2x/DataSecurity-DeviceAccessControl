import { useEffect, useState } from "react";
import { Table, Button, Switch, Tag, Space, Modal, Form, Input, Select, InputNumber, message, Popconfirm } from "antd";
import { listRules, createRule, updateRule, deleteRule, toggleRule, Rule } from "../../api/rules";

const LEVEL_COLORS = ["blue", "gold", "orange", "red"];
const LEVEL_NAMES = ["低", "中", "高", "严重"];

export default function Rules() {
  const [rows, setRows] = useState<Rule[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Rule | null>(null);
  const [form] = Form.useForm();

  const load = () => listRules().then(r => setRows(r.data));
  useEffect(() => { load(); }, []);

  const save = (values: any) => {
    const payload = { ...values, enabled: values.enabled ?? true };
    const req = editing
      ? updateRule(editing.id, payload)
      : createRule(payload);
    req.then(() => { message.success(editing ? "已更新" : "已创建"); setOpen(false); load(); })
       .catch(e => message.error(e.response?.data?.detail ?? "保存失败"));
  };

  const openNew = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ action: "alert", level: 1, enabled: true });
    setOpen(true);
  };
  const openEdit = (r: Rule) => {
    setEditing(r);
    form.setFieldsValue(r);
    setOpen(true);
  };

  const cols = [
    { title: "名称", dataIndex: "name" },
    { title: "动作", dataIndex: "action",
      render: (v: string) => <Tag color={v === "block" ? "red" : "blue"}>{v === "block" ? "阻断" : "告警"}</Tag> },
    { title: "等级", dataIndex: "level",
      render: (l: number) => <Tag color={LEVEL_COLORS[l]}>{LEVEL_NAMES[l]}</Tag> },
    { title: "启用", dataIndex: "enabled",
      render: (v: boolean, r: Rule) => <Switch checked={v} onChange={() => toggleRule(r.id).then(load)} /> },
    { title: "说明", dataIndex: "description" },
    { title: "操作", render: (_: any, r: Rule) => (
      <Space>
        <Button size="small" onClick={() => openEdit(r)}>编辑</Button>
        <Popconfirm title="确认删除?" onConfirm={() => deleteRule(r.id).then(load)}>
          <Button size="small" danger>删除</Button>
        </Popconfirm>
      </Space>
    )},
  ];

  return (
    <>
      <Button type="primary" style={{ marginBottom: 16 }} onClick={openNew}>添加规则</Button>
      <Table rowKey="id" columns={cols} dataSource={rows} />
      <Modal
        title={editing ? "编辑规则" : "新建规则"}
        open={open} onCancel={() => setOpen(false)}
        onOk={() => form.submit()} destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={save}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="说明">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="condition_json" label="条件 JSON" rules={[{ required: true }]}>
            <Input.TextArea rows={4} placeholder='{"field":"category","op":"==","value":"black"}' />
          </Form.Item>
          <Space style={{ display: "flex" }} align="start">
            <Form.Item name="action" label="动作" rules={[{ required: true }]}>
              <Select options={[{ value: "alert", label: "告警" }, { value: "block", label: "阻断" }]} />
            </Form.Item>
            <Form.Item name="level" label="风险等级" rules={[{ required: true }]}>
              <InputNumber min={0} max={3} />
            </Form.Item>
            <Form.Item name="enabled" label="启用" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </>
  );
}

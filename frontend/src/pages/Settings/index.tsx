import { useEffect, useState } from "react";
import { Card, Form, Input, Select, Button, InputNumber, message, Switch } from "antd";
import { getSettings, updateSettings } from "../../api/settings";

const BACKENDS = [
  { value: "netsh", label: "netsh (Windows 防火墙,PC 做网关时推荐)" },
  { value: "route", label: "route (本机路由黑洞)" },
  { value: "arp", label: "arp (ARP 欺骗,Android/Windows 设备有效)" },
  { value: "deauth", label: "deauth (WiFi 踢下线,需网卡支持)" },
  { value: "iptables", label: "iptables (仅 Linux)" },
  { value: "none", label: "none (仅监控不阻断)" },
];

export default function Settings() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getSettings().then(r => form.setFieldsValue(r.data)).catch(() => {});
  }, [form]);

  const save = (values: any) => {
    setLoading(true);
    const payload: Record<string, string> = {
      BLOCKER_BACKEND: values.blocker_backend,
      BLOCKER_REQUIRE_CONFIRM: values.blocker_require_confirm ? "true" : "false",
      LAN_INTERFACE: values.lan_interface || "",
      LAN_CIDR: values.lan_cidr || "",
      SCAN_INTERVAL_SEC: String(values.scan_interval_sec),
      LOG_LEVEL: values.log_level,
    };
    updateSettings(payload)
      .then(() => message.success("配置已保存,部分修改需重启后端生效"))
      .catch(() => message.error("保存失败"))
      .finally(() => setLoading(false));
  };

  return (
    <Card title="系统设置" style={{ maxWidth: 600 }}>
      <Form form={form} layout="vertical" onFinish={save}>
        <Form.Item name="blocker_backend" label="阻断后端">
          <Select options={BACKENDS} />
        </Form.Item>
        <Form.Item name="blocker_require_confirm" label="阻断需二次确认" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item name="lan_cidr" label="扫描网段 (CIDR)">
          <Input placeholder="192.168.1.0/24,留空自动推断" />
        </Form.Item>
        <Form.Item name="lan_interface" label="监听网卡 (Windows 建议留空)">
          <Input placeholder="留空让 Scapy 自动选路" />
        </Form.Item>
        <Form.Item name="scan_interval_sec" label="扫描间隔 (秒)">
          <InputNumber min={10} max={3600} />
        </Form.Item>
        <Form.Item name="log_level" label="日志级别">
          <Select options={["DEBUG","INFO","WARNING","ERROR"].map(v => ({ value: v, label: v }))} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>保存配置</Button>
        </Form.Item>
      </Form>
    </Card>
  );
}

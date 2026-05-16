import { Layout, Menu } from "antd";
import { Link, useLocation } from "react-router-dom";
import { AppRouter } from "./router";

const { Header, Sider, Content } = Layout;

const items = [
  { key: "/",        label: <Link to="/">仪表盘</Link> },
  { key: "/devices", label: <Link to="/devices">设备管理</Link> },
  { key: "/alerts",  label: <Link to="/alerts">告警中心</Link> },
  { key: "/rules",   label: <Link to="/rules">规则配置</Link> },
  { key: "/audit",   label: <Link to="/audit">审计日志</Link> },
  { key: "/settings",label: <Link to="/settings">系统设置</Link> },
];

export default function App() {
  const loc = useLocation();
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider theme="light">
        <div style={{ height: 48, margin: 16, fontWeight: 700 }}>设备控制台</div>
        <Menu mode="inline" selectedKeys={[loc.pathname]} items={items} />
      </Sider>
      <Layout>
        <Header style={{ background: "#fff", paddingLeft: 24 }}>设备接入识别与阻断控制系统</Header>
        <Content style={{ padding: 24 }}>
          <AppRouter />
        </Content>
      </Layout>
    </Layout>
  );
}

# 设备接入识别与阻断控制系统

面向家庭 / 小型办公网络的轻量级设备接入识别与阻断控制系统。

## 技术栈

- **后端**: Python 3.10+ / FastAPI / Scapy / SQLAlchemy / SQLite / APScheduler
- **前端**: React 18 / TypeScript / Vite / Ant Design 5 / ECharts
- **存储**: SQLite (零配置,单文件)

## 核心功能

1. 设备发现 — ARP 扫描 + ICMP 探测,自动发现局域网设备
2. 设备登记 — 白名单 / 黑名单 / 未知三态管理
3. 状态采集 — IP / MAC / 主机名 / 上下线时间 / 访问摘要
4. 风险判定 — 可配置规则引擎,生成四级风险
5. 阻断控制 — ARP 欺骗 / iptables 双方案
6. 可视化界面 — 仪表盘 / 设备 / 告警 / 审计
7. 审计日志 — 所有操作可追溯

## 目录结构

```
backend/   后端服务 (FastAPI)
frontend/  前端 SPA (React)
docs/      设计文档与架构图
```

## 快速开始

### 后端

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
sudo -E uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> ARP 扫描 / 阻断需要 root 或 `CAP_NET_RAW` / `CAP_NET_ADMIN` 能力。

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 法律与合规

- 仅可在你拥有或获得书面授权的网络中使用本系统。
- ARP 阻断会影响目标设备的正常通信,启用前请评估副作用。

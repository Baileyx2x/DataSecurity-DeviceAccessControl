# REST API 规范

统一前缀 `/api/v1`,WebSocket 前缀 `/ws`。

## 设备
- `GET /devices?category=&status=`
- `GET /devices/{id}`
- `POST /devices/{id}/whitelist`
- `POST /devices/{id}/blacklist`

## 扫描
- `POST /scan/trigger`
- `GET /scan/status`

## 告警与规则
- `GET /alerts?status=`
- `POST /alerts/{id}/ack`
- `GET /rules`

## 阻断
- `POST /blocker/{device_id}/block`
- `POST /blocker/{device_id}/unblock`
- `GET /blocker/active`

## 审计
- `GET /audit?limit=`

## WebSocket
- `WS /ws/realtime` — 推送 device.online / device.offline / alert.new / device.blocked 事件

# 数据模型

完整字段定义见 `backend/app/models/`。核心实体为 5 张表:

| 表 | 用途 |
|---|---|
| device      | 设备资产 (mac/ip/category/risk_level/status) |
| access_log  | 接入历史 (online/offline/ip_change 事件) |
| alert       | 风险告警 (规则触发产生) |
| rule        | 风险判定规则 (condition_json + action) |
| audit_log   | 审计日志 (所有写操作落盘) |

ER 关系:device 1 - N access_log,device 1 - N alert,rule 1 - N alert,device 1 - N audit_log。

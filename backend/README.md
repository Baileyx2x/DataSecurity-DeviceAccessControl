# 后端 — FastAPI 服务

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
python scripts/seed_rules.py
sudo -E uvicorn app.main:app --reload --port 8000
```

## 关键命令

- 初始化数据库: `python scripts/init_db.py`
- 灌入默认规则: `python scripts/seed_rules.py`
- 导出审计: `python scripts/export_audit.py`
- 单元测试: `pytest`

## 权限说明

ARP 扫描与阻断需要 `CAP_NET_RAW` / `CAP_NET_ADMIN`,生产环境推荐:

```bash
sudo setcap cap_net_raw,cap_net_admin+eip $(which python3.10)
```

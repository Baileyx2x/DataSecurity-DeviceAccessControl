"""导出审计日志为 CSV。"""
import csv, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.models.base import SessionLocal
from app.models.audit_log import AuditLog

out = pathlib.Path("audit_export.csv")
db = SessionLocal()
with out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id","timestamp","actor","action","target_device_id","reason"])
    for r in db.query(AuditLog).all():
        w.writerow([r.id, r.timestamp, r.actor, r.action, r.target_device_id, r.reason])
print(f"✅ exported to {out.resolve()}")

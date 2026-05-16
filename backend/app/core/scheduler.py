"""任务调度器 — 周期性扫描 + 风险评估 + 离线检测。"""

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from ..config import settings
from ..models.base import SessionLocal
from ..models.device import Device
from ..utils.logger import logger
from . import discovery, fingerprint, registry, telemetry, risk_engine, blocker


_scheduler: BackgroundScheduler | None = None


def _scan_job():
    db: Session = SessionLocal()
    try:
        hosts = discovery.discover()  # ARP 优先,失败自动回退 Nmap
        for h in hosts:
            fp = fingerprint.fingerprint_device(h.ip, h.mac)
            dev = registry.upsert_device(
                db, mac=h.mac, ip=h.ip,
                vendor=fp.vendor, hostname=fp.hostname, os_guess=fp.os_guess,
            )
            telemetry.mark_online(db, dev.id, dev.ip)
        # 离线检测 + 风险评估
        telemetry.reap_offline(db)
        for dev in db.query(Device).filter(Device.status == "online").all():
            alerts = risk_engine.evaluate_device(db, dev)
            # 规则 action=block → 自动阻断
            for a in alerts:
                if a.rule and a.rule.action == "block" and dev.status != "blocked":
                    logger.info(
                        f"[scheduler] auto-block: device={dev.ip} "
                        f"rule={a.rule.name}"
                    )
                    db.refresh(dev)
                    blocker.block_device(
                        db, dev,
                        actor="system",
                        reason=f"auto: rule '{a.rule.name}' triggered",
                    )
    except Exception as e:
        logger.exception(f"[scheduler] scan job failed: {e}")
    finally:
        db.close()


def start_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(_scan_job, "interval", seconds=settings.scan_interval_sec, id="scan")
    _scheduler.start()
    logger.info(f"[scheduler] started (interval={settings.scan_interval_sec}s)")


def shutdown_scheduler():
    if _scheduler:
        _scheduler.shutdown(wait=False)

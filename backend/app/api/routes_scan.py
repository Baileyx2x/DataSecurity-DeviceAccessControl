"""扫描相关路由 — 手动触发 / 进度查询。"""
from fastapi import APIRouter, BackgroundTasks
from ..core.scheduler import _scan_job

router = APIRouter()

@router.post("/trigger")
def trigger_scan(bg: BackgroundTasks):
    bg.add_task(_scan_job)
    return {"status": "queued"}

@router.get("/status")
def scan_status():
    # TODO: 实际进度跟踪
    return {"running": False}

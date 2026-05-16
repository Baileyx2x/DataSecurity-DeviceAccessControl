"""FastAPI 应用入口。

启动顺序:
    1. 加载配置
    2. 初始化数据库 (确保表存在)
    3. 注册路由
    4. 启动后台调度器 (周期性 ARP 扫描 / 风险判定)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .models.base import init_db
from .core.scheduler import start_scheduler, shutdown_scheduler
from .api import (
    routes_devices,
    routes_scan,
    routes_risk,
    routes_blocker,
    routes_audit,
    routes_ws,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- 启动 ----
    init_db()
    start_scheduler()
    yield
    # ---- 关闭 ----
    shutdown_scheduler()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST 路由
app.include_router(routes_devices.router, prefix="/api/v1/devices", tags=["devices"])
app.include_router(routes_scan.router,    prefix="/api/v1/scan",    tags=["scan"])
app.include_router(routes_risk.router,    prefix="/api/v1",         tags=["risk"])
app.include_router(routes_blocker.router, prefix="/api/v1/blocker", tags=["blocker"])
app.include_router(routes_audit.router,   prefix="/api/v1/audit",   tags=["audit"])

# WebSocket
app.include_router(routes_ws.router, prefix="/ws", tags=["ws"])


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}

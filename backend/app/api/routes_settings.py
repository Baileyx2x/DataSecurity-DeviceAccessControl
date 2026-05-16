"""系统设置路由 — 查看 / 修改运行时 + .env 配置。"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from ..config import settings, Settings

router = APIRouter()

ENV_PATH = Path(__file__).resolve().parents[3] / ".env"


@router.get("")
def get_settings():
    return {
        "blocker_backend": settings.blocker_backend,
        "blocker_require_confirm": settings.blocker_require_confirm,
        "lan_interface": settings.lan_interface,
        "lan_cidr": settings.lan_cidr,
        "scan_interval_sec": settings.scan_interval_sec,
        "log_level": settings.log_level,
        "api_port": settings.api_port,
    }


@router.put("")
def update_settings(data: dict):
    """更新 .env 文件中的配置项。后端需重启生效。"""
    allowed = {
        "BLOCKER_BACKEND", "BLOCKER_REQUIRE_CONFIRM",
        "LAN_INTERFACE", "LAN_CIDR", "SCAN_INTERVAL_SEC", "LOG_LEVEL",
    }
    if not ENV_PATH.exists():
        raise HTTPException(500, ".env file not found. Create it from .env.example.")
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines(True)
    updated = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            upper = key.upper()
            if upper in data and upper in allowed:
                val = str(data[upper])
                line = f"{key}={val}\n"
                updated.add(upper)
        new_lines.append(line)
    # 追加新增字段
    for k, v in data.items():
        if k in allowed and k not in updated:
            new_lines.append(f"{k}={v}\n")
    ENV_PATH.write_text("".join(new_lines), encoding="utf-8")

    # 立即更新运行时 settings 的对应字段
    for key, val in data.items():
        if key == "BLOCKER_BACKEND":
            settings.blocker_backend = str(val)
        elif key == "BLOCKER_REQUIRE_CONFIRM":
            settings.blocker_require_confirm = str(val).lower() in ("true", "1", "yes")
        elif key == "LAN_INTERFACE":
            settings.lan_interface = str(val) if val else ""
        elif key == "LAN_CIDR":
            settings.lan_cidr = str(val) if val else ""
        elif key == "SCAN_INTERVAL_SEC":
            try:
                settings.scan_interval_sec = int(val)
            except ValueError:
                pass
        elif key == "LOG_LEVEL":
            settings.log_level = str(val)

    return {"ok": True, "note": "Config saved. Backend restart may be required for some changes."}

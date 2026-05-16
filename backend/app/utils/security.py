"""权限/能力检查 — ARP 扫描与阻断需要 root / 管理员权限。"""
import os
import sys


def require_net_admin() -> bool:
    """Linux: 需 root (euid==0);Windows: 需以管理员身份运行。"""
    if sys.platform == "win32":
        import ctypes
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    return hasattr(os, "geteuid") and os.geteuid() == 0

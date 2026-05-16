"""OUI 厂商查询 — 基于 manuf 库。"""
from functools import lru_cache

@lru_cache(maxsize=1)
def _parser():
    from manuf import manuf
    return manuf.MacParser()

def lookup_vendor(mac: str) -> str | None:
    try:
        return _parser().get_manuf_long(mac)
    except Exception:
        return None

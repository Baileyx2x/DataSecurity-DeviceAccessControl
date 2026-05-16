"""WebSocket 事件 schema。"""
def device_online(device): return {"type": "device.online", "data": {"id": device.id, "ip": device.ip, "mac": device.mac}}
def device_offline(device): return {"type": "device.offline", "data": {"id": device.id}}
def alert_created(alert): return {"type": "alert.new", "data": {"id": alert.id, "level": alert.level, "msg": alert.message}}
def device_blocked(device, reason): return {"type": "device.blocked", "data": {"id": device.id, "reason": reason}}

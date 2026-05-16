# 部署手册

## 方式一: 直接运行 (推荐用于开发与小型实验)

```bash
# 后端
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
python scripts/seed_rules.py
sudo -E uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端 (另开终端)
cd frontend
npm install
npm run dev
```

## 方式二: systemd 服务

`/etc/systemd/system/dac.service`:

```ini
[Unit]
Description=Device Access Control
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/dac/backend
ExecStart=/opt/dac/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
AmbientCapabilities=CAP_NET_RAW CAP_NET_ADMIN
Restart=always

[Install]
WantedBy=multi-user.target
```

## 方式三: Docker

参考根目录 `docker-compose.yml`。需要 `--network host --cap-add NET_RAW --cap-add NET_ADMIN`。

## 权限

无需 root 的最小授权:

```bash
sudo setcap cap_net_raw,cap_net_admin+eip $(which python3.10)
```

---

## 方式四: Windows 启动 (开发 / 实验)

### 0. 前置依赖


| 组件           | 说明                                         | 下载                                                                     |
| ------------ | ------------------------------------------ | ---------------------------------------------------------------------- |
| Python 3.10+ | 后端运行环境                                     | [https://www.python.org](https://www.python.org)                       |
| Node.js 18+  | 前端构建                                       | [https://nodejs.org](https://nodejs.org)                               |
| **Npcap**    | Scapy 在 Windows 收发原始包的前提 (ARP 扫描 / ARP 阻断) | [https://npcap.com](https://npcap.com)                                 |
| **Nmap**     | 无 Npcap 时的发现后备方案,自带 Npcap                  | [https://nmap.org/download#windows](https://nmap.org/download#windows) |


> 安装 Npcap 时**务必勾选** `Install Npcap in WinPcap API-compatible Mode`。
> 装了 Nmap 即附带 Npcap,二选一装一个即可,但都需要在安装向导里启用兼容模式。

### 1. 启动后端 (PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # 若提示脚本被禁用,先执行:
                                      # Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python scripts\init_db.py
python scripts\seed_rules.py
```

**必须以管理员身份打开 PowerShell** 再运行(ARP 扫描 / netsh 防火墙规则都需要管理员权限):

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. 启动前端 (另开一个终端,无需管理员)

```powershell
cd frontend
npm install
npm run dev
```

### 3. Windows 推荐配置 (`backend\.env`)

```ini
LAN_INTERFACE=                 # 留空,交给 Scapy/Nmap 自动选路
LAN_CIDR=192.168.1.0/24        # 也可留空自动推断;手填更稳
BLOCKER_BACKEND=arp            # Windows 上 arp 最可靠;netsh 仅按 IP 阻断
```

### 4. 验证

- `python -c "from scapy.all import conf; print(conf.ifaces)"` 能列出网卡 → Npcap 正常
- 访问 `http://localhost:8000/docs` 看 API 文档
- 手动触发一次扫描,日志出现 `[discovery] found N hosts` 即成功

---

## 关于 Nmap 的使用

### 它在本项目中的角色

`core/discovery.py` 提供三个函数:


| 函数            | 机制                 | 依赖      | 场景                |
| ------------- | ------------------ | ------- | ----------------- |
| `arp_scan()`  | Scapy ARP 广播       | Npcap   | 首选,最快最准,能拿到 MAC   |
| `nmap_scan()` | `nmap -sn -n` 主机发现 | 本机 Nmap | **没装 Npcap 时的后备** |
| `discover()`  | 先 ARP,空/异常则回退 Nmap | 二者其一    | 定时任务实际调用的统一入口     |


调度器已改为调用 `discover()`,所以你**不改代码**就能享受自动降级:
装了 Npcap 走 ARP;只装了 Nmap 也能正常发现设备。

### 单独验证 Nmap 是否可用

1. 确认命令行可用:`nmap --version`(装完后若提示找不到,把 Nmap 安装目录加进系统 PATH 后重开终端)
2. 手动扫一次本网段(**以管理员运行才能拿到 MAC**):
  ```powershell
   nmap -sn -n 192.168.1.0/24
  ```
   输出里每个 `Host is up` + `MAC Address: xx:xx:...` 就是一台设备。
3. 在项目里单独跑后备发现:
  ```powershell
   cd backend
   .\.venv\Scripts\Activate.ps1
   python -c "from app.core.discovery import nmap_scan; print(nmap_scan('192.168.1.0/24'))"
  ```

### 注意事项

- **MAC 地址只有在同一二层网段 + 管理员权限下才能拿到**;跨网段或非管理员运行时 `mac` 字段为空,指纹/OUI 识别会受影响。
- `nmap_scan` 比 `arp_scan` 慢(秒级 vs 毫秒级),且默认不扫端口(`-sn`),只做存活发现。
- 若想让 Nmap 顺带做 OS 识别,可把 `arguments` 改为 `-sn -n` 之外加 `-O`,但 `-O` 需要管理员且更慢,非必要不建议。
- python-nmap 只是对 `nmap.exe` 的封装,**不装 Nmap 本体它无法工作**——这点和 Scapy 依赖 Npcap 是同一类问题。


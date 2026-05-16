"""配置加载 — 基于 pydantic-settings,从环境变量或 .env 读取。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DeviceAccessControl"
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./data/app.db"

    lan_interface: str = ""           # 空 = 自动识别
    lan_cidr: str = ""                # 空 = 由网卡推断
    scan_interval_sec: int = 30

    blocker_backend: str = "route"     # deauth / arp / route / netsh(Windows) / iptables(Linux) / none
    blocker_require_confirm: bool = True

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_token: str = "change-me-please"


settings = Settings()

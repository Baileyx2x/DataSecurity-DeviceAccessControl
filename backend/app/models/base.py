"""SQLAlchemy 基础对象与会话工厂。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from ..config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_session() -> Session:
    """FastAPI 依赖注入用。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sqlite_migrate(eng, logger) -> None:
    """补齐 SQLite 旧表中缺失的列(ALTER TABLE 仅在列不存在时执行)。"""
    import sqlalchemy as sa
    migrations = {
        "device": [
            ("name",                "VARCHAR(128) DEFAULT 'Unknown'"),
            ("blocked_until", "DATETIME"),
            ("block_schedule_start", "VARCHAR(5)"),
            ("block_schedule_end",   "VARCHAR(5)"),
            ("blocked_by",           "VARCHAR(16)"),
            ("qos_down_kbps",       "INTEGER"),
            ("qos_up_kbps",         "INTEGER"),
        ],
        "device_traffic": [
            ("unique_dst_ips",   "INTEGER DEFAULT 0"),
            ("unique_dst_ports", "INTEGER DEFAULT 0"),
        ],
    }
    try:
        with eng.connect() as conn:
            for table, cols in migrations.items():
                try:
                    existing = [r[1] for r in conn.execute(
                        sa.text(f"PRAGMA table_info({table})")
                    ).fetchall()]
                except Exception:
                    continue  # 表不存在,跳过
                for col, typ in cols:
                    if col not in existing:
                        conn.execute(
                            sa.text(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
                        )
                        conn.commit()
                        logger.info(f"[db] added column {table}.{col}")
    except Exception:
        pass


def init_db() -> None:
    """启动时调用,确保所有表存在并补齐缺失列。"""
    from . import device, access_log, alert, rule, audit_log, traffic  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # SQLite 不自动加列,手动补齐
    from ..utils.logger import logger
    if engine.url.get_backend_name() == "sqlite":
        _sqlite_migrate(engine, logger)

"""初始化数据库 — 创建所有表。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.models.base import init_db

if __name__ == "__main__":
    init_db()
    print("✅ database initialized")

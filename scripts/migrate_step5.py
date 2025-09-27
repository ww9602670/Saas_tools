""""轻量迁移：创建 users 表（若不存在），不修改既有表。

用 SQLAlchemy 的 Base.metadata.create_all() 
只创建新增表，不会破坏现有数据。"""

# scripts/migrate_step5.py
# scripts/migrate_step5.py
"""
Step5 / Step1 迁移脚本：仅创建 users 表（若不存在）。
安全：不会修改已有表结构与数据。
"""

import os
import sys

# 确保脚本在控制台有输出；不影响主服务的日志设置
os.environ.setdefault("LOG_TO_FILE", "false")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

from app.infra.db import engine, Base  # noqa: E402
from app.infra.logger import emit  # noqa: E402
from app.core.models_user import User  # noqa: F401, E402  # 导入以注册到 Base


def run():
    emit("migrate_users_begin", database_url=os.getenv("DATABASE_URL"))
    print("[migrate_step5] creating tables if not exists ...", flush=True)
    Base.metadata.create_all(bind=engine)
    emit("migrate_users_done", status="ok")
    print("[migrate_step5] done.", flush=True)


if __name__ == "__main__":
    print(f"[migrate_step5] DATABASE_URL={os.getenv('DATABASE_URL')}", flush=True)
    try:
        run()
        sys.exit(0)
    except Exception as e:
        emit("migrate_users_error", error=str(e))
        print(f"[migrate_step5] ERROR: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
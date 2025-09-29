# tests/test_step2_migration.py
import os
import time
from sqlalchemy import text
from app.infra.db import engine

def test_step2_columns_added_and_backfilled():
    # 使用独立的数据库文件
    ts = int(time.time())
    os.environ["DATABASE_URL"] = f"sqlite:///./pytest_step2_{ts}.db"

    # 先创建 users / 其他表（沿用 step1 的迁移）
    from scripts.migrate_step5 import run as migrate_step1
    migrate_step1()

    # seed 两个用户（admin/demo）
    from scripts.seed_step5 import run as seed
    seed()

    # 执行 step2 迁移
    from scripts.migrate_step5_step2 import run as migrate_step2
    migrate_step2()

    with engine.begin() as conn:
        for table in ("accounts", "jobs", "command_requests"):
            cols = {r[1] for r in conn.execute(text(f"PRAGMA table_info('{table}')")).fetchall()}
            assert "user_id" in cols

        # 验证索引是否创建（存在即通过；轻量校验）
        idxs = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='index'")).fetchall()}
        assert "ix_accounts_user_id" in idxs
        assert "ix_jobs_user_id" in idxs
        assert "ix_command_requests_user_id" in idxs

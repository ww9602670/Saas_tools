# scripts/migrate_step5_step2.py
"""
Step5 / Step2 迁移脚本：
- 为 accounts / jobs / command_requests 新增 user_id 列（如不存在）；
- 建索引；
- 回填历史数据（优先 admin 用户；否则首个用户；否则留空）。

作用：为 accounts、jobs、command_requests 新增 user_id 列（TEXT），并建立索引；对历史数据做安全回填（优先回填为 admin 的 id；若无，则首个用户；找不到则留空）。

特点：幂等（多次执行不报错）。

"""


import os
import sys
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import text
from app.infra.db import engine
from app.infra.logger import emit

os.environ.setdefault("LOG_TO_FILE", "false")
os.environ.setdefault("PYTHONUNBUFFERED", "1")


@contextmanager
def begin():
    with engine.begin() as conn:
        yield conn


def _table_has_column(conn, table: str, column: str) -> bool:
    # SQLite pragma 检查；若未来换 PG/MySQL，可替换为信息模式查询
    rs = conn.execute(text(f"PRAGMA table_info('{table}')")).fetchall()
    cols = {r[1] for r in rs}  # (cid, name, type, notnull, dflt_value, pk)
    return column in cols


def _add_column_if_missing(conn, table: str, column: str, coltype: str = "TEXT"):
    if not _table_has_column(conn, table, column):
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))


def _create_index_if_missing(conn, index_name: str, table: str, column: str):
    rs = conn.execute(text("SELECT name FROM sqlite_master WHERE type='index'")).fetchall()
    idxs = {r[0] for r in rs}
    if index_name not in idxs:
        conn.execute(text(f"CREATE INDEX {index_name} ON {table}({column})"))


def _find_default_user_id(conn) -> Optional[str]:
    # 优先 admin，其次任何一名用户
    row = conn.execute(text("SELECT id FROM users WHERE role='admin' LIMIT 1")).fetchone()
    if row and row[0]:
        return row[0]
    row = conn.execute(text("SELECT id FROM users LIMIT 1")).fetchone()
    if row and row[0]:
        return row[0]
    return None


def _backfill_user_id(conn, table: str, default_user_id: Optional[str]):
    # 仅回填 NULL / 空字符串
    if default_user_id:
        conn.execute(
            text(
                f"UPDATE {table} SET user_id = :uid "
                f"WHERE (user_id IS NULL OR user_id = '')"
            ),
            {"uid": default_user_id},
        )


def run():
    emit("migrate_step2_begin", database_url=os.getenv("DATABASE_URL"))
    print("[migrate_step5_step2] begin ...", flush=True)
    with begin() as conn:
        # 1) 新增列
        for table in ("accounts", "jobs", "command_requests"):
            _add_column_if_missing(conn, table, "user_id", "TEXT")
            _create_index_if_missing(conn, f"ix_{table}_user_id", table, "user_id")

        # 2) 回填
        default_uid = _find_default_user_id(conn)
        for table in ("accounts", "jobs", "command_requests"):
            _backfill_user_id(conn, table, default_uid)

    emit("migrate_step2_done", status="ok")
    print("[migrate_step5_step2] done.", flush=True)


if __name__ == "__main__":
    try:
        run()
        sys.exit(0)
    except Exception as e:
        emit("migrate_step2_error", error=str(e))
        print(f"[migrate_step5_step2] ERROR: {e}", file=sys.stderr, flush=True)
        sys.exit(1)

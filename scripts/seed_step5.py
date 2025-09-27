""""根据 .env 或默认值创建两名用户：admin 与 demo（口令哈希）。

可作为脚本执行，也可被测试直接导入调用（提供 run() 函数）"""
# scripts/seed_step5.py
"""
Step5 - 种子脚本（Step1 部分）：创建 admin/demo 用户（如不存在）。
密码从 .env 读取或使用默认值，口令以 bcrypt 哈希存储。
"""
import os
import sys

# 确保脚本在控制台有输出；不影响主服务的日志设置
os.environ.setdefault("LOG_TO_FILE", "false")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

from sqlalchemy.orm import Session  # noqa: E402
from app.infra.db import SessionLocal  # noqa: E402
from app.infra.logger import emit  # noqa: E402
from app.core.models_user import User, UserRole  # noqa: E402
from app.core.security import hash_password  # noqa: E402


def _get_env(k: str, default: str) -> str:
    v = os.getenv(k)
    return v if v is not None and v != "" else default


def upsert_user(db: Session, username: str, password: str, role: UserRole):
    u = db.query(User).filter(User.username == username).first()
    if u:
        action = "updated"
        if u.role != role:
            u.role = role
        if password:
            u.password_hash = hash_password(password)
    else:
        action = "created"
        u = User(username=username, password_hash=hash_password(password), role=role, is_active=True)
        db.add(u)

    emit("seed_user_upsert", username=username, role=role.value, action=action)
    print(f"[seed_step5] {action} user: {username} ({role.value})", flush=True)


def run():
    emit("seed_begin", database_url=os.getenv("DATABASE_URL"))
    print("[seed_step5] seeding users ...", flush=True)

    admin_username = _get_env("ADMIN_USERNAME", "admin")
    admin_password = _get_env("ADMIN_PASSWORD", "admin")
    demo_username = _get_env("DEMO_USERNAME", "demo")
    demo_password = _get_env("DEMO_PASSWORD", "demo")

    with SessionLocal() as db:
        upsert_user(db, admin_username, admin_password, UserRole.admin)
        upsert_user(db, demo_username, demo_password, UserRole.user)
        db.commit()

    emit("seed_done", status="ok")
    print("[seed_step5] done.", flush=True)


if __name__ == "__main__":
    try:
        run()
        sys.exit(0)
    except Exception as e:
        emit("seed_error", error=str(e))
        print(f"[seed_step5] ERROR: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
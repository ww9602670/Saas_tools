# tests/test_step2_write_owner_commands.py
# 先设环境变量，再导入 app（关键！）
import os, time
ts = int(time.time())
os.environ["DATABASE_URL"] = f"sqlite:///./pytest_step2_cmd_{ts}.db"
os.environ["LOG_TO_FILE"]  = "false"
os.environ.setdefault("SECRET_KEY", "test-secret")

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.infra.db import engine
from scripts.migrate_step5 import run as migrate_users
from scripts.seed_step5 import run as seed_users
from scripts.migrate_step5_step2 import run as migrate_step2

client = TestClient(app)

def _get_user_id(username: str) -> str:
    with engine.begin() as conn:
        row = conn.execute(text("select id from users where username=:u"), {"u": username}).fetchone()
        assert row and row[0]
        return row[0]

def _create_account(token: str, name_suffix: str):
    # 给账户名加时间后缀，避免唯一键冲突
    acc_name = f"acc_cmd_{name_suffix}"
    body = {"site":"example","account_name":acc_name,"secrets":{"password":"p@ss"}}
    r = client.post("/api/accounts", headers={"Authorization": f"Bearer {token}"}, json=body)
    assert r.status_code == 200, r.text
    return acc_name, r.json()["id"]

def test_submit_command_writes_owner_and_job_pending():
    # 独立 schema & 数据
    migrate_users(); seed_users(); migrate_step2()

    # 登录
    r = client.post("/api/login", json={"username":"demo","password":"demo"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    demo_uid = _get_user_id("demo")

    # 先创建账户（唯一名）
    suffix = str(int(time.time()*1000))
    acc_name, _ = _create_account(token, suffix)

    # 提交 Step4 风格命令
    idem = f"idem-{suffix}"
    body = {
        "type":"example.fetch_profile",
        "payload":{"uid":"123"},
        "idempotency_key": idem,   # 入参字段
        "account_selector":{"site":"example","account_name": acc_name}
    }
    r = client.post("/api/commands", headers={"Authorization": f"Bearer {token}"}, json=body)
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]

    with engine.begin() as conn:
        # 注意：表字段名是 key（不是 idempotency_key）
        row = conn.execute(
            text("select user_id, job_id from command_requests where key=:k"),
            {"k": idem}
        ).fetchone()
        assert row and row[0] == demo_uid and row[1] == job_id

        # Job 预创建为 PENDING/RUNNING，且写入了 user_id
        row = conn.execute(
            text("select user_id, status from jobs where id=:id"),
            {"id": job_id}
        ).fetchone()
        assert row and row[0] == demo_uid and row[1] in ("PENDING","RUNNING")

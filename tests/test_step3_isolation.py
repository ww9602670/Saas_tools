# tests/test_step3_isolation.py
# -*- coding: utf-8 -*-
# 先设环境变量，再导入 app（确保 engine 绑定到独立测试库）
import os, time
ts = int(time.time())
os.environ["DATABASE_URL"] = f"sqlite:///./pytest_step3_iso_{ts}.db"
os.environ["LOG_TO_FILE"]  = "false"
os.environ.setdefault("SECRET_KEY", "test-secret")

from fastapi.testclient import TestClient
from sqlalchemy import text
from passlib.hash import bcrypt

from app.main import app
from app.infra.db import engine
from scripts.migrate_step5 import run as migrate_users
from scripts.seed_step5 import run as seed_users
from scripts.migrate_step5_step2 import run as migrate_step2

client = TestClient(app)

def _login(username: str, password: str) -> str:
    r = client.post("/api/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]

def _create_account(token: str, name: str):
    body = {"site":"example","account_name":name,"secrets":{"password":"p@ss"}}
    r = client.post("/api/accounts", headers={"Authorization": f"Bearer {token}"}, json=body)
    assert r.status_code == 200, r.text
    return r.json()["id"]

def _submit_command(token: str, acc_name: str) -> str:
    idem = f"idem-{int(time.time()*1000)}"
    body = {
        "type":"example.fetch_profile",
        "payload":{"uid":"123"},
        "idempotency_key": idem,
        "account_selector":{"site":"example","account_name": acc_name}
    }
    r = client.post("/api/commands", headers={"Authorization": f"Bearer {token}"}, json=body)
    assert r.status_code == 200, r.text
    return r.json()["job_id"]

def test_isolation_for_jobs_and_accounts():
    # 准备 schema & 基础用户
    migrate_users(); seed_users(); migrate_step2()

    # demo 登录并创建资源
    demo_token = _login("demo", "demo")
    acc_name = f"acc_demo_{int(time.time()*1000)}"
    _create_account(demo_token, acc_name)
    job_id = _submit_command(demo_token, acc_name)

    # demo 可访问自己的 job
    r = client.get(f"/api/jobs/{job_id}", headers={"Authorization": f"Bearer {demo_token}"})
    assert r.status_code == 200, r.text

    # admin 可访问 demo 的 job（管理员旁路）
    admin_token = _login("admin", "admin")
    r = client.get(f"/api/jobs/{job_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200, r.text

    # 新增普通用户 alice，并登录 —— 注意补上 created_at
    alice_pw = "alice"
    alice_hash = bcrypt.hash(alice_pw)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO users (id, username, password_hash, role, is_active, created_at)
            VALUES (:id, :un, :ph, 'user', 1, CURRENT_TIMESTAMP)
        """), {
            "id": f"alice-{int(time.time()*1000)}",
            "un": "alice",
            "ph": alice_hash
        })
    alice_token = _login("alice", alice_pw)

    # alice 访问 demo 的 job → 应当隔离（返回 404）
    r = client.get(f"/api/jobs/{job_id}", headers={"Authorization": f"Bearer {alice_token}"})
    assert r.status_code == 404, r.text

    # demo 看自己的 accounts 至少包含刚创建的那个
    r = client.get("/api/accounts", headers={"Authorization": f"Bearer {demo_token}"})
    assert r.status_code == 200
    assert any(it.get("account_name") == acc_name for it in r.json())

    # 注：若 /api/accounts 尚未实现 admin 旁路（admin 看全量），此处暂不强行断言
    # 若将来实现了，可补充：
    # r = client.get("/api/accounts", headers={"Authorization": f"Bearer {admin_token}"})
    # assert r.status_code == 200
    # assert any(it.get("account_name") == acc_name for it in r.json())

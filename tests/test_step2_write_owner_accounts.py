import os, time, json
from fastapi.testclient import TestClient
from sqlalchemy import text

import pytest

@pytest.fixture(scope="session", autouse=True)
def _env():
    ts = int(time.time())
    os.environ["DATABASE_URL"] = f"sqlite:///./pytest_step2_acc_{ts}.db"
    os.environ["LOG_TO_FILE"] = "false"
    os.environ.setdefault("SECRET_KEY", "test-secret")
    yield

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

def test_create_account_writes_user_id():
    # 准备 schema & 基础数据
    migrate_users(); seed_users(); migrate_step2()

    # 登录 demo 获取 token
    r = client.post("/api/login", json={"username":"demo","password":"demo"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    # 创建账户
    body = {"site":"example","account_name":"acc_step2","secrets":{"password":"p@ss"}}
    r = client.post("/api/accounts", headers={"Authorization": f"Bearer {token}"}, json=body)
    assert r.status_code == 200, r.text
    acc_id = r.json()["id"]

    # 校验库里该 account 的 user_id = demo 的 user_id
    demo_uid = _get_user_id("demo")
    with engine.begin() as conn:
        row = conn.execute(text("select user_id from accounts where id=:id"), {"id": acc_id}).fetchone()
        assert row and row[0] == demo_uid

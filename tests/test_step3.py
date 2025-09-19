# tests/test_step3.py
import os, time, pytest
# 测试环境变量要在导入 app 之前设置
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["LOG_TO_FILE"] = "false"   # 测试别落盘，减少噪音
os.environ["LOG_LEVEL"] = "WARNING"

from fastapi.testclient import TestClient
from app.main import app
from app.infra.db import init_db

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        init_db()  # 保险：若某些环境没触发 lifespan，也能建表
        yield c

def login(client: TestClient) -> str:
    r = client.post("/api/login", json={"username": "demo", "password": "demo"})
    assert r.status_code == 200
    return r.json()["access_token"]

def test_login_and_me(client: TestClient):
    token = login(client)
    r = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["user_id"] == "demo"

def test_command_idempotency_and_job_flow(client: TestClient):
    token = login(client)
    body = {"type": "IMPORT_CUSTOMERS", "payload": {"file_url": "x"}, "idempotency_key": "pytest-1"}

    r1 = client.post("/api/commands", headers={"Authorization": f"Bearer {token}"}, json=body)
    assert r1.status_code == 200
    job_id = r1.json()["job_id"]

    # 同 key 再提交 → 命中幂等
    r2 = client.post("/api/commands", headers={"Authorization": f"Bearer {token}"}, json=body)
    assert r2.status_code == 200
    assert r2.json()["job_id"] == job_id

    # 轮询直到成功
    for _ in range(20):
        r = client.get(f"/api/jobs/{job_id}", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        if r.json()["status"] == "SUCCEEDED":
            break
        time.sleep(0.1)
    assert r.json()["status"] == "SUCCEEDED"

def test_unknown_command_type(client: TestClient):
    token = login(client)
    r = client.post("/api/commands", headers={"Authorization": f"Bearer {token}"},
                    json={"type": "FOO", "payload": {}, "idempotency_key": "k"})
    assert r.status_code == 400

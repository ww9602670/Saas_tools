import os, time, pytest
os.environ.setdefault("DATABASE_URL","sqlite:///./test.db")
os.environ.setdefault("LOG_TO_FILE","false")
os.environ.setdefault("SECRET_KEY","dev-secret")
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c: yield c

def login(c):
    r = c.post("/api/login", json={"username":"demo","password":"demo"})
    assert r.status_code == 200
    return r.json()["access_token"]

def test_e2e_submit_and_poll(client):
    token = login(client)
    # 创建站点账号
    r = client.post("/api/accounts", headers={"Authorization": f"Bearer {token}"},
                    json={"site":"example","account_name":"acc1","secrets":{"password":"p@ss"}})
    assert r.status_code == 200
    # 提交命令（会入队）
    r = client.post("/api/commands", headers={"Authorization": f"Bearer {token}"},
                    json={"type":"example.fetch_profile","payload":{"uid":"123"},
                          "idempotency_key":"pytest-idem-1",
                          "account_selector":{"site":"example","account_name":"acc1"}})
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    # 若未启动 worker，这里可能一直 PENDING/RUNNING；我们不强制 SUCCEEDED
    rr = client.get(f"/api/jobs/{job_id}", headers={"Authorization": f"Bearer {token}"})
    assert rr.status_code == 200

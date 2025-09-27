""""使用临时 SQLite；

调用迁移与 seed（作为模块函数导入）；

用 TestClient 调 /api/login，验证成功/失败；

解码 JWT 负载（只检查结构，不改变接口）。"""
# tests/test_step1_auth_users.py
import os
import time
import jwt
import pytest
from fastapi.testclient import TestClient

# 统一设置测试专用环境
@pytest.fixture(scope="session", autouse=True)
def _setup_env():
    ts = int(time.time())
    os.environ["DATABASE_URL"] = f"sqlite:///./pytest_step1_{ts}.db"
    os.environ["LOG_TO_FILE"] = "false"
    os.environ.setdefault("SECRET_KEY", "test-secret")  # 测试秘钥
    yield


from app.main import app  # noqa: E402
from scripts.migrate_step5 import run as migrate_run  # noqa: E402
from scripts.seed_step5 import run as seed_run  # noqa: E402

client = TestClient(app)


def test_login_success_and_role_in_jwt():
    # 迁移 + 种子
    migrate_run()
    seed_run()

    # 成功登录 demo
    r = client.post("/api/login", json={"username": "demo", "password": "demo"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    assert token

    payload = jwt.decode(token, os.environ["SECRET_KEY"], algorithms=["HS256"])
    assert payload.get("username") == "demo"
    assert payload.get("role") == "user"
    assert "sub" in payload  # user_id 存在


def test_login_failed_wrong_password():
    r = client.post("/api/login", json={"username": "demo", "password": "bad"})
    assert r.status_code == 401


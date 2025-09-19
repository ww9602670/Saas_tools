# app/api/auth.py
"""
颁发 JWT（HS256）

日志事件：

auth_login_attempt（收到请求）

auth_login_failed（失败）

auth_login_success（成功）"""

import time, os, jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.infra.logger import emit

router = APIRouter()
ALGO = "HS256"
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")

class LoginIn(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(inp: LoginIn):
    # 调试日志：收到登录尝试
    emit("auth_login_attempt", username=inp.username)

    # 最小可用：固定账号密码（生产请改成 DB + 密码哈希校验）
    if not (inp.username == "demo" and inp.password == "demo"):
        emit("auth_login_failed", username=inp.username)
        raise HTTPException(401, "Invalid credentials")

    now = int(time.time())
    token = jwt.encode(
        {"sub": inp.username, "role": "admin", "iat": now, "exp": now + 3600},
        JWT_SECRET,
        algorithm=ALGO,
    )
    emit("auth_login_success", username=inp.username)
    return {"access_token": token, "token_type": "bearer"}

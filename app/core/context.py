# app/core/context.py
"""
统一提供请求上下文（user_id、username、role）。
- 兼容秘钥：优先 SECRET_KEY，其次 JWT_SECRET（为老环境兜底）
- 兼容头部：标准 Bearer / 裸 JWT
- 兼容负载：sub / user_id / username
- 事件打点：auth_missing_header / auth_token_invalid / auth_token_expired / auth_token_missing_sub
"""
from __future__ import annotations

import os
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.infra.logger import emit

ALGO = "HS256"
_bearer = HTTPBearer(auto_error=False)


def _get_secret() -> str:
    # 与登录签发保持一致（SECRET_KEY）；老环境兼容 JWT_SECRET
    return os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or "dev-secret"


class Context(BaseModel):
    user_id: str
    role: str = "user"
    username: Optional[str] = None  # ★ 新增：携带用户名，便于 /api/me 返回

    def serialize(self) -> dict:
        # 兼容原有代码（包含 username）
        return self.model_dump()

    @classmethod
    def from_payload(cls, data: dict) -> "Context":
        # 支持多种字段命名
        uid = data.get("sub") or data.get("user_id") or data.get("username") or ""
        role = data.get("role") or "user"
        uname = data.get("username")
        return cls(user_id=str(uid), role=str(role), username=uname)


def _extract_token(request: Request, creds: Optional[HTTPAuthorizationCredentials]) -> str:
    if creds and creds.credentials:
        return creds.credentials
    # 兼容：Authorization: <JWT>
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.count(".") == 2 and " " not in auth.strip():
        return auth.strip()
    emit("auth_missing_header")
    raise HTTPException(status_code=401, detail="Missing Authorization header")


def get_context(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    token = _extract_token(request, creds)
    try:
        payload = jwt.decode(
            token,
            _get_secret(),
            algorithms=[ALGO],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        emit("auth_token_expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError as e:
        emit("auth_token_invalid", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid token")

    ctx = Context.from_payload(payload)
    if not ctx.user_id:
        emit("auth_token_missing_sub")
        raise HTTPException(status_code=401, detail="Invalid token")
    return ctx

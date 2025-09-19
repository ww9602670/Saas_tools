# app/core/context.py
#统一提供请求上下文（user_id、role）。

#错误日志：auth_missing_header、auth_token_invalid。

import os, jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from app.infra.logger import emit

ALGO = "HS256"
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
bearer = HTTPBearer(auto_error=False)

class Context(BaseModel):
    user_id: str
    role: str
    def serialize(self) -> dict:
        return self.model_dump()
    @classmethod
    def from_payload(cls, data: dict) -> "Context":
        return cls(**data)

def get_context(credentials = Depends(bearer)) -> Context:
    """解析 Authorization: Bearer <JWT>，失败直接 401"""
    if not credentials:
        emit("auth_missing_header")
        raise HTTPException(401, "Missing Authorization header")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGO])
        return Context(user_id=payload.get("sub"), role=payload.get("role", "viewer"))
    except jwt.PyJWTError as e:
        # 调试日志：token 解析失败
        emit("auth_token_invalid", error=str(e))
        raise HTTPException(401, "Invalid token")
# app/core/context.py
import os, jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from app.infra.logger import emit

ALGO = "HS256"
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
bearer = HTTPBearer(auto_error=False)

class Context(BaseModel):
    user_id: str
    role: str
    def serialize(self) -> dict:
        return self.model_dump()
    @classmethod
    def from_payload(cls, data: dict) -> "Context":
        return cls(**data)

def get_context(credentials = Depends(bearer)) -> Context:
    """解析 Authorization: Bearer <JWT>，失败直接 401"""
    if not credentials:
        emit("auth_missing_header")
        raise HTTPException(401, "Missing Authorization header")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGO])
        return Context(user_id=payload.get("sub"), role=payload.get("role", "viewer"))
    except jwt.PyJWTError as e:
        # 调试日志：token 解析失败
        emit("auth_token_invalid", error=str(e))
        raise HTTPException(401, "Invalid token")

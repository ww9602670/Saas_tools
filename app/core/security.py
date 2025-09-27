# app/core/security.py
""""封装口令哈希/校验（passlib[bcrypt]）与 JWT 生成。

create_access_token() 会把 sub/username/role/exp 写入 JWT 负载；
响应 JSON 不变（仍只返回 access_token 字段）。"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any

import jwt  # PyJWT
from passlib.context import CryptContext

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_secret_key() -> str:
    key = os.getenv("SECRET_KEY")
    if not key:
        raise RuntimeError("SECRET_KEY is not set in environment")
    return key


def get_access_token_expire_minutes() -> int:
    try:
        return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    except Exception:
        return 60


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(payload: Dict[str, Any]) -> str:
    expire = datetime.utcnow() + timedelta(minutes=get_access_token_expire_minutes())
    to_encode = dict(payload)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)
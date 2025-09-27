# app/core/models_user.py
""""定义 UserRole（admin|ops|user）与 User ORM 实体：
id/username/password_hash/role/is_active/created_at。

只声明数据结构，不改变现有接口行为。"""
from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, String, Index
from app.infra.db import Base


class UserRole(str, Enum):
    admin = "admin"
    ops = "ops"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.user)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# 便于查询与唯一性保障
Index("ix_users_username_unique", User.username, unique=True)

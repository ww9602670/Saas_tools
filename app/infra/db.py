# app/infra/db.py
""""模块职能：

读取 DATABASE_URL，创建 SQLAlchemy 引擎

暴露 SessionLocal、get_db()（FastAPI 依赖）

init_db()：启动时统一建表

主要函数：

init_db()：根据 Base.metadata 建表

get_db()：每请求/每任务创建并释放一个 Session"""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖函数：yield 一个 Session，用后自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# app/api/jobs.py
# -*- coding: utf-8 -*-
"""
Job 查询 API（读侧资源隔离版）
------------------------------------------------
职能：
- 提供 GET /api/jobs/{job_id} 查询任务状态与错误信息
- 非 admin 仅可查询自己名下（user_id）的 Job；admin 可查询全部

引用库：
- FastAPI: 定义路由与依赖注入
- SQLAlchemy: 使用 Session + text 执行 SQL
- 自有模块:
    - app.core.context.get_context: 从 Bearer Token 解析当前请求用户（user_id / role / username）
    - app.infra.db.get_db: 提供数据库会话（与全局 engine 绑定）
    - app.infra.logger.emit: 结构化日志，打印到控制台或 logs/app.log（取决于 LOG_TO_FILE）

运行逻辑：
1) 从 ctx（上下文）获取 user_id 与 role
2) 读取 jobs 表中的记录（id, type, status, error, user_id）
3) 若记录不存在 → 404（隐藏不存在）
4) 若非 admin 且 row.user_id != ctx.user_id → 404（隐藏存在性，避免越权探测）
5) 返回与历史版本一致的 JSON：{"job_id","type","status","error"}

与其他脚本的关系：
- Step2 已在写入路径（/api/commands 预创建 Job）将 user_id 落库到 jobs.user_id
- workers/dispatcher.py 执行时沿用透传的 user_id（不受本文件影响）
- 本文件仅加强“读侧”的校验与可观测性（结构化日志）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.context import get_context, Context
from app.infra.db import get_db
from app.infra.logger import emit

router = APIRouter()

@router.get("/jobs/{job_id}", summary="Get Job", tags=["jobs"])
def get_job(job_id: str, ctx: Context = Depends(get_context), db: Session = Depends(get_db)):
    """
    获取单个 Job 的状态（读侧隔离）：
    - admin：可查看任意 Job
    - 非 admin：仅可查看自己名下 Job（row.user_id == ctx.user_id）
    返回体保持与既有版本一致：
        {
          "job_id": "<uuid>",
          "type": "<example.fetch_profile>",
          "status": "PENDING|RUNNING|SUCCEEDED|FAILED",
          "error": ""   # 无错时为空串
        }
    """
    emit("job_fetch_attempt", job_id=job_id, actor=ctx.user_id, role=ctx.role)

    # 用 Core API 读取，避免耦合到 ORM 模型；COALESCE 将 None 转为空串，减少返回处理分支
    row = db.execute(
        text("""
            SELECT
                id,
                type,
                status,
                COALESCE(error, '') AS error,
                user_id
            FROM jobs
            WHERE id = :id
        """),
        {"id": job_id},
    ).mappings().first()

    if not row:
        emit("job_fetch_not_found", job_id=job_id)
        raise HTTPException(status_code=404, detail="Job not found")

    # 非 admin 禁止越权读取（以 404 隐藏存在性）
    if ctx.role != "admin" and row["user_id"] != ctx.user_id:
        emit("job_fetch_forbidden", job_id=job_id, actor=ctx.user_id, owner=row["user_id"])
        raise HTTPException(status_code=404, detail="Job not found")

    emit("job_fetch_ok", job_id=job_id, owner=row["user_id"], status=row["status"])
    return {
        "job_id": row["id"],
        "type": row["type"],
        "status": row["status"],
        "error": row["error"] or "",
    }

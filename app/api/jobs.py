""""模块职能：

查询任务状态（仅允许查询自己的任务）

主要函数：

get_job(job_id, db, ctx)：校验归属 → 返回 type/status/error"""

# app/api/jobs.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.infra.db import get_db
from app.core.models import Job
from app.core.context import get_context, Context

router = APIRouter()

@router.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db), ctx: Context = Depends(get_context)):
    job = db.get(Job, job_id)
    if not job or job.user_id != ctx.user_id:
        raise HTTPException(404, "Job not found")
    return {
        "job_id": job.id,
        "type": job.type,
        "status": job.status,
        "error": job.error or "",
    }

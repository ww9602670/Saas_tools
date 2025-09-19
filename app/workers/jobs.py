""""模块职能：

示例后台任务 import_customers：模拟 3 步处理，按状态机推进并记录调试日志

主要函数：

import_customers(ctx_payload, payload, job_id)：

解析上下文 user_id

Job.start 置 RUNNING

依次输出 job_step：download_csv/parse_csv/upsert_db

Job.finish 标记 SUCCEEDED/FAILED"""
# app/workers/jobs.py
import time
from app.core.context import Context
from app.infra.db import SessionLocal
from app.core.models import Job
from app.core.state_machine import JobStatus
from app.infra.logger import emit

def import_customers(ctx_payload: dict, payload: dict, job_id: str):
    """
    示例任务：
    - 读上下文获得 user_id
    - 置 RUNNING
    - 模拟 3 步：download_csv / parse_csv / upsert_db
    - SUCCEEDED 或 FAILED
    """
    ctx = Context.from_payload(ctx_payload)
    db = SessionLocal()
    try:
        emit("job_start", job_id=job_id, type="IMPORT_CUSTOMERS", user_id=ctx.user_id)
        Job.start(db, job_id)
        for step in ("download_csv", "parse_csv", "upsert_db"):
            emit("job_step", job_id=job_id, step=step, user_id=ctx.user_id)
            time.sleep(0.2)
        Job.finish(db, job_id, JobStatus.SUCCEEDED)
        emit("job_finished", job_id=job_id, status="SUCCEEDED", user_id=ctx.user_id)
    except Exception as e:
        Job.finish(db, job_id, JobStatus.FAILED, str(e))
        emit("job_finished", job_id=job_id, status="FAILED", error=str(e), user_id=ctx.user_id)
        raise
    finally:
        db.close()

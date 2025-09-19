""""模块职能：

接收指令请求，按 idempotency_key 做幂等，生成 job_id，后台执行，并返回 PENDING

主要函数：

submit_command(inp, background, db, ctx)：

ensure_request → 幂等 MISS/HIT

仅支持 IMPORT_CUSTOMERS（示例）

Job.create_pending 预创建任务

link_job_id 绑定幂等请求与 job_id

background.add_task 后台线程执行"""
# app/api/commands.py
import uuid
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.context import get_context, Context
from app.infra.db import get_db
from app.core.models import Job
from app.services.idempotency import ensure_request, link_job_id
from app.workers.jobs import import_customers
from app.infra.logger import emit

router = APIRouter()

class CommandIn(BaseModel):
    type: str                  # 例：IMPORT_CUSTOMERS
    payload: dict = {}
    idempotency_key: str

@router.post("/commands")
def submit_command(
    inp: CommandIn,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    ctx: Context = Depends(get_context),
):
    emit("cmd_submit", user_id=ctx.user_id, type=inp.type, key=inp.idempotency_key)

    existed = ensure_request(db, ctx.user_id, inp.idempotency_key, inp.type, inp.payload)
    if existed and existed.get("job_id"):
        emit("idem_hit", user_id=ctx.user_id, key=inp.idempotency_key, job_id=existed["job_id"])
        return existed

    if existed and not existed.get("job_id"):
        emit("idem_miss", user_id=ctx.user_id, key=inp.idempotency_key)

    # 目前只支持一个示例指令
    if inp.type != "IMPORT_CUSTOMERS":
        emit("cmd_unknown_type", user_id=ctx.user_id, type=inp.type)
        raise HTTPException(400, "Unknown command type")

    job_id = str(uuid.uuid4())
    Job.create_pending(db, job_id=job_id, user_id=ctx.user_id, job_type=inp.type)
    link_job_id(db, ctx.user_id, inp.idempotency_key, job_id)
    emit("job_created_pending", user_id=ctx.user_id, job_id=job_id, type=inp.type)

    # 后台线程执行示例任务
    background.add_task(import_customers, ctx.serialize(), inp.payload, job_id)

    return {"job_id": job_id, "status": "PENDING"}

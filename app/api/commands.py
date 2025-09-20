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
from typing import Optional, Dict
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.context import get_context, Context
from app.infra.db import get_db
from app.core.models import Job
from app.services.idempotency import ensure_request, link_job_id
from app.workers.jobs import import_customers
from app.infra.logger import emit
from app.workers.queue import enqueue

router = APIRouter()

class CommandIn(BaseModel):
    # Step4： "example.fetch_profile"；Step3： "IMPORT_CUSTOMERS"
    type: str                 
    payload: Dict = Field(default_factory=dict)
    idempotency_key: str

    # Step4 使用；为了兼容 Step3，设为可选
    account_selector: Optional[Dict] = None  # 例：{"site":"example","account_name":"acc1"}

@router.post("/commands")
def submit_command(
    inp: CommandIn,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    ctx: Context = Depends(get_context),
):
    emit("cmd_submit", user_id=ctx.user_id, type=inp.type, key=inp.idempotency_key)

    # 幂等：第一次创建记录；后续命中直接返回旧 job
    existed = ensure_request(db, ctx.user_id, inp.idempotency_key, inp.type, inp.payload)
    if not existed:
        emit("idem_none_unexpected", user_id=ctx.user_id, key=inp.idempotency_key, type=inp.type)
        raise HTTPException(500, "idempotency_record_create_failed")

    if existed.job_id:
        emit("idem_hit", user_id=ctx.user_id, key=inp.idempotency_key, job_id=existed.job_id)
        return {"job_id": existed.job_id, "status": "PENDING"}

    emit("idem_miss", user_id=ctx.user_id, key=inp.idempotency_key)

    # 统一创建 Job（PENDING），并把 job_id 绑定到幂等记录
    job_id = str(uuid.uuid4())
    Job.create_pending(db, job_id=job_id, user_id=ctx.user_id, job_type=inp.type)
    link_job_id(db, ctx.user_id, inp.idempotency_key, job_id)
    emit("job_created_pending", user_id=ctx.user_id, job_id=job_id, type=inp.type)

    # —— 分流执行 —— #
    if "." in inp.type:
        # Step4：队列化（需要 account_selector）
        if not inp.account_selector:
            raise HTTPException(400, "account_selector is required for Step4 commands (site.action)")
        # 入队：dispatcher 在 Worker 里解析 site/action，拉账号、登录/复用会话、执行连接器动作
        enqueue(job_id=job_id, user_id=ctx.user_id, type=inp.type,
                account_selector=inp.account_selector, payload=inp.payload)
    elif inp.type == "IMPORT_CUSTOMERS":
        # Step3：保留老逻辑，方便兼容旧测试/脚本
        background.add_task(import_customers, ctx.serialize(), inp.payload, job_id)
    else:
        # 不认识的老式类型
        emit("cmd_unknown_type", user_id=ctx.user_id, type=inp.type)
        raise HTTPException(400, "Unknown command type")

    return {"job_id": job_id, "status": "PENDING"}

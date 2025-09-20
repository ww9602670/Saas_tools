""""模块职能：

幂等请求插入与回查，保证同一用户+同一 idempotency_key 只产生一个 Job

主要函数：

ensure_request(db, user_id, key, cmd_type, payload)

第一次插入成功 → 返回 None

重复插入命中唯一键 → 返回已有记录（若已绑定 job_id，直接把它返回）

link_job_id(db, user_id, key, job_id)：将这次幂等请求与 job_id 关联"""
# app/services/idempotency.py
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.infra.logger import emit
from app.core.models import CommandRequest
import json, uuid

def ensure_request(db, user_id: str, key: str, cmd_type: str, payload: dict):
    """
    职能：
    - 幂等记录：首次插入；若唯一键冲突则查回已有记录并返回。
    返回：
    - CommandRequest ORM 对象（保证非 None）；出错直接抛异常。
    日志：
    - idem_create_ok / idem_integrity_hit / idem_integrity_miss / idem_create_error
    """
    req = CommandRequest(
        id=str(uuid.uuid4()),
        user_id=user_id,
        key=key,
        cmd_type=cmd_type,
        payload=json.dumps(payload or {}),
        job_id=None,
    )
    try:
        db.add(req)
        db.commit()
        db.refresh(req)
        emit("idem_create_ok", user_id=user_id, key=key, request_id=req.id)
        return req
    except IntegrityError:
        db.rollback()
        existed = (
            db.query(CommandRequest)
              .filter(CommandRequest.user_id == user_id, CommandRequest.key == key)
              .first()
        )
        if existed:
            emit("idem_integrity_hit", user_id=user_id, key=key, request_id=existed.id, job_id=existed.job_id)
            return existed
        else:
            emit("idem_integrity_miss", user_id=user_id, key=key)
            raise
    except Exception as e:
        db.rollback()
        emit("idem_create_error", user_id=user_id, key=key, error=str(e))
        raise

def link_job_id(db: Session, user_id: str, key: str, job_id: str):
    row = db.query(CommandRequest).filter_by(user_id=user_id, key=key).first()
    if row:
        row.job_id = job_id
        db.add(row); db.commit()

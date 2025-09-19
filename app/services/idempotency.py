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
from app.core.models import CommandRequest

def ensure_request(db: Session, user_id: str, key: str, cmd_type: str, payload: dict):
    row = CommandRequest(user_id=user_id, key=key, cmd_type=cmd_type, payload=payload)
    db.add(row)
    try:
        db.commit()     # 首次提交成功
        return None
    except IntegrityError:
        db.rollback()
        existed = db.query(CommandRequest).filter_by(user_id=user_id, key=key).first()
        if existed and existed.job_id:
            return {"job_id": existed.job_id, "status": "PENDING"}
        return {"job_id": None, "status": "PENDING"}

def link_job_id(db: Session, user_id: str, key: str, job_id: str):
    row = db.query(CommandRequest).filter_by(user_id=user_id, key=key).first()
    if row:
        row.job_id = job_id
        db.add(row); db.commit()

"""
模块职能：
- Worker 侧统一调度：解析命令→解析账号→会话→调用 Connector→返回结果。

函数：
- run_job(job_id, user_id, site, action, account_selector, payload)

日志：
- job_dispatch / job_start / job_step / job_finished / job_failed
"""
import os, traceback
from sqlalchemy.orm import Session
from app.infra.db import SessionLocal
from app.infra.logger import emit
from app.services import accounts as acct_svc, secrets as sec_svc, sessions as sess_svc
from app.connectors.registry import get_connector

SESSION_TTL = int(os.getenv("SESSION_TTL_SECONDS","86400"))

def run_job(job_id: str, user_id: str, site: str, action: str, account_selector: dict, payload: dict) -> dict:
    emit("job_dispatch", job_id=job_id, user_id=user_id, site=site, action=action)
    db: Session = SessionLocal()
    try:
        acc = acct_svc.resolve(db, user_id, account_selector)
        acc_dict = {"id":acc.id, "user_id":acc.user_id, "site":acc.site, "account_name":acc.account_name}
        secrets = sec_svc.decrypt_str(acc.secret_encrypted)

        Connector = get_connector(site); connector = Connector()
        emit("job_start", job_id=job_id)
        session_ctx = sess_svc.ensure_session(db, connector, acc_dict, secrets, ttl_seconds=SESSION_TTL)

        emit("job_step", job_id=job_id, step="perform", action=action)
        res = connector.perform(action, payload, session_ctx)
        if not res.ok:
            emit("job_finished", job_id=job_id, status="FAILED", error=res.error)
            return {"ok": False, "error": res.error}

        emit("job_finished", job_id=job_id, status="SUCCEEDED")
        return {"ok": True, "data": res.data}
    except Exception as e:
        emit("job_failed", job_id=job_id, error=str(e), trace=traceback.format_exc())
        return {"ok": False, "error": str(e)}
    finally:
        db.close()

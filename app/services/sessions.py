"""
模块职能：
- 会话复用与登录：优先用有效会话；失效则调用 Connector.login()，再落库。

日志：
- sess_hit / sess_miss_login / sess_saved
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.core.models import Session as SessionModel
from app.services.secrets import encrypt_dict, decrypt_str
from app.infra.logger import emit
from app.connectors.base import SessionCtx

def _now(): return datetime.now(timezone.utc)

def get_valid_session(db: Session, account_id: str) -> Optional[Dict]:
    row = (db.query(SessionModel)
           .filter(SessionModel.account_id==account_id, SessionModel.status=="ACTIVE")
           .order_by(SessionModel.updated_at.desc()).first())
    if row and row.expires_at and row.expires_at > _now():
        emit("sess_hit", account_id=account_id)
        return decrypt_str(row.data_encrypted)
    return None

def save_session(db: Session, account_id: str, data_dict: Dict, expires_at: Optional[datetime]):
    row = SessionModel(account_id=account_id, data_encrypted=encrypt_dict(data_dict),
                       status="ACTIVE", expires_at=expires_at)
    db.add(row); db.commit()
    emit("sess_saved", account_id=account_id)

def ensure_session(db: Session, connector, account: Dict, secrets: Dict, ttl_seconds: int) -> SessionCtx:
    cached = get_valid_session(db, account["id"])
    if cached:
        return SessionCtx(kind=cached.get("kind","httpx"), store=cached.get("store",{}))
    emit("sess_miss_login", account_id=account["id"])
    res = connector.login(account, secrets, backend="httpx")
    if not res.ok:
        if res.need_user_action: raise RuntimeError("pending_user_action")
        raise RuntimeError(f"login_failed: {res.error}")
    expires = _now() + timedelta(seconds=ttl_seconds) if ttl_seconds>0 else None
    save_session(db, account_id=account["id"],
                 data_dict={"kind":res.session.kind,"store":res.session.store},
                 expires_at=expires)
    return res.session

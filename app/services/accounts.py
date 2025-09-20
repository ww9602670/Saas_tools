"""
模块职能：
- 账户 CRUD 与选择器解析（{"site":"...", "account_name":"..."}）。

日志：
- acct_create / acct_resolve
"""
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from app.core.models import Account
from app.services.secrets import encrypt_dict
from app.infra.logger import emit

def create_account(db: Session, user_id: str, site: str, account_name: str,
                   secrets: Dict, meta: Optional[Dict]=None) -> Account:
    acc = Account(user_id=user_id, site=site, account_name=account_name,
                  secret_encrypted=encrypt_dict(secrets), meta_json=(meta or {}).__str__())
    db.add(acc); db.commit(); db.refresh(acc)
    emit("acct_create", user_id=user_id, site=site, account_id=acc.id)
    return acc

def list_accounts(db: Session, user_id: str, site: Optional[str]=None) -> List[Account]:
    q = db.query(Account).filter(Account.user_id==user_id)
    if site: q = q.filter(Account.site==site)
    return q.order_by(Account.created_at.desc()).all()

def resolve(db: Session, user_id: str, selector: Dict) -> Account:
    site, name = selector.get("site"), selector.get("account_name")
    acc = (db.query(Account)
           .filter(Account.user_id==user_id, Account.site==site, Account.account_name==name)
           .first())
    if not acc: raise ValueError("account_not_found")
    emit("acct_resolve", user_id=user_id, site=site, account_id=acc.id)
    return acc

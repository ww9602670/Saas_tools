"""
模块职能：
- 账户创建/列表/测试登录，供前端与运维使用。
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.context import get_context, Context
from app.infra.db import get_db
from app.services import accounts as acct_svc, secrets as sec_svc
from app.connectors.registry import get_connector
from app.infra.logger import emit

router = APIRouter()

class CreateAccountIn(BaseModel):
    site: str
    account_name: str
    secrets: dict

@router.post("/accounts")
def create_account(inp: CreateAccountIn, db: Session=Depends(get_db), ctx: Context=Depends(get_context)):
    acc = acct_svc.create_account(db, ctx.user_id, inp.site, inp.account_name, inp.secrets)
    emit("api_accounts_create", user_id=ctx.user_id, site=inp.site, account_id=acc.id)
    return {"id": acc.id, "site": acc.site, "account_name": acc.account_name}

@router.get("/accounts")
def list_accounts(site: str|None=Query(default=None), db: Session=Depends(get_db), ctx: Context=Depends(get_context)):
    rows = acct_svc.list_accounts(db, ctx.user_id, site=site)
    emit("api_accounts_list", user_id=ctx.user_id, site=site or "*")
    return [{"id":r.id,"site":r.site,"account_name":r.account_name} for r in rows]

class TestLoginIn(BaseModel):
    account_selector: dict  # {"site":"example","account_name":"acc1"}

@router.post("/accounts/test_login")
def test_login(inp: TestLoginIn, db: Session=Depends(get_db), ctx: Context=Depends(get_context)):
    acc = acct_svc.resolve(db, ctx.user_id, inp.account_selector)
    secrets = sec_svc.decrypt_str(acc.secret_encrypted)
    Connector = get_connector(acc.site); connector = Connector()
    res = connector.login({"id": acc.id, "user_id":acc.user_id,"site":acc.site,"account_name":acc.account_name},
                          secrets, backend="httpx")
    if not res.ok:
        raise HTTPException(400, f"login_failed: {res.error}")
    emit("api_accounts_test_login", account_id=acc.id, ok=True)
    return {"ok": True}

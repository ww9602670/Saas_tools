# app/api/accounts.py
# -*- coding: utf-8 -*-
"""
账户 API（读侧隔离增强：管理员旁路）
------------------------------------
职能：
- 创建账户（保持原有行为与返回不变）
- 列表账户：普通用户仅能看到自己的；管理员可查看全量（可按 site 过滤）
- 测试登录（保持原有行为与返回不变）

引用库说明：
- FastAPI: APIRouter / Depends / HTTPException / Query
- SQLAlchemy: Session + text（在管理员旁路分支里用 SQL 读取，避免改动 service 层）
- Pydantic: 入参模型校验
- 项目内模块：
  - app.core.context: get_context / Context（从 JWT 解析 user_id/role/username）
  - app.infra.db: get_db（提供数据库会话）
  - app.services.accounts / app.services.secrets: 账户创建、账户解析与密钥解密
  - app.connectors.registry.get_connector: 动态加载站点 connector
  - app.infra.logger.emit: 结构化日志，写控制台或 logs/app.log（取决于 LOG_TO_FILE）

运行逻辑（列表接口）：
1) 解析 ctx（user_id / role）
2) 如果 role == "admin"：
   - 直接用 SQL 查询 accounts（可选按 site 过滤）
   - 记录日志 api_accounts_list_all（包含 count）
3) 否则（普通用户）：
   - 走原来的 service: acct_svc.list_accounts(db, ctx.user_id, site)
   - 记录日志 api_accounts_list（包含 count）
4) 返回结构保持为 [{"id","site","account_name"}]

与其他脚本/模块的关系：
- 不改 services.accounts 的签名与行为；普通用户路径仍调用它
- 不改 /api/accounts 的输入输出，前端/测试无感
- 不改 /api/accounts/test_login 的权限，仍按“只能解本人的账户”解析
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

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
def create_account(
    inp: CreateAccountIn,
    db: Session = Depends(get_db),
    ctx: Context = Depends(get_context),
):
    """
    创建账户（保持原有逻辑）：
    - 使用服务层将密钥加密后落库到 accounts 表
    - 账户归属（owner）= 当前登录用户 ctx.user_id（Step2 已实现）
    - 返回 {"id","site","account_name"}，不回传敏感信息
    """
    acc = acct_svc.create_account(db, ctx.user_id, inp.site, inp.account_name, inp.secrets)
    emit("api_accounts_create", user_id=ctx.user_id, site=inp.site, account_id=acc.id)
    return {"id": acc.id, "site": acc.site, "account_name": acc.account_name}

@router.get("/accounts")
def list_accounts(
    site: str | None = Query(default=None),
    db: Session = Depends(get_db),
    ctx: Context = Depends(get_context),
):
    """
    列表账户（读侧隔离 + 管理员旁路）：
    - 普通用户：仅返回自己名下账户（沿用 service 层）
    - 管理员：返回全量账户（可按 site 过滤）
    返回结构： [{"id","site","account_name"}]
    """
    # 管理员旁路：查询全量
    if ctx.role == "admin":
        if site:
            rows = db.execute(
                text("""
                    SELECT id, site, account_name
                    FROM accounts
                    WHERE site = :site
                    ORDER BY created_at DESC
                """),
                {"site": site},
            ).mappings().all()
        else:
            rows = db.execute(
                text("""
                    SELECT id, site, account_name
                    FROM accounts
                    ORDER BY created_at DESC
                """)
            ).mappings().all()

        emit("api_accounts_list_all", actor=ctx.user_id, role="admin", site=site or "*", count=len(rows))
        return [{"id": r["id"], "site": r["site"], "account_name": r["account_name"]} for r in rows]

    # 普通用户：仅本人
    rows = acct_svc.list_accounts(db, ctx.user_id, site=site)
    emit("api_accounts_list", user_id=ctx.user_id, site=site or "*", count=len(rows))
    return [{"id": r.id, "site": r.site, "account_name": r.account_name} for r in rows]

class TestLoginIn(BaseModel):
    account_selector: dict  # {"site":"example","account_name":"acc1"}

@router.post("/accounts/test_login")
def test_login(
    inp: TestLoginIn,
    db: Session = Depends(get_db),
    ctx: Context = Depends(get_context),
):
    """
    账户测试登录（保持原有逻辑）：
    - 解析 account_selector 为具体账户（仅能解析到“当前用户”的账户）
    - 解密密钥，加载对应 connector 执行一次登录动作
    - 成功则返回 {"ok": true}，失败 400
    """
    acc = acct_svc.resolve(db, ctx.user_id, inp.account_selector)
    secrets = sec_svc.decrypt_str(acc.secret_encrypted)

    Connector = get_connector(acc.site)
    connector = Connector()
    res = connector.login(
        {"id": acc.id, "user_id": acc.user_id, "site": acc.site, "account_name": acc.account_name},
        secrets,
        backend="httpx",
    )
    if not res.ok:
        emit("api_accounts_test_login", account_id=acc.id, ok=False, error=res.error)
        raise HTTPException(400, f"login_failed: {res.error}")

    emit("api_accounts_test_login", account_id=acc.id, ok=True)
    return {"ok": True}

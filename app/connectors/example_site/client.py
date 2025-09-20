"""
模块职能：
- “示例站点”连接器：演示 login/perform。
- 不依赖外网，便于端到端打通。

日志事件：
- connector_example_login_ok / connector_example_login_need_action / connector_example_action
"""
from typing import Dict
from app.connectors.base import BaseConnector, SessionCtx, LoginResult, ActionResult
from app.infra.logger import emit
from app.connectors.example_site.schemas import FetchProfileIn, FetchProfileOut

class ExampleConnector(BaseConnector):
    site = "example"
    supported_actions = {"fetch_profile"}

    def login(self, account: dict, secrets: dict, *, backend: str="httpx") -> LoginResult:
        if not secrets.get("password"):
            emit("connector_example_login_need_action", account_id=account["id"])
            return LoginResult(ok=False, need_user_action=True, error="missing password")
        session = SessionCtx(kind="httpx", store={"token": f"TOKEN_{account['account_name']}"})
        emit("connector_example_login_ok", account_id=account["id"])
        return LoginResult(ok=True, session=session)

    def perform(self, action: str, payload: Dict, session: SessionCtx) -> ActionResult:
        if action == "fetch_profile":
            data_in = FetchProfileIn(**payload)
            out = FetchProfileOut(uid=data_in.uid, name="Alice", level=3)
            emit("connector_example_action", action=action, uid=data_in.uid)
            return ActionResult(ok=True, data=out.dict())
        return ActionResult(ok=False, error=f"unsupported action: {action}")

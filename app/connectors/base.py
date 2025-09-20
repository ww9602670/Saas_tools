"""
模块职能：
- 定义连接器抽象（登录 + 动作执行），统一会话/返回结构。

函数/类：
- SessionCtx：封装 httpx/Playwright 句柄与凭据片段。
- LoginResult / ActionResult：统一返回。
- BaseConnector：站点适配器基类（login/perform）。
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Literal, Optional, Dict

class SessionCtx:
    def __init__(self, kind: Literal["httpx","playwright"], handle: Any=None, store: Optional[Dict]=None):
        self.kind = kind
        self.handle = handle
        self.store = store or {}

class LoginResult:
    def __init__(self, ok: bool, session: Optional[SessionCtx]=None, need_user_action: bool=False, error: str=""):
        self.ok = ok
        self.session = session
        self.need_user_action = need_user_action
        self.error = error

class ActionResult:
    def __init__(self, ok: bool, data: Any=None, artifacts: Optional[list]=None, error: str=""):
        self.ok = ok
        self.data = data
        self.artifacts = artifacts or []
        self.error = error

class BaseConnector(ABC):
    site: ClassVar[str]
    supported_actions: ClassVar[set[str]]

    @abstractmethod
    def login(self, account: dict, secrets: dict, *, backend: str="httpx") -> LoginResult: ...
    @abstractmethod
    def perform(self, action: str, payload: dict, session: SessionCtx) -> ActionResult: ...

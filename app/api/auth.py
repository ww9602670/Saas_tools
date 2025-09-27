# app/api/auth.py
"""
颁发 JWT（HS256）

日志事件（通过 app.infra.logger.emit 发出）：
- auth_login_attempt：收到登录请求（不记录明文密码）
- auth_login_failed：登录失败（原因：inactive / not_found_or_bad_password）
- auth_login_success：登录成功（包含 user_id、role）
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infra.db import get_db
from app.infra.logger import emit
from app.core.models_user import User
from app.core.security import verify_password, create_access_token

# 注意：这里不要再写 prefix="/api"
router = APIRouter(tags=["auth"])


class LoginInput(BaseModel):
    username: str
    password: str


class LoginOutput(BaseModel):
    access_token: str


# 子路由路径只写 "/login"；最终会被主程序以 "/api" 前缀挂载为 "/api/login"
@router.post("/login", response_model=LoginOutput)
def login(body: LoginInput, request: Request, db: Session = Depends(get_db)):
    # 1) 请求打点（不记录明文密码）
    emit(
        "auth_login_attempt",
        username=body.username,
        ip=str(request.client.host) if request.client else None,
        ua=request.headers.get("user-agent"),
    )

    user = db.query(User).filter(User.username == body.username).first()
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        # 2) 失败打点（避免精确区分“用户不存在”和“口令错误”，以免信息泄露）
        reason = "inactive" if (user and not user.is_active) else "not_found_or_bad_password"
        emit("auth_login_failed", username=body.username, reason=reason)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 3) 成功签发（JWT 负载包含 role；响应 JSON 结构不变）
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role.value,
    }
    token = create_access_token(payload)

    # 4) 成功打点（不记录 token）
    emit("auth_login_success", user_id=user.id, username=user.username, role=user.role.value)

    return {"access_token": token}

"""
应用入口：
- 加载 .env（先 .env.example 作默认，再用 .env 覆盖）
- lifespan 启动阶段：配置日志 → 打印 logger_config → 初始化数据库
- 装载请求日志中间件、路由
- 提供 /health、/api/me
"""
from pathlib import Path
from dotenv import load_dotenv

# 1) 先加载 .env，务必在导入 logger 之前
ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
if ENV_EXAMPLE.exists():
    load_dotenv(ENV_EXAMPLE, override=False)
if ENV.exists():
    load_dotenv(ENV, override=True)

# 2) 正常导入
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from app.middleware.logging import RequestLoggingMiddleware
from app.infra.logger import (
    configure_logging, emit,
    LOG_TO_FILE, LOG_DIR, LOG_FILE, LOG_ROTATE_WHEN, LOG_BACKUP_COUNT,
)
from app.infra.db import init_db
from app.api import auth as auth_api
from app.api import commands as commands_api
from app.api import jobs as jobs_api
from app.core.context import get_context, Context

# 3) lifespan：替代 on_event（startup/shutdown）
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    configure_logging()
    emit(
        "logger_config",
        to_file=LOG_TO_FILE, dir=LOG_DIR, file=LOG_FILE,
        when=LOG_ROTATE_WHEN, backup=LOG_BACKUP_COUNT,
    )
    init_db()
    emit("db_init_done")
    yield
    # shutdown
    emit("app_shutdown")

# 4) 创建应用并装配（lifespan 要在这里传入）
app = FastAPI(title="Step3: Commands + Idempotency", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)

@app.get("/health")
def health():
    return {"ok": True}

# 路由
app.include_router(auth_api.router,    prefix="/api", tags=["auth"])
app.include_router(commands_api.router, prefix="/api", tags=["commands"])
app.include_router(jobs_api.router,     prefix="/api", tags=["jobs"])

# 受保护示例：/api/me
@app.get("/api/me")
def whoami(ctx: Context = Depends(get_context)):
    emit("auth_whoami", user_id=ctx.user_id, role=ctx.role)
    return {"user_id": ctx.user_id, "role": ctx.role}
"""
应用入口：
- 加载 .env（先 .env.example 作默认，再用 .env 覆盖）
- lifespan 启动阶段：配置日志 → 打印 logger_config → 初始化数据库
- 装载请求日志中间件、路由
- 提供 /health、/api/me
"""
from pathlib import Path
from dotenv import load_dotenv

# 1) 先加载 .env，务必在导入 logger 之前
ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
if ENV_EXAMPLE.exists():
    load_dotenv(ENV_EXAMPLE, override=False)
if ENV.exists():
    load_dotenv(ENV, override=True)

# 2) 正常导入
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from app.middleware.logging import RequestLoggingMiddleware
from app.infra.logger import (
    configure_logging, emit,
    LOG_TO_FILE, LOG_DIR, LOG_FILE, LOG_ROTATE_WHEN, LOG_BACKUP_COUNT,
)
from app.infra.db import init_db
from app.api import auth as auth_api
from app.api import commands as commands_api
from app.api import jobs as jobs_api
from app.core.context import get_context, Context

# 3) lifespan：替代 on_event（startup/shutdown）
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    configure_logging()
    emit(
        "logger_config",
        to_file=LOG_TO_FILE, dir=LOG_DIR, file=LOG_FILE,
        when=LOG_ROTATE_WHEN, backup=LOG_BACKUP_COUNT,
    )
    init_db()
    emit("db_init_done")
    yield
    # shutdown
    emit("app_shutdown")

# 4) 创建应用并装配（lifespan 要在这里传入）
app = FastAPI(title="Step3: Commands + Idempotency", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)

@app.get("/health")
def health():
    return {"ok": True}

# 路由
app.include_router(auth_api.router,    prefix="/api", tags=["auth"])
app.include_router(commands_api.router, prefix="/api", tags=["commands"])
app.include_router(jobs_api.router,     prefix="/api", tags=["jobs"])

# 受保护示例：/api/me
@app.get("/api/me")
def whoami(ctx: Context = Depends(get_context)):
    emit("auth_whoami", user_id=ctx.user_id, role=ctx.role)
    return {"user_id": ctx.user_id, "role": ctx.role}

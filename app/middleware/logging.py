"""
模块职责：请求级调试日志中间件。
- 为每个请求生成 request_id；
- 记录 request_start 与 request_end（含耗时、状态码）；
- 捕获异常并输出 request_error，随后抛出让 FastAPI 处理。
"""
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.infra.logger import emit

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = str(uuid.uuid4())
        start = time.perf_counter()
        emit(
            "request_start",
            request_id=rid,
            method=request.method,
            path=str(request.url.path),
        )
        try:
            response: Response = await call_next(request)
            dur_ms = round((time.perf_counter() - start) * 1000, 2)
            emit(
                "request_end",
                request_id=rid,
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                duration_ms=dur_ms,
            )
            # 便于链路追踪，在响应头带上 request_id
            response.headers["x-request-id"] = rid
            return response
        except Exception as e:
            dur_ms = round((time.perf_counter() - start) * 1000, 2)
            emit(
                "request_error",
                request_id=rid,
                method=request.method,
                path=str(request.url.path),
                error=repr(e),
                duration_ms=dur_ms,
            )
            raise
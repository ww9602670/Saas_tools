# Step 1: Health + Debug Logging

## 1) 准备
cp .env.example .env

## 2) 启动
# Docker 方式
docker compose up --build -d
# 或本地方式
# uvicorn app.main:app --reload

## 3) 验证
curl -i http://localhost:8000/health

# 预期：
HTTP/1.1 200 OK
x-request-id: <UUID>
{"ok": true}

## 4) 查看日志
# 容器日志（或本地控制台）应该出现：
{"event": "request_start", "request_id": "...", "method": "GET", "path": "/health"}
{"event": "request_end",   "request_id": "...", "method": "GET", "path": "/health", "status_code": 200, "duration_ms": 1.23}

## 5) 故障排查
- 若 8000 端口无响应：检查容器是否运行 `docker ps`；
- 若无日志：确认 `LOG_LEVEL`；确保未被平台屏蔽 stdout；
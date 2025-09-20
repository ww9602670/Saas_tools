# app/workers/worker_entry.py
"""
RQ Worker 启动入口：
- 默认常驻；传 --burst 则队列空了就退出。
- 兼容 RQ 1.x/2.x；显式 Redis 连接。
日志：worker_env_loaded / worker_start / worker_stop
"""
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from app.infra.logger import configure_logging, emit

try:
    from rq import Worker
except ImportError:
    from rq.worker import Worker
try:
    from rq import Queue
except ImportError:
    from rq.queue import Queue

from redis import from_url as redis_from_url

def _load_env():
    root = Path(__file__).resolve().parents[2]
    env_example = root / ".env.example"
    env_file = root / ".env"
    if env_example.exists():
        load_dotenv(env_example, override=False)
    if env_file.exists():
        load_dotenv(env_file, override=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--burst", action="store_true", help="队列空时自动退出")
    parser.add_argument("--queue", default=os.getenv("RQ_QUEUE", "default"))
    parser.add_argument("--redis", default=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    args = parser.parse_args()

    _load_env()
    configure_logging()
    emit("worker_env_loaded", REDIS_URL=args.redis, RQ_QUEUE=args.queue)
    emit("worker_start", redis=args.redis, queue=args.queue)

    conn = redis_from_url(args.redis)
    q = Queue(args.queue, connection=conn)
    worker = Worker([q], connection=conn)

    try:
        worker.work(burst=args.burst)
    except KeyboardInterrupt:
        emit("worker_stop", reason="KeyboardInterrupt")
    finally:
        emit("worker_stop", reason="exit")

if __name__ == "__main__":
    main()

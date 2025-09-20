"""
模块职能：
- 生产者：把作业入 RQ 队列（Redis）。

函数：
- enqueue(job_id, user_id, type, account_selector, payload)

日志：
- q_enqueue
"""
import os
from app.infra.logger import emit

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RQ_QUEUE  = os.getenv("RQ_QUEUE", "default")

_redis = None
_Queue = None
_queue = None


def _get_queue():
    global _redis, _Queue, _queue
    if _queue is None:
        from redis import from_url as redis_from_url
        try:
            from rq import Queue
        except ImportError:
            from rq.queue import Queue
        _redis = redis_from_url(REDIS_URL)
        _Queue = Queue
        _queue = _Queue(RQ_QUEUE, connection=_redis)
    return _queue

def enqueue(job_id: str, user_id: str, type: str, account_selector: dict, payload: dict) -> str:
    site, action = type.split(".", 1)
    from app.workers.dispatcher import run_job  # 延迟导入避免循环
    rq_job = _get_queue().enqueue(
        run_job,
        job_id=job_id,
        kwargs=dict(job_id=job_id, user_id=user_id, site=site, action=action,
                    account_selector=account_selector, payload=payload),
        retry=None,
    )
    emit("q_enqueue", job_id=job_id, rq_job_id=rq_job.id, site=site, action=action)
    return rq_job.id
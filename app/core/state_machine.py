# app/core/state_machine.py
""""模块职能：

定义 Job 的状态与合法迁移，保障“PENDING→RUNNING→SUCCEEDED/FAILED”的有序性

主要函数/枚举：

JobStatus：状态枚举

can_transit(src, dst)：判断是否允许状态迁移"""

from enum import Enum

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"

VALID = {
    "PENDING": {"RUNNING"},
    "RUNNING": {"SUCCEEDED", "FAILED"},
    "SUCCEEDED": set(),
    "FAILED": set(),
}

def can_transit(src: JobStatus, dst: JobStatus) -> bool:
    return dst in VALID[src]

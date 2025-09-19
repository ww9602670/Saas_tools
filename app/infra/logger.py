"""
模块职责：统一日志配置与结构化输出。
- configure_logging(): 根据环境变量设置日志等级，兼容 uvicorn。
- emit(event, **kwargs): 输出结构化日志（dict -> 一行），方便检索。
"""
"""
统一日志配置（控制台 + 文件），结构化输出（JSON 一行）。
- 环境变量控制开关与路径。
- uvicorn 日志也合流到同一套 handler。
"""
import logging, json, os, pathlib
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timezone


LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "true").lower() == "true"
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_FILE = os.getenv("LOG_FILE", "app.log")
LOG_ROTATE_WHEN = os.getenv("LOG_ROTATE_WHEN", "midnight")
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "7"))

_configured = False

def configure_logging():
    global _configured
    if _configured:
        return

    if LOG_TO_FILE:
        pathlib.Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
        logfile_path = os.path.join(LOG_DIR, LOG_FILE)

    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    console = logging.StreamHandler()
    console.setLevel(getattr(logging, LEVEL, logging.INFO))
    console.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    root.addHandler(console)

    if LOG_TO_FILE:
        fileh = TimedRotatingFileHandler(
            logfile_path, when=LOG_ROTATE_WHEN, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
        )
        fileh.setLevel(getattr(logging, LEVEL, logging.INFO))
        # 文件里只写 message，本项目 message 是纯 JSON，便于检索
        fileh.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(fileh)

    root.setLevel(getattr(logging, LEVEL, logging.INFO))

    # 合流 uvicorn 日志
    for ln in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(ln)
        lg.handlers = []
        lg.propagate = True

    _configured = True

_app_logger = logging.getLogger("app")

def _now_iso():
    # 本地时区 + 毫秒，示例：2025-09-18T17:30:42.123+09:00
    return datetime.now().astimezone().isoformat(timespec="milliseconds")

def emit(event: str, level: str = "INFO", **kwargs):
    """
    结构化日志：默认 INFO；每条都带时间戳 ts（本地时区）。
    用法：emit("request_start", request_id=..., method="GET", path="/health")
    """
    rec = {"ts": _now_iso(), "level": level, "event": event, **kwargs}
    try:
        _app_logger.info(json.dumps(rec, ensure_ascii=False))
    except Exception:
        _app_logger.info(str(rec))


def emit_error(event: str, **kwargs):
    """
    错误日志（level=ERROR），同样带 ts。
    用法：emit_error("db_error", request_id=..., err=str(e))
    """
    rec = {"ts": _now_iso(), "level": "ERROR", "event": event, **kwargs}
    try:
        _app_logger.error(json.dumps(rec, ensure_ascii=False))
    except Exception:
        _app_logger.error(str(rec))
""""
模块职能：

定义两张表：

command_requests：记录用户的每次“提交命令”，并用 (user_id, key) 保证幂等

jobs：记录后台任务的生命周期与结果

主要类型/方法：

CommandRequest：字段 user_id / key / cmd_type / payload / job_id

Job：字段 id / user_id / type / status / error

Job.create_pending(db, job_id, user_id, job_type)：预创建 PENDING

Job.start(db, job_id)：置 RUNNING

Job.finish(db, job_id, status, error="")：置 SUCCEEDED/FAILED"""

# app/core/models.py
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy import Column, String, JSON, UniqueConstraint, Text, DateTime
from sqlalchemy.sql import func
import uuid
from app.core.state_machine import JobStatus, can_transit

Base = declarative_base()

class CommandRequest(Base):
    __tablename__ = "command_requests"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True, nullable=False)
    key = Column(String, nullable=False)       # 幂等键
    cmd_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    job_id = Column(String, nullable=True)
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_idem"),)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True)      # 与后台任务 job_id 一致
    user_id = Column(String, index=True, nullable=False)
    type = Column(String, nullable=False)
    status = Column(String, default=JobStatus.PENDING)
    error = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    @staticmethod
    def create_pending(db: Session, job_id: str, user_id: str, job_type: str):
        obj = Job(id=job_id, user_id=user_id, type=job_type, status=JobStatus.PENDING)
        db.add(obj); db.commit()

    @staticmethod
    def start(db: Session, job_id: str):
        job = db.get(Job, job_id)
        if job and can_transit(JobStatus(job.status), JobStatus.RUNNING):
            job.status = JobStatus.RUNNING
            db.add(job); db.commit()
        return job

    @staticmethod
    def finish(db: Session, job_id: str, status: str, error: str = ""):
        job = db.get(Job, job_id)
        if job and can_transit(JobStatus(job.status), JobStatus(status)):
            job.status = status
            job.error = error or ""
            db.add(job); db.commit()
        return job

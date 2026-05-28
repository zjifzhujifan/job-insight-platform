from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CrawlTask(Base):
    __tablename__ = "crawl_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    celery_task_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    task_type: Mapped[str] = mapped_column(String(50))  # crawl / analyze / report
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / running / completed / failed
    params: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 格式的任务参数
    result: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 格式的任务结果
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

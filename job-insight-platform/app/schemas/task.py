from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TaskCreate(BaseModel):
    task_type: Literal["crawl", "analyze", "report"]
    params: dict | None = None


class TaskResponse(BaseModel):
    id: int
    celery_task_id: str
    task_type: str
    status: str
    result: str | None = None
    error_message: str | None = None
    retry_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    total: int
    items: list[TaskResponse]

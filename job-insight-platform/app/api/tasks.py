import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.task import CrawlTask
from app.models.user import User
from app.schemas.task import TaskCreate, TaskResponse, TaskListResponse
from app.worker.celery_app import celery_app
from app.worker.tasks import run_analysis, run_crawl, run_report

router = APIRouter(prefix="/tasks", tags=["任务管理"])


class TaskDispatcher:
    """将 API 层任务类型映射到真实 Celery 任务。"""

    def __init__(self):
        self._task_map = {
            "crawl": run_crawl,
            "analyze": run_analysis,
            "report": run_report,
        }

    def delay(self, task_type: str, params: dict | None = None):
        task = self._task_map.get(task_type)
        if task is None:
            raise ValueError(f"未知任务类型: {task_type}")
        return task.delay(params)


dispatch_task = TaskDispatcher()


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """提交异步任务（爬虫 / 分析 / 报告）"""
    try:
        celery_result = dispatch_task.delay(data.task_type, data.params)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    task = CrawlTask(
        celery_task_id=celery_result.id,
        task_type=data.task_type,
        status="pending",
        params=json.dumps(data.params) if data.params else None,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """查询任务列表"""
    stmt = select(CrawlTask)
    count_stmt = select(func.count(CrawlTask.id))

    if status:
        stmt = stmt.where(CrawlTask.status == status)
        count_stmt = count_stmt.where(CrawlTask.status == status)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(CrawlTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)

    return TaskListResponse(total=total, items=result.scalars().all())


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """查询任务状态"""
    result = await db.execute(select(CrawlTask).where(CrawlTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.delete("/{task_id}", status_code=204)
async def cancel_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """取消任务"""
    result = await db.execute(select(CrawlTask).where(CrawlTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    celery_app.control.revoke(task.celery_task_id, terminate=True)

    task.status = "cancelled"
    await db.commit()

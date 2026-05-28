from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobResponse, JobListResponse

router = APIRouter(prefix="/jobs", tags=["岗位"])


@router.get("", response_model=JobListResponse)
async def list_jobs(
    city: str | None = Query(None, description="城市筛选"),
    skill: str | None = Query(None, description="技能筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """查询岗位列表（支持分页和筛选）"""
    stmt = select(Job)
    count_stmt = select(func.count(Job.id))

    if city:
        stmt = stmt.where(Job.city == city)
        count_stmt = count_stmt.where(Job.city == city)
    if skill:
        stmt = stmt.where(Job.skills.ilike(f"%{skill}%"))
        count_stmt = count_stmt.where(Job.skills.ilike(f"%{skill}%"))

    # 总数
    total = (await db.execute(count_stmt)).scalar() or 0

    # 分页
    stmt = stmt.order_by(Job.crawled_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return JobListResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """获取岗位详情"""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="岗位不存在")
    return job

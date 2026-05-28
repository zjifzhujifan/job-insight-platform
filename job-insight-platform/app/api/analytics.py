from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.job import Job
from app.models.user import User
from app.schemas.job import SalaryAnalysis, SkillRanking, TrendData
from app.services.analytics import get_salary_by_city, get_skill_ranking

router = APIRouter(prefix="/analytics", tags=["数据分析"])


@router.get("/salary", response_model=list[SalaryAnalysis])
async def salary_analysis(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """各城市薪资分析"""
    return await get_salary_by_city(db)


@router.get("/skills", response_model=list[SkillRanking])
async def skill_ranking(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """热门技能排行"""
    return await get_skill_ranking(db, limit=limit)


@router.get("/trends", response_model=list[TrendData])
async def job_trends(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """岗位数量与薪资趋势"""
    date_expr = func.date(Job.crawled_at)
    stmt = (
        select(
            date_expr.label("date"),
            func.count(Job.id).label("job_count"),
            func.avg((Job.salary_min + Job.salary_max) / 2).label("avg_salary"),
        )
        .where(Job.salary_min.isnot(None), Job.salary_max.isnot(None))
        .group_by(date_expr)
        .order_by(date_expr)
    )
    result = await db.execute(stmt)
    return [
        TrendData(
            date=str(row.date),
            job_count=row.job_count,
            avg_salary=round(float(row.avg_salary), 0),
        )
        for row in result.all()
    ]

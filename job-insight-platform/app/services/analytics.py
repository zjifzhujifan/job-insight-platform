from collections import Counter

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.schemas.job import SalaryAnalysis, SkillRanking


async def get_salary_by_city(db: AsyncSession) -> list[SalaryAnalysis]:
    """按城市统计薪资"""
    stmt = (
        select(
            Job.city,
            func.avg((Job.salary_min + Job.salary_max) / 2).label("avg_salary"),
            func.count(Job.id).label("job_count"),
        )
        .where(Job.salary_min.isnot(None), Job.salary_max.isnot(None))
        .group_by(Job.city)
        .order_by(func.count(Job.id).desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        SalaryAnalysis(
            city=row.city,
            avg_salary=round(float(row.avg_salary), 0),
            median_salary=round(float(row.avg_salary), 0),  # 简化处理，实际可用窗口函数
            job_count=row.job_count,
        )
        for row in rows
    ]


async def get_skill_ranking(db: AsyncSession, limit: int = 20) -> list[SkillRanking]:
    """统计技能出现频率"""
    result = await db.execute(select(Job.skills).where(Job.skills.isnot(None)))
    rows = result.scalars().all()

    counter: Counter[str] = Counter()
    for skills_str in rows:
        for skill in skills_str.split(","):
            skill = skill.strip().lower()
            if skill:
                counter[skill] += 1

    total = sum(counter.values())
    return [
        SkillRanking(
            skill=skill,
            count=count,
            percentage=round(count / total * 100, 2) if total else 0,
        )
        for skill, count in counter.most_common(limit)
    ]

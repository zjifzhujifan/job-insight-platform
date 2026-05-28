"""
数据管道 —— 将爬取到的 JobItem 清洗并存入数据库。
支持：字段清洗、技能标准化、增量去重（基于 title+company+city 判断是否已存在）。
"""

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler.spiders.base import JobItem
from app.models.job import Job


# 技能名称标准化映射
SKILL_ALIASES = {
    "python3": "python",
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "pg": "postgresql",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "es": "elasticsearch",
    "mongo": "mongodb",
    "rabbitmq": "rabbitmq",
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "node.js": "nodejs",
    "node": "nodejs",
    "golang": "go",
}


def clean_item(item: JobItem) -> JobItem:
    """数据清洗：去空白、标准化薪资和技能"""
    item.title = item.title.strip()
    item.company = item.company.strip()
    item.city = item.city.strip()

    # 薪资合理性校验
    if item.salary_min and item.salary_max:
        if item.salary_min > item.salary_max:
            item.salary_min, item.salary_max = item.salary_max, item.salary_min
        if item.salary_min < 1000:
            item.salary_min = None
            item.salary_max = None
        if item.salary_max and item.salary_max > 500000:
            item.salary_max = 500000

    # 技能标签标准化
    if item.skills:
        raw_skills = [s.strip().lower() for s in item.skills.split(",") if s.strip()]
        normalized = []
        seen = set()
        for skill in raw_skills:
            skill = SKILL_ALIASES.get(skill, skill)
            if skill not in seen:
                seen.add(skill)
                normalized.append(skill)
        item.skills = ", ".join(sorted(normalized))

    return item


async def check_duplicate(db: AsyncSession, item: JobItem) -> bool:
    """检查是否已存在相同岗位（基于 title + company + city + source）"""
    stmt = select(Job.id).where(
        and_(
            Job.title == item.title,
            Job.company == item.company,
            Job.city == item.city,
            Job.source == item.source,
        )
    ).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def save_items(db: AsyncSession, items: list[JobItem], skip_duplicates: bool = True) -> int:
    """
    批量存入数据库。
    skip_duplicates=True 时跳过已存在的记录（增量爬取）。
    返回实际写入数量。
    """
    saved = 0
    skipped = 0

    for item in items:
        item = clean_item(item)

        if skip_duplicates and await check_duplicate(db, item):
            skipped += 1
            continue

        job = Job(
            title=item.title,
            company=item.company,
            city=item.city,
            salary_min=item.salary_min,
            salary_max=item.salary_max,
            experience=item.experience,
            education=item.education,
            skills=item.skills,
            description=item.description,
            source=item.source,
            source_url=item.source_url,
        )
        db.add(job)
        saved += 1

    if saved > 0:
        await db.commit()

    return saved

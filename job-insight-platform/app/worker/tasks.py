"""
Celery 异步任务定义。
三种任务类型：爬虫 / 数据分析 / 报告生成。
"""

import asyncio
import json

from celery.utils.log import get_task_logger
from sqlalchemy import update

from app.worker.celery_app import celery_app
from app.database import async_session
from app.models.task import CrawlTask
from app.crawler.spider_manager import spider_manager, setup_spiders
from app.crawler.pipelines import save_items

logger = get_task_logger(__name__)

# 初始化爬虫注册
setup_spiders()


def _run_async(coro):
    """在同步 Celery worker 中运行异步代码"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _update_task_status(celery_task_id: str, status: str, result: str | None = None, error: str | None = None):
    """更新数据库中的任务状态"""
    async with async_session() as db:
        stmt = (
            update(CrawlTask)
            .where(CrawlTask.celery_task_id == celery_task_id)
            .values(status=status, result=result, error_message=error)
        )
        await db.execute(stmt)
        await db.commit()


@celery_app.task(bind=True, name="app.worker.tasks.run_crawl", max_retries=3, default_retry_delay=60)
def run_crawl(self, params: dict | None = None):
    """
    爬虫任务：支持单源或多源爬取。
    params:
        keyword: 搜索关键词（默认 Python）
        city: 城市（默认空，不限）
        pages: 每个爬虫爬取页数（默认 3）
        spiders: 指定爬虫列表（默认 ['demo']，可选 zhipin/51job/lagou）
    """
    params = params or {}
    keyword = params.get("keyword", "Python")
    city = params.get("city", "")
    pages = params.get("pages", 3)
    spider_names = params.get("spiders", ["demo"])

    logger.info(f"开始爬虫任务: keyword={keyword}, city={city}, pages={pages}, spiders={spider_names}")
    _run_async(_update_task_status(self.request.id, "running"))

    try:
        # 使用爬虫管理器并发执行
        crawl_result = _run_async(
            spider_manager.run_all(
                keyword=keyword,
                city=city,
                pages=pages,
                spider_names=spider_names,
            )
        )

        # 存入数据库
        async def _save():
            async with async_session() as db:
                return await save_items(db, crawl_result.items)

        saved_count = _run_async(_save())

        result = json.dumps({
            "crawled": crawl_result.total_items,
            "saved": saved_count,
            "by_source": crawl_result.items_by_source,
            "stats": crawl_result.stats_by_source,
        }, ensure_ascii=False)

        _run_async(_update_task_status(self.request.id, "completed", result=result))
        logger.info(f"爬虫任务完成: 爬取 {crawl_result.total_items} 条，存入 {saved_count} 条")
        return result

    except Exception as exc:
        _run_async(_update_task_status(self.request.id, "failed", error=str(exc)))
        logger.error(f"爬虫任务失败: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, name="app.worker.tasks.run_analysis", max_retries=3)
def run_analysis(self, params: dict | None = None):
    """数据分析任务：生成薪资、技能等分析数据"""
    logger.info("开始数据分析任务")
    _run_async(_update_task_status(self.request.id, "running"))

    try:
        from app.services.analytics import get_salary_by_city, get_skill_ranking

        async def _analyze():
            async with async_session() as db:
                salary = await get_salary_by_city(db)
                skills = await get_skill_ranking(db)
                return {
                    "salary_by_city": [s.model_dump() for s in salary],
                    "skill_ranking": [s.model_dump() for s in skills],
                }

        data = _run_async(_analyze())
        result = json.dumps(data, ensure_ascii=False)
        _run_async(_update_task_status(self.request.id, "completed", result=result))
        logger.info("数据分析任务完成")
        return result

    except Exception as exc:
        _run_async(_update_task_status(self.request.id, "failed", error=str(exc)))
        logger.error(f"数据分析任务失败: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, name="app.worker.tasks.run_report", max_retries=3)
def run_report(self, params: dict | None = None):
    """报告生成任务：生成 pyecharts 可视化 HTML 报告"""
    logger.info("开始报告生成任务")
    _run_async(_update_task_status(self.request.id, "running"))

    try:
        from app.services.report import ReportGenerator

        async def _generate():
            async with async_session() as db:
                generator = ReportGenerator(db)
                filename = await generator.generate()
                return filename

        filename = _run_async(_generate())
        result = json.dumps({"report_file": filename}, ensure_ascii=False)
        _run_async(_update_task_status(self.request.id, "completed", result=result))
        logger.info(f"报告生成完成: {filename}")
        return result

    except Exception as exc:
        _run_async(_update_task_status(self.request.id, "failed", error=str(exc)))
        logger.error(f"报告生成失败: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(name="app.worker.tasks.dispatch_task")
def dispatch_task(task_type: str, params: dict | None = None):
    """兼容旧调用的任务分发入口，返回真实业务任务 ID。"""
    task_map = {
        "crawl": run_crawl,
        "analyze": run_analysis,
        "report": run_report,
    }
    task_func = task_map.get(task_type)
    if not task_func:
        raise ValueError(f"未知任务类型: {task_type}，可选: {list(task_map.keys())}")
    result = task_func.delay(params)
    return {"task_type": task_type, "celery_task_id": result.id}

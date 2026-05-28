"""
爬虫管理器 —— 注册、调度和管理多个爬虫。
支持：多源并发爬取、结果合并去重、统计汇总。
"""

import asyncio
from dataclasses import dataclass

from loguru import logger

from app.crawler.spiders.base import BaseSpider, JobItem


@dataclass
class CrawlResult:
    """爬取结果汇总"""
    total_items: int
    items_by_source: dict[str, int]
    stats_by_source: dict[str, dict]
    items: list[JobItem]


class SpiderManager:
    """爬虫管理器"""

    def __init__(self):
        self._spiders: dict[str, type[BaseSpider]] = {}

    def register(self, spider_cls: type[BaseSpider]) -> None:
        """注册爬虫类"""
        name = spider_cls.name
        self._spiders[name] = spider_cls
        logger.info(f"注册爬虫: {name}")

    def get_spider(self, name: str) -> BaseSpider | None:
        """获取爬虫实例"""
        cls = self._spiders.get(name)
        return cls() if cls else None

    @property
    def available_spiders(self) -> list[str]:
        return list(self._spiders.keys())

    async def run_single(
        self,
        spider_name: str,
        keyword: str = "Python",
        city: str = "",
        pages: int = 3,
    ) -> list[JobItem]:
        """运行单个爬虫"""
        spider = self.get_spider(spider_name)
        if not spider:
            raise ValueError(f"未找到爬虫: {spider_name}，可用: {self.available_spiders}")
        return await spider.run(keyword=keyword, city=city, pages=pages)

    async def run_all(
        self,
        keyword: str = "Python",
        city: str = "",
        pages: int = 3,
        spider_names: list[str] | None = None,
    ) -> CrawlResult:
        """
        并发运行多个爬虫，合并去重结果。
        spider_names: 指定要运行的爬虫，None 则运行所有。
        """
        names = spider_names or self.available_spiders
        spiders = []
        for name in names:
            spider = self.get_spider(name)
            if spider:
                spiders.append(spider)
            else:
                logger.warning(f"跳过未知爬虫: {name}")

        if not spiders:
            return CrawlResult(total_items=0, items_by_source={}, stats_by_source={}, items=[])

        logger.info(f"并发启动 {len(spiders)} 个爬虫: {[s.name for s in spiders]}")

        # 并发执行所有爬虫
        tasks = [
            spider.run(keyword=keyword, city=city, pages=pages)
            for spider in spiders
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果并去重
        all_items: list[JobItem] = []
        seen: set[str] = set()
        items_by_source: dict[str, int] = {}
        stats_by_source: dict[str, dict] = {}

        for spider, result in zip(spiders, results):
            if isinstance(result, Exception):
                logger.error(f"[{spider.name}] 爬取异常: {result}")
                stats_by_source[spider.name] = {"error": str(result)}
                continue

            source_count = 0
            for item in result:
                fp = item.fingerprint
                if fp not in seen:
                    seen.add(fp)
                    all_items.append(item)
                    source_count += 1

            items_by_source[spider.name] = source_count
            stats_by_source[spider.name] = spider.stats.summary()

        logger.info(f"全部爬取完成: 总计 {len(all_items)} 条（去重后），来源分布: {items_by_source}")

        return CrawlResult(
            total_items=len(all_items),
            items_by_source=items_by_source,
            stats_by_source=stats_by_source,
            items=all_items,
        )


# 全局爬虫管理器
spider_manager = SpiderManager()


def setup_spiders():
    """注册所有可用爬虫"""
    from app.crawler.spiders.demo_spider import DemoSpider
    from app.crawler.spiders.zhipin_spider import ZhipinSpider
    from app.crawler.spiders.qcwy_spider import QcwySpider
    from app.crawler.spiders.lagou_spider import LagouSpider

    spider_manager.register(DemoSpider)
    spider_manager.register(ZhipinSpider)
    spider_manager.register(QcwySpider)
    spider_manager.register(LagouSpider)

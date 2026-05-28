"""爬虫模块测试：基类、DemoSpider、数据管道、爬虫管理器"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler.spiders.base import JobItem, CrawlStats
from app.crawler.spiders.demo_spider import DemoSpider
from app.crawler.spiders.zhipin_spider import ZhipinSpider
from app.crawler.spiders.qcwy_spider import QcwySpider
from app.crawler.spiders.lagou_spider import LagouSpider
from app.crawler.pipelines import clean_item, save_items, check_duplicate, SKILL_ALIASES
from app.crawler.spider_manager import SpiderManager
from app.crawler.proxy_pool import ProxyPool, Proxy
from app.models.job import Job


# ========== JobItem 测试 ==========

class TestJobItem:
    def test_fingerprint_uniqueness(self):
        item1 = JobItem(title="Python开发", company="字节", city="北京", source="demo")
        item2 = JobItem(title="Python开发", company="字节", city="北京", source="demo")
        item3 = JobItem(title="Java开发", company="字节", city="北京", source="demo")
        assert item1.fingerprint == item2.fingerprint
        assert item1.fingerprint != item3.fingerprint

    def test_fingerprint_different_source(self):
        item1 = JobItem(title="Python开发", company="字节", city="北京", source="zhipin")
        item2 = JobItem(title="Python开发", company="字节", city="北京", source="lagou")
        assert item1.fingerprint != item2.fingerprint


# ========== CrawlStats 测试 ==========

class TestCrawlStats:
    def test_initial_stats(self):
        stats = CrawlStats()
        assert stats.total_requests == 0
        assert stats.success_rate == 0

    def test_success_rate(self):
        stats = CrawlStats(total_requests=10, success_requests=8, failed_requests=2)
        assert stats.success_rate == 80.0

    def test_summary(self):
        stats = CrawlStats(total_requests=5, success_requests=4, failed_requests=1, total_items=20, duplicates=3)
        summary = stats.summary()
        assert summary["total_requests"] == 5
        assert summary["total_items"] == 20
        assert summary["duplicates"] == 3


# ========== DemoSpider 测试 ==========

class TestDemoSpider:
    @pytest.mark.asyncio
    async def test_run_returns_items(self):
        spider = DemoSpider()
        items = await spider.run(keyword="Python", pages=2)
        assert len(items) > 0
        assert all(isinstance(i, JobItem) for i in items)

    @pytest.mark.asyncio
    async def test_items_have_required_fields(self):
        spider = DemoSpider()
        items = await spider.run(pages=1)
        for item in items:
            assert item.title
            assert item.company
            assert item.city
            assert item.salary_min is not None
            assert item.salary_max is not None
            assert item.source == "demo"

    @pytest.mark.asyncio
    async def test_stats_updated(self):
        spider = DemoSpider()
        await spider.run(pages=2)
        assert spider.stats.total_requests == 2
        assert spider.stats.success_requests == 2
        assert spider.stats.total_items > 0

    @pytest.mark.asyncio
    async def test_deduplication(self):
        spider = DemoSpider()
        await spider.run(pages=5)
        fingerprints = [item.fingerprint for item in spider.items]
        assert len(fingerprints) == len(set(fingerprints))

    @pytest.mark.asyncio
    async def test_city_filter(self):
        spider = DemoSpider()
        items = await spider.run(city="北京", pages=1)
        for item in items:
            assert item.city == "北京"


# ========== 薪资解析测试 ==========

class TestSalaryParsing:
    def test_zhipin_salary(self):
        spider = ZhipinSpider()
        assert spider._parse_salary("15-25K") == (15000, 25000)
        assert spider._parse_salary("15-25k·14薪") == (15000, 25000)
        assert spider._parse_salary("面议") == (None, None)

    def test_qcwy_salary(self):
        spider = QcwySpider()
        assert spider._parse_salary("1-1.5万/月") == (10000, 15000)
        assert spider._parse_salary("8-12千/月") == (8000, 12000)
        assert spider._parse_salary("20-40万/年") == (int(200000 / 12), int(400000 / 12))
        assert spider._parse_salary("面议") == (None, None)

    def test_lagou_salary(self):
        spider = LagouSpider()
        assert spider._parse_salary("15k-25k") == (15000, 25000)
        assert spider._parse_salary("15K-25K") == (15000, 25000)
        assert spider._parse_salary("面议") == (None, None)


# ========== URL 构建测试 ==========

class TestBuildUrls:
    def test_zhipin_urls(self):
        spider = ZhipinSpider()
        urls = spider.build_urls("Python", "北京", 3)
        assert len(urls) == 3
        assert "101010100" in urls[0]
        assert "Python" in urls[0]

    def test_qcwy_urls(self):
        spider = QcwySpider()
        urls = spider.build_urls("Python", "上海", 2)
        assert len(urls) == 2
        assert "020000" in urls[0]

    def test_lagou_urls(self):
        spider = LagouSpider()
        urls = spider.build_urls("Python", "杭州", 3)
        assert len(urls) == 3


# ========== 数据管道测试 ==========

class TestPipeline:
    def test_clean_item_basic(self):
        item = JobItem(title="  Python开发  ", company=" 字节跳动 ", city=" 北京 ",
                       skills="Python, fastapi, REDIS, python", source="test")
        cleaned = clean_item(item)
        assert cleaned.title == "Python开发"
        assert cleaned.company == "字节跳动"
        assert cleaned.city == "北京"

    def test_clean_skills_dedup_and_normalize(self):
        item = JobItem(title="T", company="C", city="B",
                       skills="Python, python, py, k8s, Golang", source="t")
        cleaned = clean_item(item)
        skills = cleaned.skills.split(", ")
        # python 只出现一次（py 和 python 合并）
        assert skills.count("python") == 1
        assert "kubernetes" in skills
        assert "go" in skills

    def test_clean_salary_swap(self):
        item = JobItem(title="T", company="C", city="B",
                       salary_min=30000, salary_max=15000, source="t")
        cleaned = clean_item(item)
        assert cleaned.salary_min == 15000
        assert cleaned.salary_max == 30000

    def test_clean_salary_too_low(self):
        item = JobItem(title="T", company="C", city="B",
                       salary_min=500, salary_max=1000, source="t")
        cleaned = clean_item(item)
        assert cleaned.salary_min is None

    def test_clean_salary_cap(self):
        item = JobItem(title="T", company="C", city="B",
                       salary_min=10000, salary_max=999999, source="t")
        cleaned = clean_item(item)
        assert cleaned.salary_max == 500000

    @pytest.mark.asyncio
    async def test_save_items(self, db_session: AsyncSession):
        items = [
            JobItem(title="测试岗位1", company="测试公司", city="北京",
                    salary_min=10000, salary_max=20000, skills="python", source="test"),
            JobItem(title="测试岗位2", company="测试公司", city="上海",
                    salary_min=15000, salary_max=25000, skills="java", source="test"),
        ]
        saved = await save_items(db_session, items)
        assert saved == 2

    @pytest.mark.asyncio
    async def test_save_items_skip_duplicates(self, db_session: AsyncSession):
        items = [
            JobItem(title="去重测试", company="公司A", city="北京", source="test"),
        ]
        saved1 = await save_items(db_session, items)
        assert saved1 == 1

        # 再次保存相同数据应跳过
        saved2 = await save_items(db_session, items)
        assert saved2 == 0

    @pytest.mark.asyncio
    async def test_check_duplicate(self, db_session: AsyncSession):
        item = JobItem(title="唯一岗位", company="唯一公司", city="深圳", source="test")
        assert await check_duplicate(db_session, item) is False

        await save_items(db_session, [item])
        assert await check_duplicate(db_session, item) is True


# ========== 爬虫管理器测试 ==========

class TestSpiderManager:
    def test_register_and_list(self):
        manager = SpiderManager()
        manager.register(DemoSpider)
        assert "demo" in manager.available_spiders

    def test_get_spider(self):
        manager = SpiderManager()
        manager.register(DemoSpider)
        spider = manager.get_spider("demo")
        assert isinstance(spider, DemoSpider)

    def test_get_unknown_spider(self):
        manager = SpiderManager()
        assert manager.get_spider("nonexistent") is None

    @pytest.mark.asyncio
    async def test_run_single(self):
        manager = SpiderManager()
        manager.register(DemoSpider)
        items = await manager.run_single("demo", pages=1)
        assert len(items) > 0

    @pytest.mark.asyncio
    async def test_run_single_unknown(self):
        manager = SpiderManager()
        with pytest.raises(ValueError, match="未找到爬虫"):
            await manager.run_single("nonexistent")

    @pytest.mark.asyncio
    async def test_run_all(self):
        manager = SpiderManager()
        manager.register(DemoSpider)
        result = await manager.run_all(pages=1)
        assert result.total_items > 0
        assert "demo" in result.items_by_source
        assert "demo" in result.stats_by_source

    @pytest.mark.asyncio
    async def test_run_all_empty(self):
        manager = SpiderManager()
        result = await manager.run_all(pages=1, spider_names=["nonexistent"])
        assert result.total_items == 0


# ========== 代理池测试 ==========

class TestProxyPool:
    @pytest.mark.asyncio
    async def test_add_and_get(self):
        pool = ProxyPool()
        await pool.add("127.0.0.1", 8080)
        assert pool.size == 1

        proxy = await pool.get()
        assert proxy is not None
        assert proxy.host == "127.0.0.1"
        assert proxy.port == 8080

    @pytest.mark.asyncio
    async def test_dedup(self):
        pool = ProxyPool()
        await pool.add("127.0.0.1", 8080)
        await pool.add("127.0.0.1", 8080)
        assert pool.size == 1

    @pytest.mark.asyncio
    async def test_report_fail_and_evict(self):
        pool = ProxyPool()
        await pool.add("bad.proxy", 1234)
        proxy = await pool.get()

        for _ in range(ProxyPool.MAX_FAIL_COUNT):
            await pool.report_fail(proxy)

        # 应该被淘汰
        assert pool.size == 0
        assert await pool.get() is None

    @pytest.mark.asyncio
    async def test_report_success_resets_fail(self):
        pool = ProxyPool()
        await pool.add("good.proxy", 5678)
        proxy = await pool.get()

        await pool.report_fail(proxy)
        assert proxy.fail_count == 1

        await pool.report_success(proxy)
        assert proxy.fail_count == 0

    @pytest.mark.asyncio
    async def test_proxy_url(self):
        proxy = Proxy(host="1.2.3.4", port=8080, protocol="http")
        assert proxy.url == "http://1.2.3.4:8080"

        proxy_s = Proxy(host="1.2.3.4", port=443, protocol="https")
        assert proxy_s.url == "https://1.2.3.4:443"

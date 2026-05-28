"""
爬虫基类 —— 所有具体爬虫继承此类实现 parse 方法。
支持：并发控制、代理轮换、请求重试、增量爬取、请求统计。
"""

import asyncio
import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx
from fake_useragent import UserAgent
from loguru import logger

from app.config import get_settings
from app.crawler.proxy_pool import ProxyPool, proxy_pool

settings = get_settings()


@dataclass
class JobItem:
    """爬取到的岗位数据结构"""
    title: str
    company: str
    city: str
    salary_min: int | None = None
    salary_max: int | None = None
    experience: str | None = None
    education: str | None = None
    skills: str | None = None
    description: str | None = None
    source: str = ""
    source_url: str | None = None

    @property
    def fingerprint(self) -> str:
        """生成唯一指纹用于去重"""
        raw = f"{self.title}|{self.company}|{self.city}|{self.source}"
        return hashlib.md5(raw.encode()).hexdigest()


@dataclass
class CrawlStats:
    """爬取统计"""
    total_requests: int = 0
    success_requests: int = 0
    failed_requests: int = 0
    total_items: int = 0
    duplicates: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def elapsed(self) -> float:
        return round(time.time() - self.start_time, 2)

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0
        return round(self.success_requests / self.total_requests * 100, 1)

    def summary(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "success_requests": self.success_requests,
            "failed_requests": self.failed_requests,
            "success_rate": f"{self.success_rate}%",
            "total_items": self.total_items,
            "duplicates": self.duplicates,
            "elapsed_seconds": self.elapsed,
        }


class BaseSpider(ABC):
    """爬虫基类"""

    name: str = "base"
    base_url: str = ""
    max_retries: int = 3
    use_proxy: bool = False

    def __init__(self):
        self.ua = UserAgent()
        self.semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_REQUESTS)
        self.delay = settings.CRAWL_DELAY
        self.items: list[JobItem] = []
        self.seen_fingerprints: set[str] = set()
        self.stats = CrawlStats()
        self.proxy_pool: ProxyPool = proxy_pool

    def _headers(self) -> dict:
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    async def fetch(self, client: httpx.AsyncClient, url: str) -> str | None:
        """带并发限制、代理轮换和重试的请求"""
        async with self.semaphore:
            for attempt in range(1, self.max_retries + 1):
                self.stats.total_requests += 1
                proxy_url = None

                if self.use_proxy:
                    proxy = await self.proxy_pool.get()
                    if proxy:
                        proxy_url = proxy.url

                try:
                    req_kwargs = {"headers": self._headers(), "timeout": 15}
                    if proxy_url:
                        # httpx 需要在 client 层设置 proxy，这里用新 client
                        async with httpx.AsyncClient(proxy=proxy_url, follow_redirects=True) as proxy_client:
                            resp = await proxy_client.get(url, **req_kwargs)
                    else:
                        resp = await client.get(url, **req_kwargs)

                    resp.raise_for_status()
                    self.stats.success_requests += 1

                    if self.use_proxy and proxy:
                        await self.proxy_pool.report_success(proxy)

                    await asyncio.sleep(self.delay)
                    return resp.text

                except httpx.HTTPError as e:
                    self.stats.failed_requests += 1
                    if self.use_proxy and proxy:
                        await self.proxy_pool.report_fail(proxy)

                    if attempt < self.max_retries:
                        wait = attempt * 2
                        logger.warning(f"[{self.name}] 请求失败 ({attempt}/{self.max_retries}): {url} - {e}，{wait}s 后重试")
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"[{self.name}] 请求最终失败: {url} - {e}")

            return None

    async def fetch_json(self, client: httpx.AsyncClient, url: str, **kwargs) -> dict | None:
        """请求 JSON 接口"""
        async with self.semaphore:
            for attempt in range(1, self.max_retries + 1):
                self.stats.total_requests += 1
                try:
                    resp = await client.get(url, headers=self._headers(), timeout=15, **kwargs)
                    resp.raise_for_status()
                    self.stats.success_requests += 1
                    await asyncio.sleep(self.delay)
                    return resp.json()
                except (httpx.HTTPError, ValueError) as e:
                    self.stats.failed_requests += 1
                    if attempt < self.max_retries:
                        await asyncio.sleep(attempt * 2)
                    else:
                        logger.error(f"[{self.name}] JSON 请求失败: {url} - {e}")
            return None

    def add_item(self, item: JobItem) -> bool:
        """添加岗位，自动去重。返回 True 表示新增成功。"""
        fp = item.fingerprint
        if fp in self.seen_fingerprints:
            self.stats.duplicates += 1
            return False
        self.seen_fingerprints.add(fp)
        self.items.append(item)
        self.stats.total_items += 1
        return True

    @abstractmethod
    async def parse(self, html: str, url: str) -> list[JobItem]:
        """解析页面，返回岗位列表。子类必须实现。"""
        ...

    async def run(self, keyword: str = "Python", city: str = "", pages: int = 3) -> list[JobItem]:
        """启动爬虫，返回所有爬取到的岗位"""
        self.stats = CrawlStats()
        urls = self.build_urls(keyword, city, pages)
        logger.info(f"[{self.name}] 开始爬取: keyword={keyword}, city={city}, pages={len(urls)}")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for url in urls:
                html = await self.fetch(client, url)
                if html:
                    items = await self.parse(html, url)
                    for item in items:
                        self.add_item(item)
                    logger.info(f"[{self.name}] {url} -> {len(items)} 条")

        logger.info(f"[{self.name}] 爬取完成: {self.stats.summary()}")
        return self.items

    @abstractmethod
    def build_urls(self, keyword: str, city: str, pages: int) -> list[str]:
        """构造分页 URL 列表。子类必须实现。"""
        ...

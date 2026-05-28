"""
代理池 —— 管理和轮换代理 IP，降低被封禁风险。
支持从免费代理源获取、验证可用性、自动淘汰失效代理。
"""

import asyncio
import random
import time
from dataclasses import dataclass, field

import httpx
from loguru import logger


@dataclass
class Proxy:
    host: str
    port: int
    protocol: str = "http"
    fail_count: int = 0
    last_used: float = 0.0

    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"


class ProxyPool:
    """代理池：获取、验证、轮换代理"""

    MAX_FAIL_COUNT = 3
    VERIFY_URL = "https://httpbin.org/ip"
    VERIFY_TIMEOUT = 8

    def __init__(self):
        self._proxies: list[Proxy] = []
        self._lock = asyncio.Lock()

    @property
    def size(self) -> int:
        return len(self._proxies)

    async def add(self, host: str, port: int, protocol: str = "http") -> None:
        async with self._lock:
            # 去重
            if not any(p.host == host and p.port == port for p in self._proxies):
                self._proxies.append(Proxy(host=host, port=port, protocol=protocol))

    async def get(self) -> Proxy | None:
        """获取一个可用代理（优先选择失败次数少、最久未使用的）"""
        async with self._lock:
            available = [p for p in self._proxies if p.fail_count < self.MAX_FAIL_COUNT]
            if not available:
                return None
            # 按 (fail_count, last_used) 排序，优先使用质量好的
            available.sort(key=lambda p: (p.fail_count, p.last_used))
            proxy = available[0]
            proxy.last_used = time.time()
            return proxy

    async def report_fail(self, proxy: Proxy) -> None:
        """报告代理失败，累积到阈值自动淘汰"""
        async with self._lock:
            proxy.fail_count += 1
            if proxy.fail_count >= self.MAX_FAIL_COUNT:
                self._proxies = [p for p in self._proxies if p is not proxy]
                logger.info(f"淘汰代理: {proxy.url}")

    async def report_success(self, proxy: Proxy) -> None:
        """报告代理成功，重置失败计数"""
        async with self._lock:
            proxy.fail_count = 0

    async def verify(self, proxy: Proxy) -> bool:
        """验证代理是否可用"""
        try:
            async with httpx.AsyncClient(proxy=proxy.url, timeout=self.VERIFY_TIMEOUT) as client:
                resp = await client.get(self.VERIFY_URL)
                return resp.status_code == 200
        except Exception:
            return False

    async def fetch_free_proxies(self) -> int:
        """
        从免费代理源获取代理列表。
        实际使用时可替换为付费代理 API 以获得更好的质量和稳定性。
        """
        sources = [
            self._fetch_from_proxylist,
        ]
        total_added = 0
        for source in sources:
            try:
                count = await source()
                total_added += count
            except Exception as e:
                logger.warning(f"获取代理失败: {e}")
        logger.info(f"代理池更新完成，新增 {total_added} 个，当前总数 {self.size}")
        return total_added

    async def _fetch_from_proxylist(self) -> int:
        """示例：从公开代理列表获取（可替换为其他来源）"""
        count = 0
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # 这是示例，实际中替换为可靠的代理源 API
                resp = await client.get("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=&ssl=no&anonymity=anonymous")
                if resp.status_code == 200:
                    for line in resp.text.strip().split("\n"):
                        line = line.strip()
                        if ":" in line:
                            parts = line.split(":")
                            await self.add(parts[0], int(parts[1]))
                            count += 1
        except Exception as e:
            logger.warning(f"proxylist 获取失败: {e}")
        return count

    async def verify_all(self, max_concurrent: int = 20) -> int:
        """批量验证所有代理，淘汰不可用的"""
        sem = asyncio.Semaphore(max_concurrent)
        removed = 0

        async def _check(proxy: Proxy):
            nonlocal removed
            async with sem:
                if not await self.verify(proxy):
                    await self.report_fail(proxy)
                    await self.report_fail(proxy)
                    await self.report_fail(proxy)  # 直接淘汰
                    removed += 1

        tasks = [_check(p) for p in list(self._proxies)]
        await asyncio.gather(*tasks)
        logger.info(f"代理验证完成，淘汰 {removed} 个，剩余 {self.size} 个")
        return removed


# 全局代理池实例
proxy_pool = ProxyPool()

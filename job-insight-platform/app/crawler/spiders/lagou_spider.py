"""
拉勾网爬虫 —— 通过 Ajax JSON 接口爬取数据。
展示与 HTML 解析不同的 JSON API 爬取方式。
"""

import re

import httpx
from loguru import logger

from app.crawler.spiders.base import BaseSpider, JobItem


class LagouSpider(BaseSpider):
    """拉勾网爬虫（Ajax API 方式）"""

    name = "lagou"
    base_url = "https://www.lagou.com"
    search_api = "https://www.lagou.com/jobs/positionAjax.json"

    def build_urls(self, keyword: str, city: str, pages: int) -> list[str]:
        # 拉勾使用 POST 接口，这里返回页码列表作为占位
        return [str(p) for p in range(1, pages + 1)]

    def _parse_salary(self, salary_text: str) -> tuple[int | None, int | None]:
        """解析 '15k-25k' 格式"""
        match = re.search(r"(\d+)[kK]-(\d+)[kK]", salary_text)
        if match:
            return int(match.group(1)) * 1000, int(match.group(2)) * 1000
        return None, None

    async def run(self, keyword: str = "Python", city: str = "北京", pages: int = 3) -> list[JobItem]:
        """重写 run 方法，因为拉勾使用 POST + Cookie 验证"""
        self.stats.__init__()
        logger.info(f"[{self.name}] 开始爬取: keyword={keyword}, city={city}, pages={pages}")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            # 第一步：访问首页获取 Cookie
            try:
                await client.get(
                    f"{self.base_url}/jobs/list_{keyword}",
                    headers=self._headers(),
                    timeout=15,
                )
            except httpx.HTTPError as e:
                logger.error(f"[{self.name}] 获取 Cookie 失败: {e}")
                return self.items

            # 第二步：通过 Ajax 接口分页获取数据
            for page in range(1, pages + 1):
                self.stats.total_requests += 1
                try:
                    headers = self._headers()
                    headers.update({
                        "Referer": f"{self.base_url}/jobs/list_{keyword}",
                        "Content-Type": "application/x-www-form-urlencoded",
                        "X-Requested-With": "XMLHttpRequest",
                    })

                    resp = await client.post(
                        self.search_api,
                        headers=headers,
                        params={"city": city, "needAddtionalResult": "false"},
                        data={"first": "true" if page == 1 else "false", "pn": str(page), "kd": keyword},
                        timeout=15,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    self.stats.success_requests += 1

                    items = await self.parse_json(data)
                    for item in items:
                        self.add_item(item)
                    logger.info(f"[{self.name}] 第 {page} 页 -> {len(items)} 条")

                except (httpx.HTTPError, ValueError, KeyError) as e:
                    self.stats.failed_requests += 1
                    logger.warning(f"[{self.name}] 第 {page} 页失败: {e}")

                # 拉勾反爬严格，需要较长间隔
                import asyncio
                await asyncio.sleep(self.delay + 3)

        logger.info(f"[{self.name}] 爬取完成: {self.stats.summary()}")
        return self.items

    async def parse(self, html: str, url: str) -> list[JobItem]:
        """HTML 解析（备用）"""
        return []

    async def parse_json(self, data: dict) -> list[JobItem]:
        """解析 JSON 响应"""
        items = []

        try:
            result = data.get("content", {}).get("positionResult", {})
            positions = result.get("result", [])
        except (AttributeError, TypeError):
            return items

        for pos in positions:
            try:
                salary_text = pos.get("salary", "")
                salary_min, salary_max = self._parse_salary(salary_text)

                # 技能标签
                labels = pos.get("skillLables", []) or pos.get("positionLables", [])
                skills = ", ".join(labels) if labels else None

                items.append(JobItem(
                    title=pos.get("positionName", ""),
                    company=pos.get("companyFullName", pos.get("companyShortName", "未知")),
                    city=pos.get("city", ""),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    experience=pos.get("workYear"),
                    education=pos.get("education"),
                    skills=skills,
                    description=pos.get("positionAdvantage"),
                    source=self.name,
                    source_url=f"{self.base_url}/jobs/{pos.get('positionId', '')}.html",
                ))
            except Exception as e:
                logger.warning(f"[{self.name}] 解析岗位失败: {e}")
                continue

        return items

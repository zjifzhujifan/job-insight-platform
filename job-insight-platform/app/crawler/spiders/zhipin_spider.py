"""
Boss 直聘爬虫 —— 爬取 zhipin.com 的 Python 相关岗位。
注意：Boss 直聘反爬较严格，实际使用需配合代理池和适当的请求频率。
"""

import re
from urllib.parse import quote

from bs4 import BeautifulSoup
from loguru import logger

from app.crawler.spiders.base import BaseSpider, JobItem


class ZhipinSpider(BaseSpider):
    name = "zhipin"
    base_url = "https://www.zhipin.com"
    use_proxy = True  # Boss 直聘需要代理

    # 城市编码映射
    CITY_CODES = {
        "北京": "101010100",
        "上海": "101020100",
        "深圳": "101280600",
        "广州": "101280100",
        "杭州": "101210100",
        "成都": "101270100",
        "南京": "101190100",
        "武汉": "101200100",
    }

    def build_urls(self, keyword: str, city: str, pages: int) -> list[str]:
        city_code = self.CITY_CODES.get(city, "101010100")
        urls = []
        for page in range(1, pages + 1):
            urls.append(
                f"{self.base_url}/web/geek/job?query={quote(keyword)}&city={city_code}&page={page}"
            )
        return urls

    def _parse_salary(self, salary_text: str) -> tuple[int | None, int | None]:
        """解析薪资文本，如 '15-25K', '15-25K·14薪'"""
        match = re.search(r"(\d+)-(\d+)[Kk]", salary_text)
        if match:
            return int(match.group(1)) * 1000, int(match.group(2)) * 1000
        return None, None

    async def parse(self, html: str, url: str) -> list[JobItem]:
        items = []
        soup = BeautifulSoup(html, "lxml")

        # Boss 直聘的岗位卡片选择器
        job_cards = soup.select(".job-card-wrapper") or soup.select(".job-list li")

        for card in job_cards:
            try:
                # 岗位名称
                title_el = card.select_one(".job-name") or card.select_one(".job-title")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                # 薪资
                salary_el = card.select_one(".salary")
                salary_text = salary_el.get_text(strip=True) if salary_el else ""
                salary_min, salary_max = self._parse_salary(salary_text)

                # 公司名称
                company_el = card.select_one(".company-name") or card.select_one(".company-text")
                company = company_el.get_text(strip=True) if company_el else "未知"

                # 城市
                location_el = card.select_one(".job-area")
                city = location_el.get_text(strip=True).split("·")[0] if location_el else ""

                # 经验和学历
                tags = card.select(".tag-list li") or card.select(".job-info .text")
                experience = ""
                education = ""
                for tag in tags:
                    text = tag.get_text(strip=True)
                    if "年" in text or "经验" in text or "应届" in text:
                        experience = text
                    elif any(k in text for k in ["本科", "硕士", "大专", "博士", "不限"]):
                        education = text

                # 技能标签
                skill_tags = card.select(".tag-list .tag") or card.select(".job-keyword span")
                skills = ", ".join(t.get_text(strip=True) for t in skill_tags) if skill_tags else ""

                # 详情链接
                link_el = card.select_one("a[href]")
                detail_url = self.base_url + link_el["href"] if link_el and link_el.get("href") else None

                items.append(JobItem(
                    title=title,
                    company=company,
                    city=city,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    experience=experience or None,
                    education=education or None,
                    skills=skills or None,
                    source=self.name,
                    source_url=detail_url,
                ))
            except Exception as e:
                logger.warning(f"[{self.name}] 解析岗位卡片失败: {e}")
                continue

        return items

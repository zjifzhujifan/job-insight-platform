"""
前程无忧 (51job) 爬虫 —— 通过搜索接口爬取岗位数据。
前程无忧提供了相对规范的搜索页面结构，适合作为爬虫入门示例。
"""

import re
from urllib.parse import quote

from bs4 import BeautifulSoup
from loguru import logger

from app.crawler.spiders.base import BaseSpider, JobItem


class QcwySpider(BaseSpider):
    """前程无忧爬虫"""

    name = "51job"
    base_url = "https://search.51job.com"

    # 城市编码
    CITY_CODES = {
        "北京": "010000",
        "上海": "020000",
        "深圳": "040000",
        "广州": "030200",
        "杭州": "080200",
        "成都": "090200",
        "南京": "070200",
        "武汉": "180200",
    }

    def build_urls(self, keyword: str, city: str, pages: int) -> list[str]:
        city_code = self.CITY_CODES.get(city, "000000")
        urls = []
        for page in range(1, pages + 1):
            urls.append(
                f"{self.base_url}/jobsearch/search_result.php"
                f"?fromJs=1&keyword={quote(keyword)}&jobarea={city_code}&curr_page={page}"
            )
        return urls

    def _parse_salary(self, salary_text: str) -> tuple[int | None, int | None]:
        """
        解析薪资文本，支持多种格式：
        - '1-1.5万/月' -> (10000, 15000)
        - '8-12千/月'  -> (8000, 12000)
        - '20-40万/年' -> (16666, 33333)
        """
        salary_text = salary_text.strip()
        if not salary_text:
            return None, None

        # X-Y万/月
        match = re.search(r"([\d.]+)-([\d.]+)\s*万/月", salary_text)
        if match:
            return int(float(match.group(1)) * 10000), int(float(match.group(2)) * 10000)

        # X-Y千/月
        match = re.search(r"([\d.]+)-([\d.]+)\s*千/月", salary_text)
        if match:
            return int(float(match.group(1)) * 1000), int(float(match.group(2)) * 1000)

        # X-Y万/年 -> 转为月薪
        match = re.search(r"([\d.]+)-([\d.]+)\s*万/年", salary_text)
        if match:
            return int(float(match.group(1)) * 10000 / 12), int(float(match.group(2)) * 10000 / 12)

        return None, None

    async def parse(self, html: str, url: str) -> list[JobItem]:
        items = []
        soup = BeautifulSoup(html, "lxml")

        # 51job 搜索结果列表
        job_list = soup.select(".j_joblist .e") or soup.select("#resultList .el")

        for el in job_list:
            try:
                # 岗位名称
                title_el = el.select_one(".jname") or el.select_one(".t1 a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                # 公司名称
                company_el = el.select_one(".cname") or el.select_one(".t2 a")
                company = company_el.get_text(strip=True) if company_el else "未知"

                # 薪资
                salary_el = el.select_one(".sal") or el.select_one(".t4")
                salary_text = salary_el.get_text(strip=True) if salary_el else ""
                salary_min, salary_max = self._parse_salary(salary_text)

                # 工作地点
                location_el = el.select_one(".d.at") or el.select_one(".t3")
                city = ""
                if location_el:
                    city = location_el.get_text(strip=True).split("-")[0].strip()

                # 经验和学历（通常在同一个区域）
                info_el = el.select_one(".d.at") or el.select_one(".dc")
                experience = ""
                education = ""
                if info_el:
                    info_text = info_el.get_text(" ", strip=True)
                    exp_match = re.search(r"(\d+-\d+年|应届|不限)", info_text)
                    edu_match = re.search(r"(本科|硕士|大专|博士|不限学历)", info_text)
                    if exp_match:
                        experience = exp_match.group(1)
                    if edu_match:
                        education = edu_match.group(1)

                # 技能标签
                tag_els = el.select(".tags span") or el.select(".d.at span")
                skills = ", ".join(t.get_text(strip=True) for t in tag_els if t.get_text(strip=True))

                # 详情链接
                link = title_el.get("href", "") if title_el.name == "a" else ""
                if not link:
                    link_el = el.select_one("a[href]")
                    link = link_el["href"] if link_el else ""

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
                    source_url=link or None,
                ))
            except Exception as e:
                logger.warning(f"[{self.name}] 解析失败: {e}")
                continue

        return items

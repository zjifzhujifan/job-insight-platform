"""
示例爬虫 —— 生成模拟数据用于开发和测试。
替换此类为真实爬虫时，只需实现 build_urls 和 parse 方法。
"""

import random

from app.crawler.spiders.base import BaseSpider, JobItem


class DemoSpider(BaseSpider):
    """
    模拟爬虫：生成示例数据，不发送真实网络请求。
    用于开发调试和测试环境。
    """

    name = "demo"
    use_proxy = False

    _TITLES = [
        "Python开发工程师", "Python后端开发", "高级Python工程师",
        "数据分析师", "爬虫工程师", "AI算法工程师",
        "全栈开发工程师", "DevOps工程师", "数据工程师",
    ]
    _COMPANIES = [
        "字节跳动", "阿里巴巴", "腾讯", "美团", "百度",
        "京东", "网易", "快手", "滴滴", "小红书",
        "哔哩哔哩", "拼多多", "华为", "商汤科技", "旷视科技",
    ]
    _CITIES = ["北京", "上海", "深圳", "杭州", "广州", "成都", "南京", "武汉"]
    _SKILLS_POOL = [
        "Python", "Django", "FastAPI", "Flask", "MySQL", "Redis", "Docker", "Linux",
        "Git", "Celery", "PostgreSQL", "MongoDB", "Kafka", "Elasticsearch", "Kubernetes",
        "Scrapy", "Pandas", "NumPy", "PyTorch", "TensorFlow", "Go", "Java", "Vue", "React",
        "AWS", "CI/CD", "Nginx", "RabbitMQ", "GraphQL", "gRPC",
    ]
    _EDUCATION = ["本科", "硕士", "大专", "不限"]
    _EXPERIENCE = ["1-3年", "3-5年", "5-10年", "应届生", "不限"]
    _DESCRIPTIONS = [
        "负责后端服务架构设计与开发",
        "参与数据平台建设，处理海量数据",
        "开发和维护爬虫系统，保障数据采集稳定性",
        "负责AI模型的工程化落地",
        "参与微服务架构的设计和实现",
    ]

    def build_urls(self, keyword: str, city: str, pages: int) -> list[str]:
        return [f"https://demo.local/jobs?keyword={keyword}&city={city}&page={p}" for p in range(1, pages + 1)]

    async def run(self, keyword: str = "Python", city: str = "", pages: int = 3) -> list[JobItem]:
        """重写 run，跳过网络请求直接生成数据"""
        from app.crawler.spiders.base import CrawlStats
        self.stats = CrawlStats()

        for page in range(1, pages + 1):
            items = await self.parse("", f"demo://page/{page}")
            for item in items:
                if city and item.city != city:
                    item.city = city
                self.add_item(item)

        self.stats.total_requests = pages
        self.stats.success_requests = pages
        return self.items

    async def parse(self, html: str, url: str) -> list[JobItem]:
        items = []
        for _ in range(random.randint(10, 15)):
            salary_min = random.choice([8, 10, 12, 15, 18, 20, 25, 30]) * 1000
            salary_max = salary_min + random.choice([3, 5, 8, 10, 15]) * 1000
            skills = ", ".join(random.sample(self._SKILLS_POOL, k=random.randint(3, 7)))

            items.append(JobItem(
                title=random.choice(self._TITLES),
                company=random.choice(self._COMPANIES),
                city=random.choice(self._CITIES),
                salary_min=salary_min,
                salary_max=salary_max,
                experience=random.choice(self._EXPERIENCE),
                education=random.choice(self._EDUCATION),
                skills=skills,
                description=random.choice(self._DESCRIPTIONS),
                source=self.name,
                source_url=url,
            ))
        return items

"""
报告生成服务 —— 使用 pyecharts 生成可视化 HTML 报告。
包含：薪资分布图、城市薪资对比、技能排行、岗位趋势、学历/经验分布。
"""

import os
from datetime import datetime
from collections import Counter

from pyecharts import options as opts
from pyecharts.charts import Bar, Line, Pie, WordCloud, Page, Grid
from pyecharts.globals import ThemeType
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "reports")


class ReportGenerator:
    """可视化报告生成器"""

    def __init__(self, db: AsyncSession):
        self.db = db
        os.makedirs(REPORTS_DIR, exist_ok=True)

    async def generate(self) -> str:
        """生成完整 HTML 报告，返回文件名"""
        page = Page(page_title="招聘数据分析报告", layout=Page.SimplePageLayout)

        # 并行获取所有数据
        salary_chart = await self._salary_by_city_chart()
        skill_chart = await self._skill_wordcloud()
        skill_bar = await self._skill_bar_chart()
        edu_chart = await self._education_pie()
        exp_chart = await self._experience_pie()
        trend_chart = await self._trend_chart()
        company_chart = await self._top_companies_chart()

        page.add(
            salary_chart,
            skill_chart,
            skill_bar,
            trend_chart,
            edu_chart,
            exp_chart,
            company_chart,
        )

        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(REPORTS_DIR, filename)
        page.render(filepath)
        return filename

    async def _salary_by_city_chart(self) -> Bar:
        """各城市平均薪资对比柱状图"""
        stmt = (
            select(
                Job.city,
                func.avg(Job.salary_min).label("avg_min"),
                func.avg(Job.salary_max).label("avg_max"),
                func.count(Job.id).label("count"),
            )
            .where(Job.salary_min.isnot(None), Job.salary_max.isnot(None))
            .group_by(Job.city)
            .order_by(func.avg((Job.salary_min + Job.salary_max) / 2).desc())
            .limit(15)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        cities = [r.city for r in rows]
        avg_min = [round(float(r.avg_min) / 1000, 1) for r in rows]
        avg_max = [round(float(r.avg_max) / 1000, 1) for r in rows]

        chart = (
            Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="1000px", height="500px"))
            .add_xaxis(cities)
            .add_yaxis("平均最低薪资 (K)", avg_min, stack="salary")
            .add_yaxis("平均最高薪资 (K)", avg_max, stack="salary")
            .set_global_opts(
                title_opts=opts.TitleOpts(title="各城市薪资水平对比", subtitle="单位：千元/月"),
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30)),
                datazoom_opts=opts.DataZoomOpts(),
            )
        )
        return chart

    async def _skill_wordcloud(self) -> WordCloud:
        """技能词云图"""
        counter = await self._count_skills()
        words = [(skill, count) for skill, count in counter.most_common(60)]

        chart = (
            WordCloud(init_opts=opts.InitOpts(width="1000px", height="500px"))
            .add("", words, word_size_range=[16, 80], shape="circle")
            .set_global_opts(
                title_opts=opts.TitleOpts(title="热门技能词云"),
                tooltip_opts=opts.TooltipOpts(is_show=True),
            )
        )
        return chart

    async def _skill_bar_chart(self) -> Bar:
        """技能需求 Top20 柱状图"""
        counter = await self._count_skills()
        top20 = counter.most_common(20)
        skills = [s[0] for s in top20]
        counts = [s[1] for s in top20]

        chart = (
            Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="1000px", height="500px"))
            .add_xaxis(skills)
            .add_yaxis("岗位数量", counts)
            .set_global_opts(
                title_opts=opts.TitleOpts(title="技能需求 Top 20"),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
                datazoom_opts=opts.DataZoomOpts(),
            )
        )
        return chart

    async def _education_pie(self) -> Pie:
        """学历要求分布饼图"""
        stmt = (
            select(Job.education, func.count(Job.id).label("count"))
            .where(Job.education.isnot(None))
            .group_by(Job.education)
            .order_by(func.count(Job.id).desc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        data = [(r.education, r.count) for r in rows]

        chart = (
            Pie(init_opts=opts.InitOpts(width="500px", height="400px"))
            .add("", data, radius=["30%", "70%"], rosetype="radius")
            .set_global_opts(
                title_opts=opts.TitleOpts(title="学历要求分布"),
                legend_opts=opts.LegendOpts(orient="vertical", pos_right="5%", pos_top="15%"),
            )
            .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {d}%"))
        )
        return chart

    async def _experience_pie(self) -> Pie:
        """经验要求分布饼图"""
        stmt = (
            select(Job.experience, func.count(Job.id).label("count"))
            .where(Job.experience.isnot(None))
            .group_by(Job.experience)
            .order_by(func.count(Job.id).desc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        data = [(r.experience, r.count) for r in rows]

        chart = (
            Pie(init_opts=opts.InitOpts(width="500px", height="400px"))
            .add("", data, radius=["30%", "70%"], rosetype="area")
            .set_global_opts(
                title_opts=opts.TitleOpts(title="经验要求分布"),
                legend_opts=opts.LegendOpts(orient="vertical", pos_right="5%", pos_top="15%"),
            )
            .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {d}%"))
        )
        return chart

    async def _trend_chart(self) -> Line:
        """岗位数量与薪资趋势折线图"""
        date_expr = func.date(Job.crawled_at)
        stmt = (
            select(
                date_expr.label("date"),
                func.count(Job.id).label("job_count"),
                func.avg((Job.salary_min + Job.salary_max) / 2).label("avg_salary"),
            )
            .where(Job.salary_min.isnot(None), Job.salary_max.isnot(None))
            .group_by(date_expr)
            .order_by(date_expr)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        dates = [str(r.date) for r in rows]
        counts = [r.job_count for r in rows]
        salaries = [round(float(r.avg_salary) / 1000, 1) for r in rows]

        chart = (
            Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="1000px", height="500px"))
            .add_xaxis(dates)
            .add_yaxis("岗位数量", counts, yaxis_index=0)
            .add_yaxis("平均薪资 (K)", salaries, yaxis_index=1)
            .extend_axis(yaxis=opts.AxisOpts(name="薪资 (K)", position="right"))
            .set_global_opts(
                title_opts=opts.TitleOpts(title="岗位数量与薪资趋势"),
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                xaxis_opts=opts.AxisOpts(type_="category"),
                yaxis_opts=opts.AxisOpts(name="岗位数"),
                datazoom_opts=opts.DataZoomOpts(),
            )
        )
        return chart

    async def _top_companies_chart(self) -> Bar:
        """招聘岗位最多的公司 Top15"""
        stmt = (
            select(Job.company, func.count(Job.id).label("count"))
            .group_by(Job.company)
            .order_by(func.count(Job.id).desc())
            .limit(15)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        companies = [r.company for r in rows]
        counts = [r.count for r in rows]

        chart = (
            Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="1000px", height="500px"))
            .add_xaxis(companies)
            .add_yaxis("岗位数量", counts)
            .set_global_opts(
                title_opts=opts.TitleOpts(title="招聘岗位数 Top 15 公司"),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30)),
            )
        )
        return chart

    async def _count_skills(self) -> Counter:
        """统计所有技能出现次数"""
        result = await self.db.execute(select(Job.skills).where(Job.skills.isnot(None)))
        rows = result.scalars().all()

        counter: Counter[str] = Counter()
        for skills_str in rows:
            for skill in skills_str.split(","):
                skill = skill.strip()
                if skill:
                    counter[skill] += 1
        return counter

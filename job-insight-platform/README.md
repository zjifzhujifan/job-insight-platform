# Job Insight Platform

招聘数据爬取、分析与可视化报告平台。项目提供 FastAPI 接口、Celery 异步任务、招聘站点爬虫、薪资/技能分析和 pyecharts HTML 报告生成能力。

## 技术栈

- FastAPI + Uvicorn
- SQLAlchemy Async + Alembic
- PostgreSQL / SQLite
- Redis + Celery + Celery Beat + Flower
- httpx + BeautifulSoup
- pyecharts
- pytest + pytest-asyncio

## 快速启动

详细启动、Swagger 操作和常见问题见：[docs/USAGE.md](docs/USAGE.md)。

复制环境变量模板并按需修改：

```bash
cp .env.example .env
```

使用 Docker Compose 启动完整环境：

```bash
docker compose up --build
```

服务地址：

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Flower: http://localhost:5555

## 数据库迁移

项目使用 Alembic 管理表结构：

```bash
alembic upgrade head
```

本地开发默认也可以使用 SQLite，生产环境建议使用 `.env.example` 中的 PostgreSQL 配置。

## 测试

安装依赖后运行：

```bash
pytest
```

当前测试覆盖认证、岗位查询、分析接口、任务接口、报告生成、爬虫基础逻辑和数据管道。

## 常用接口

- `POST /auth/register` 注册
- `POST /auth/login` 登录并获取 JWT
- `GET /jobs` 查询岗位列表
- `GET /analytics/salary` 城市薪资分析
- `GET /analytics/skills` 技能排行
- `GET /analytics/trends` 岗位趋势
- `POST /tasks` 创建爬取、分析或报告任务
- `POST /reports/generate` 同步生成 HTML 报告
- `GET /reports/list` 查看报告列表

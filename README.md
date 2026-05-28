# Job Insight Platform

招聘数据采集、分析与可视化报告平台。项目提供 FastAPI 接口、Celery 异步任务、招聘站点爬虫、薪资/技能分析和 pyecharts HTML 报告生成能力。

## 项目亮点

- 基于 FastAPI 实现用户注册登录、JWT 鉴权、岗位查询、任务管理、分析接口和报告下载。
- 使用 SQLAlchemy Async + Alembic 管理异步数据库访问和迁移，支持 SQLite 本地开发与 PostgreSQL 部署。
- 使用 Celery + Redis 实现爬虫、分析和报告生成异步任务，并支持任务状态追踪和失败重试。
- 封装多源爬虫管理器，支持 demo、Boss 直聘、前程无忧、拉勾等数据源接入。
- 实现岗位数据清洗、去重、技能标准化和批量入库。
- 使用 pyecharts 生成薪资城市分布、技能词云、岗位趋势、学历/经验分布等 HTML 报告。
- 使用 pytest 覆盖认证、岗位查询、分析接口、任务接口、报告生成和爬虫核心逻辑。

## 技术栈

FastAPI、SQLAlchemy Async、Alembic、Celery、Redis、PostgreSQL/SQLite、JWT、httpx、BeautifulSoup、pyecharts、pytest

## 启动命令速查

首次安装：

```bash
cd job-insight-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
```

启动 API：

```bash
cd job-insight-platform
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动 Celery Worker：

```bash
cd job-insight-platform
source .venv/bin/activate
celery -A app.worker.celery_app worker --loglevel=info --concurrency=4 -Q crawl,analysis,report,celery
```

访问地址：

```text
http://localhost:8000/docs
```

## 目录结构

```text
job-insight-platform/
  app/api/             API 路由
  app/models/          SQLAlchemy 数据模型
  app/schemas/         Pydantic 数据结构
  app/crawler/         爬虫、代理池和数据管道
  app/worker/          Celery 任务
  app/services/        认证、分析、报告服务
  alembic/             数据库迁移
  tests/               测试用例
  docs/                使用文档
```

## 快速启动

```bash
cd job-insight-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问：

```text
http://localhost:8000/docs
```

## 异步任务

本地创建爬虫任务前需要启动 Redis 和 Celery worker：

```bash
celery -A app.worker.celery_app worker --loglevel=info --concurrency=4 -Q crawl,analysis,report,celery
```

完整使用说明见 `job-insight-platform/docs/USAGE.md`。

## 测试

```bash
cd job-insight-platform
source .venv/bin/activate
pytest
```

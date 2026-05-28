# Job Insight Platform

招聘数据采集、分析与可视化报告平台。项目围绕招聘岗位数据构建后端服务，提供用户认证、岗位查询、异步爬虫任务、薪资分析、技能排行、趋势统计和 HTML 可视化报告生成能力。

## 项目定位

这个项目适合用于展示 Python 后端开发、异步任务、数据库建模、爬虫接入和数据分析能力。整体设计模拟一个招聘数据运营平台：通过爬虫或示例数据采集岗位信息，入库后提供 API 查询和分析接口，并生成可下载的可视化报告。

## 核心功能

| 模块 | 功能说明 |
| --- | --- |
| 用户认证 | 支持用户注册、登录、密码哈希和 JWT Bearer 鉴权 |
| 岗位查询 | 支持岗位分页查询、城市筛选、技能筛选和岗位详情 |
| 数据分析 | 支持城市薪资分析、技能出现频率排行、岗位数量与薪资趋势 |
| 异步任务 | 使用 Celery + Redis 管理爬虫、分析和报告生成任务 |
| 爬虫管理 | 支持 demo、Boss 直聘、前程无忧、拉勾等爬虫接入 |
| 数据管道 | 对岗位数据进行字段清洗、薪资校验、技能标准化和去重入库 |
| 报告生成 | 使用 pyecharts 生成薪资、技能、趋势、学历、经验、公司排行等 HTML 报告 |
| 接口文档 | 使用 FastAPI OpenAPI 文档，并内置本地 Swagger UI 静态资源 |
| 自动化测试 | 使用 pytest / pytest-asyncio 覆盖接口、服务、任务和爬虫核心逻辑 |

## 技术栈

- API 框架：FastAPI、Uvicorn
- 数据库：SQLAlchemy Async、Alembic、SQLite、PostgreSQL
- 异步任务：Celery、Redis、Celery Beat、Flower
- 认证：JWT、python-jose、passlib、bcrypt
- 爬虫：httpx、BeautifulSoup、fake-useragent、lxml
- 数据分析：Pandas、pyecharts
- 测试：pytest、pytest-asyncio、pytest-cov
- 部署：Docker、Docker Compose

## 系统架构

```text
FastAPI REST API
    |
    +-- Auth / Jobs / Analytics / Tasks / Reports
    |
    +-- SQLAlchemy Async
    |       |
    |       +-- SQLite / PostgreSQL
    |
    +-- Celery Task Queue
            |
            +-- Redis Broker
            +-- Crawler Task
            +-- Analysis Task
            +-- Report Task
```

## 数据流程

```text
创建爬虫任务
    |
    v
Celery Worker 执行爬虫
    |
    v
清洗字段 / 标准化技能 / 去重
    |
    v
写入 jobs 表
    |
    +----------------------+
    |                      |
    v                      v
岗位查询 API          薪资/技能/趋势分析
                           |
                           v
                    pyecharts HTML 报告
```

## 目录结构

```text
job-insight-platform/
  app/main.py                 FastAPI 应用入口
  app/api/                    认证、岗位、分析、任务、报告接口
  app/models/                 SQLAlchemy ORM 模型
  app/schemas/                Pydantic 请求/响应结构
  app/services/               认证、分析和报告服务
  app/crawler/                爬虫基类、爬虫实现、代理池和入库管道
  app/worker/                 Celery 应用和异步任务定义
  app/static/swagger-ui/      本地 Swagger UI 静态资源
  alembic/                    数据库迁移
  tests/                      自动化测试
  docs/USAGE.md               本地启动和 Swagger 操作说明
```

## 启动命令

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

访问接口文档：

```text
http://localhost:8000/docs
```

启动 Redis 后，再启动 Celery Worker：

```bash
cd job-insight-platform
source .venv/bin/activate
celery -A app.worker.celery_app worker --loglevel=info --concurrency=4 -Q crawl,analysis,report,celery
```

可选启动定时任务：

```bash
celery -A app.worker.celery_app beat --loglevel=info
```

## Docker Compose 启动

```bash
cd job-insight-platform
cp .env.example .env
docker compose up --build
```

默认服务地址：

```text
API:     http://localhost:8000
Swagger: http://localhost:8000/docs
Flower:  http://localhost:5555
```

## 常用接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/auth/register` | 注册用户 |
| POST | `/auth/login` | 登录并获取 JWT |
| GET | `/jobs` | 查询岗位列表 |
| GET | `/jobs/{job_id}` | 查询岗位详情 |
| GET | `/analytics/salary` | 城市薪资分析 |
| GET | `/analytics/skills` | 技能排行 |
| GET | `/analytics/trends` | 岗位趋势 |
| POST | `/tasks` | 创建爬虫/分析/报告异步任务 |
| GET | `/tasks` | 查询任务列表 |
| POST | `/reports/generate` | 同步生成 HTML 报告 |
| GET | `/reports/list` | 查看已生成报告 |

## 示例任务

创建 demo 爬虫任务：

```json
{
  "task_type": "crawl",
  "params": {
    "keyword": "Python",
    "city": "北京",
    "pages": 3,
    "spiders": ["demo"]
  }
}
```

真实招聘站点可能存在反爬限制，推荐先使用 `demo` 爬虫跑通任务流、数据入库和分析报告。

## 测试

```bash
cd job-insight-platform
source .venv/bin/activate
pytest
```

测试覆盖范围：

- 注册、登录和鉴权
- 岗位分页和筛选查询
- 薪资、技能和趋势分析
- 任务创建、查询、取消
- 报告生成和路径安全
- 爬虫数据结构、薪资解析、URL 构造、数据管道和代理池

## 配置说明

配置文件使用 `.env`，模板为 `.env.example`：

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/job_insight
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-change-in-production
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CRAWL_DELAY=2
MAX_CONCURRENT_REQUESTS=5
```

本地开发可以把 `DATABASE_URL` 改为：

```env
DATABASE_URL=sqlite+aiosqlite:///./job_insight.db
```

真实 `.env`、数据库文件和报告输出不应提交到仓库。

## 简历描述参考

基于 FastAPI 开发招聘数据洞察平台，实现 JWT 鉴权、岗位查询、异步爬虫任务、薪资/技能分析和 pyecharts 报告生成；使用 SQLAlchemy Async + Alembic 管理数据库结构，使用 Celery + Redis 实现任务队列和状态追踪，并编写 pytest 覆盖核心接口和爬虫逻辑。

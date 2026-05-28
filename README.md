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

## 项目亮点

- 后端采用典型分层结构，将 API、Schema、Model、Service、Crawler、Worker 拆开，方便维护和扩展。
- 使用 SQLAlchemy Async 构建异步数据库访问，支持 SQLite 本地演示和 PostgreSQL 部署。
- 使用 Celery + Redis 将爬虫、分析和报告生成从 API 请求中拆出，避免耗时任务阻塞接口。
- 爬虫层提供统一的 `BaseSpider`、`SpiderManager` 和入库管道，便于接入多个招聘网站或 demo 数据源。
- 报告模块使用 pyecharts 生成可视化 HTML 页面，适合直接展示薪资、技能、岗位趋势和公司排行。
- 项目包含 Docker Compose、Alembic 迁移和 pytest 测试，能够体现后端项目工程化能力。

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

## 关键实现

| 设计点 | 实现方式 | 项目价值 |
| --- | --- | --- |
| 认证鉴权 | 注册时使用密码哈希保存，登录后签发 JWT，接口通过 Bearer Token 识别用户 | 展示后端安全基础能力 |
| 异步数据库 | 使用 SQLAlchemy AsyncSession 和 Pydantic Schema 做数据读写与响应约束 | 适合高并发 API 场景 |
| 任务生命周期 | API 创建任务后写入任务表，Celery 执行并回写状态、结果和错误信息 | 便于追踪爬虫/报告任务 |
| 爬虫抽象 | 统一 Spider 输入参数、抓取结果、代理池、失败重试和数据管道 | 减少新增数据源成本 |
| 数据清洗 | 对薪资区间、城市、技能、公司、URL 和重复岗位做标准化处理 | 提高分析结果可信度 |
| 报告安全 | 下载报告时做路径检查，避免任意文件读取 | 展示接口安全意识 |

## 演示流程

1. 启动数据库、Redis、API 和 Celery Worker。
2. 打开 `http://localhost:8000/docs`，先调用注册和登录接口获取 Token。
3. 使用 `/tasks` 创建 demo 爬虫任务，等待任务状态变为完成。
4. 调用 `/jobs` 查看岗位列表，使用城市、技能等条件筛选。
5. 调用 `/analytics/salary`、`/analytics/skills`、`/analytics/trends` 查看分析结果。
6. 调用 `/reports/generate` 生成 HTML 报告，再通过 `/reports/download/{filename}` 下载查看。

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

## 任务类型说明

| task_type | 执行内容 | 典型参数 |
| --- | --- | --- |
| `crawl` | 执行招聘数据采集，清洗后写入数据库 | `keyword`、`city`、`pages`、`spiders` |
| `analyze` | 汇总岗位数量、薪资和技能统计 | 可根据业务扩展筛选条件 |
| `report` | 生成 pyecharts HTML 可视化报告 | 可扩展城市、岗位关键字、时间范围 |

任务状态会记录在任务表中，方便前端或 API 客户端轮询任务进度。

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

## 可用于简历展示的能力

| 能力方向 | README 中对应内容 |
| --- | --- |
| FastAPI 后端开发 | REST API、OpenAPI 文档、依赖注入、异常处理 |
| 数据库建模 | SQLAlchemy ORM、Alembic 迁移、异步查询 |
| 认证与安全 | JWT、密码哈希、接口鉴权、报告路径安全 |
| 异步任务 | Celery 队列、Redis Broker、任务状态追踪、失败重试 |
| 数据采集 | 爬虫基类、站点适配、代理池、数据清洗和去重 |
| 数据分析 | 薪资统计、技能排行、趋势分析和 HTML 报告 |
| 测试与部署 | pytest、Docker Compose、本地 Swagger UI |

## 后续优化方向

- 增加前端管理页面，展示任务状态、岗位列表、分析图表和报告下载。
- 对爬虫任务增加更细粒度的限速、代理质量评分和站点失败熔断。
- 增加岗位数据版本表，保留同一岗位在不同时间的薪资和描述变化。
- 增加定时分析任务，将热门技能、城市薪资和岗位趋势缓存为统计快照。
- 将报告模板做成可配置模块，支持按城市、岗位方向或时间范围生成专题报告。

## 简历描述参考

基于 FastAPI 开发招聘数据洞察平台，实现 JWT 鉴权、岗位查询、异步爬虫任务、薪资/技能分析和 pyecharts 报告生成；使用 SQLAlchemy Async + Alembic 管理数据库结构，使用 Celery + Redis 实现任务队列和状态追踪，并编写 pytest 覆盖核心接口和爬虫逻辑。

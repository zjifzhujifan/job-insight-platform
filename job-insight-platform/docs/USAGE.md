# 使用说明

本文档记录本项目在本机开发环境中的完整启动和使用流程。

## 1. 当前推荐配置

本地开发推荐使用 SQLite，避免必须启动 PostgreSQL。

确认 `.env` 中数据库配置为：

```env
DATABASE_URL=sqlite+aiosqlite:///./job_insight.db
```

Redis 仍然需要启动，因为 Celery 异步任务依赖 Redis 队列：

```env
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

## 2. 启动 Redis

如果没有安装 Redis：

```bash
brew install redis
```

启动 Redis：

```bash
brew services start redis
```

验证 Redis：

```bash
redis-cli ping
```

正常返回：

```text
PONG
```

## 3. 安装依赖

进入项目目录：

```bash
cd /Users/zhujifan/job-insight-platform
source .venv/bin/activate
```

安装依赖：

```bash
PIP_USER=false pip install --no-user -r requirements.txt
```

如果遇到 Python 证书问题，可以使用：

```bash
PIP_USER=false pip install --no-user --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

## 4. 初始化数据库

执行迁移建表：

```bash
alembic upgrade head
```

成功后会生成或更新本地数据库文件：

```text
job_insight.db
```

## 5. 启动 API 服务

启动 FastAPI：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

打开接口文档：

```text
http://localhost:8000/docs
```

如果提示端口已占用：

```text
ERROR: [Errno 48] Address already in use
```

可以换端口启动：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

然后访问：

```text
http://localhost:8001/docs
```

## 6. 启动 Celery Worker

另开一个终端，进入项目并激活虚拟环境：

```bash
cd /Users/zhujifan/job-insight-platform
source .venv/bin/activate
```

必须监听项目使用的所有队列：

```bash
celery -A app.worker.celery_app worker --loglevel=info --concurrency=4 -Q crawl,analysis,report,celery
```

看到下面内容表示 worker 正常：

```text
Connected to redis://localhost:6379/1
celery@... ready.
```

如果出现：

```text
Cannot connect to redis://localhost:6379/1
```

说明 Redis 没启动，先执行：

```bash
brew services start redis
```

## 7. 启动 Celery Beat

Celery Beat 是定时任务调度器。手动在 Swagger 里创建任务时不是必须，但可以启动。

另开一个终端：

```bash
cd /Users/zhujifan/job-insight-platform
source .venv/bin/activate
celery -A app.worker.celery_app beat --loglevel=info
```

看到下面内容表示正常：

```text
beat: Starting...
```

## 8. Swagger 使用流程

### 8.1 注册用户

打开：

```text
POST /auth/register
```

请求体示例：

```json
{
  "username": "admin",
  "email": "admin@example.com",
  "password": "123456"
}
```

成功状态码：

```text
201
```

如果提示用户名或邮箱已存在，换一个用户名或邮箱。

### 8.2 登录获取 Token

打开：

```text
POST /auth/login
```

填写表单：

```text
username: admin
password: 123456
```

其他字段可以不填。

成功返回：

```json
{
  "access_token": "一长串 token",
  "token_type": "bearer"
}
```

### 8.3 授权

点击 Swagger 页面右上角：

```text
Authorize
```

填入：

```text
Bearer 你的access_token
```

示例：

```text
Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

点击 `Authorize`，再点击 `Close`。

## 9. 创建 demo 爬虫任务

打开：

```text
POST /tasks
```

请求体：

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

成功返回状态码：

```text
201
```

返回结果里会有：

```json
{
  "id": 6,
  "celery_task_id": "...",
  "task_type": "crawl",
  "status": "pending"
}
```

记录这里的 `id`，后续查询任务状态要用。

## 10. 查询任务状态

打开：

```text
GET /tasks/{task_id}
```

填入任务 ID，例如：

```text
6
```

成功执行后，状态会从：

```text
pending
```

变成：

```text
running
```

最后变成：

```text
completed
```

成功任务示例：

```json
{
  "id": 6,
  "task_type": "crawl",
  "status": "completed",
  "result": "{\"crawled\": 27, \"saved\": 10}",
  "error_message": null
}
```

如果失败，会看到：

```json
{
  "status": "failed",
  "error_message": "具体错误信息"
}
```

## 11. 查看岗位数据

任务完成后打开：

```text
GET /jobs
```

常用参数：

```text
page: 1
page_size: 20
city: 北京
skill: python
```

可以先只填：

```text
page: 1
page_size: 20
```

如果有数据，会返回：

```json
{
  "total": 107,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "title": "Python开发工程师",
      "company": "...",
      "city": "北京"
    }
  ]
}
```

## 12. 查看分析结果

岗位数据存在后，可以使用：

```text
GET /analytics/salary
GET /analytics/skills
GET /analytics/trends
```

## 13. 生成报告

打开：

```text
POST /reports/generate
```

成功返回：

```json
{
  "filename": "report_20260527_191000.html",
  "download_url": "/reports/download/report_20260527_191000.html"
}
```

浏览器打开：

```text
http://localhost:8000/reports/download/report_20260527_191000.html
```

如果 API 启动在 8001，则使用：

```text
http://localhost:8001/reports/download/report_20260527_191000.html
```

## 14. 常见问题

### 14.1 `/docs` 页面空白

本项目已经改成本地 Swagger UI 静态资源。如果浏览器仍然空白，强制刷新：

```text
Cmd + Shift + R
```

或者打开无痕窗口访问。

### 14.2 注册或登录返回 500

通常是数据库配置不对或未建表。

检查 `.env`：

```env
DATABASE_URL=sqlite+aiosqlite:///./job_insight.db
```

执行：

```bash
alembic upgrade head
```

然后重启 API。

### 14.3 任务一直是 pending

通常是 worker 没监听 `crawl` 队列。

错误启动方式：

```bash
celery -A app.worker.celery_app worker --loglevel=info --concurrency=4
```

正确启动方式：

```bash
celery -A app.worker.celery_app worker --loglevel=info --concurrency=4 -Q crawl,analysis,report,celery
```

### 14.4 Celery 无法连接 Redis

报错：

```text
Cannot connect to redis://localhost:6379/1
```

解决：

```bash
brew services start redis
redis-cli ping
```

确认返回：

```text
PONG
```

### 14.5 8000 端口被占用

换端口：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

或停止原来的 Uvicorn 终端后重新启动。

## 15. 推荐启动顺序总结

每次本地开发按这个顺序：

```bash
cd /Users/zhujifan/job-insight-platform
source .venv/bin/activate
brew services start redis
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

另开 worker 终端：

```bash
cd /Users/zhujifan/job-insight-platform
source .venv/bin/activate
celery -A app.worker.celery_app worker --loglevel=info --concurrency=4 -Q crawl,analysis,report,celery
```

可选，另开 beat 终端：

```bash
cd /Users/zhujifan/job-insight-platform
source .venv/bin/activate
celery -A app.worker.celery_app beat --loglevel=info
```

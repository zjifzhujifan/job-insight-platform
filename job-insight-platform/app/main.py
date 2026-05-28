from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api import auth, jobs, analytics, tasks, reports


SWAGGER_UI_DIR = Path(__file__).resolve().parent / "static" / "swagger-ui"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Job Insight Platform",
    description="招聘数据爬取、分析与可视化平台",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.mount("/static/swagger-ui", StaticFiles(directory=SWAGGER_UI_DIR), name="swagger-ui")

# 注册路由
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(analytics.router)
app.include_router(tasks.router)
app.include_router(reports.router)


@app.get("/health", tags=["健康检查"])
async def health_check():
    return {"status": "ok"}


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js?v=5.17.14",
        swagger_css_url="/static/swagger-ui/swagger-ui.css?v=5.17.14",
        swagger_favicon_url="/static/swagger-ui/favicon-32x32.png?v=5.17.14",
    )


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()

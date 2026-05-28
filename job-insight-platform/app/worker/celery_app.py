from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "job_insight",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    # 序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,

    # 重试策略
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,
    task_max_retries=3,

    # 任务路由：不同类型任务分配到不同队列
    task_routes={
        "app.worker.tasks.run_crawl": {"queue": "crawl"},
        "app.worker.tasks.run_analysis": {"queue": "analysis"},
        "app.worker.tasks.run_report": {"queue": "report"},
    },

    # 定时任务（Celery Beat）
    beat_schedule={
        "scheduled-crawl": {
            "task": "app.worker.tasks.run_crawl",
            "schedule": crontab(hour=2, minute=0, day_of_week="1,4"),  # 每周一、四凌晨2点
            "args": [{"keyword": "Python", "pages": 5}],
        },
    },
)

# 自动发现任务
celery_app.autodiscover_tasks(["app.worker"])

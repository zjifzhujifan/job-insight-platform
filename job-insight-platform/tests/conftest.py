import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base, get_db
from app.main import app
from app.services.auth import hash_password
from app.models.user import User
from app.models.job import Job

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient, db_session: AsyncSession):
    """带认证的测试客户端"""
    user = User(username="testuser", email="test@example.com", hashed_password=hash_password("testpass"))
    db_session.add(user)
    await db_session.commit()

    resp = await client.post("/auth/login", data={"username": "testuser", "password": "testpass"})
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest_asyncio.fixture
async def seed_jobs(db_session: AsyncSession):
    """插入测试岗位数据"""
    jobs = [
        Job(title="Python后端开发", company="字节跳动", city="北京",
            salary_min=20000, salary_max=35000, experience="3-5年",
            education="本科", skills="python, fastapi, redis, docker", source="demo"),
        Job(title="Python工程师", company="阿里巴巴", city="杭州",
            salary_min=25000, salary_max=40000, experience="3-5年",
            education="本科", skills="python, django, mysql, celery", source="demo"),
        Job(title="数据分析师", company="腾讯", city="深圳",
            salary_min=15000, salary_max=25000, experience="1-3年",
            education="硕士", skills="python, pandas, sql, tableau", source="demo"),
        Job(title="爬虫工程师", company="美团", city="北京",
            salary_min=18000, salary_max=30000, experience="1-3年",
            education="本科", skills="python, scrapy, redis, mongodb", source="demo"),
        Job(title="AI算法工程师", company="百度", city="北京",
            salary_min=30000, salary_max=50000, experience="3-5年",
            education="硕士", skills="python, pytorch, tensorflow, docker", source="demo"),
        Job(title="全栈开发", company="快手", city="北京",
            salary_min=22000, salary_max=38000, experience="3-5年",
            education="本科", skills="python, vue, react, postgresql", source="demo"),
        Job(title="DevOps工程师", company="网易", city="杭州",
            salary_min=20000, salary_max=35000, experience="3-5年",
            education="本科", skills="python, docker, kubernetes, linux", source="demo"),
        Job(title="Python开发", company="小红书", city="上海",
            salary_min=18000, salary_max=32000, experience="1-3年",
            education="本科", skills="python, fastapi, mysql, redis", source="demo"),
        Job(title="后端开发", company="滴滴", city="北京",
            salary_min=20000, salary_max=35000, experience="3-5年",
            education="本科", skills="python, go, kafka, elasticsearch", source="demo"),
        Job(title="数据工程师", company="拼多多", city="上海",
            salary_min=25000, salary_max=45000, experience="3-5年",
            education="本科", skills="python, spark, hadoop, sql", source="demo"),
    ]
    for job in jobs:
        db_session.add(job)
    await db_session.commit()
    return jobs

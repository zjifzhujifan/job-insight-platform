import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_salary_analysis_unauthorized(client: AsyncClient):
    resp = await client.get("/analytics/salary")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_salary_analysis(auth_client: AsyncClient, seed_jobs):
    resp = await auth_client.get("/analytics/salary")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # 验证数据结构
    item = data[0]
    assert "city" in item
    assert "avg_salary" in item
    assert "job_count" in item
    assert item["job_count"] > 0
    assert item["avg_salary"] > 0


@pytest.mark.asyncio
async def test_skill_ranking_unauthorized(client: AsyncClient):
    resp = await client.get("/analytics/skills")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_skill_ranking(auth_client: AsyncClient, seed_jobs):
    resp = await auth_client.get("/analytics/skills")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0

    item = data[0]
    assert "skill" in item
    assert "count" in item
    assert "percentage" in item

    # python 应该排名靠前
    skill_names = [s["skill"] for s in data]
    assert "python" in skill_names


@pytest.mark.asyncio
async def test_skill_ranking_limit(auth_client: AsyncClient, seed_jobs):
    resp = await auth_client.get("/analytics/skills", params={"limit": 5})
    data = resp.json()
    assert len(data) <= 5


@pytest.mark.asyncio
async def test_trends(auth_client: AsyncClient, seed_jobs):
    resp = await auth_client.get("/analytics/trends")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

    if data:
        item = data[0]
        assert "date" in item
        assert "job_count" in item
        assert "avg_salary" in item

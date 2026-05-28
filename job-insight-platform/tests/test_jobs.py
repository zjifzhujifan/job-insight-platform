import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job


@pytest.mark.asyncio
async def test_list_jobs_unauthorized(client: AsyncClient):
    resp = await client.get("/jobs")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_jobs(auth_client: AsyncClient, seed_jobs):
    resp = await auth_client.get("/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 10
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert len(data["items"]) == 10


@pytest.mark.asyncio
async def test_list_jobs_pagination(auth_client: AsyncClient, seed_jobs):
    resp = await auth_client.get("/jobs", params={"page": 1, "page_size": 3})
    data = resp.json()
    assert data["total"] == 10
    assert len(data["items"]) == 3
    assert data["page"] == 1

    resp2 = await auth_client.get("/jobs", params={"page": 2, "page_size": 3})
    data2 = resp2.json()
    assert len(data2["items"]) == 3
    # 确保第二页和第一页的数据不同
    ids_page1 = {item["id"] for item in data["items"]}
    ids_page2 = {item["id"] for item in data2["items"]}
    assert ids_page1.isdisjoint(ids_page2)


@pytest.mark.asyncio
async def test_list_jobs_filter_city(auth_client: AsyncClient, seed_jobs):
    resp = await auth_client.get("/jobs", params={"city": "北京"})
    data = resp.json()
    expected_total = sum(1 for job in seed_jobs if job.city == "北京")
    assert data["total"] == expected_total
    for item in data["items"]:
        assert item["city"] == "北京"


@pytest.mark.asyncio
async def test_list_jobs_filter_skill(auth_client: AsyncClient, seed_jobs):
    resp = await auth_client.get("/jobs", params={"skill": "fastapi"})
    data = resp.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert "fastapi" in item["skills"].lower()


@pytest.mark.asyncio
async def test_list_jobs_filter_city_and_skill(auth_client: AsyncClient, seed_jobs):
    resp = await auth_client.get("/jobs", params={"city": "北京", "skill": "python"})
    data = resp.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["city"] == "北京"
        assert "python" in item["skills"].lower()


@pytest.mark.asyncio
async def test_get_job_detail(auth_client: AsyncClient, seed_jobs):
    # 先获取列表拿到一个 id
    resp = await auth_client.get("/jobs", params={"page_size": 1})
    job_id = resp.json()["items"][0]["id"]

    resp = await auth_client.get(f"/jobs/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == job_id
    assert "title" in data
    assert "company" in data


@pytest.mark.asyncio
async def test_get_job_not_found(auth_client: AsyncClient):
    resp = await auth_client.get("/jobs/99999")
    assert resp.status_code == 404

import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_crawl_task(auth_client: AsyncClient):
    mock_result = MagicMock()
    mock_result.id = "fake-celery-id-001"

    with patch("app.api.tasks.dispatch_task") as mock_dispatch:
        mock_dispatch.delay.return_value = mock_result
        resp = await auth_client.post("/tasks", json={
            "task_type": "crawl",
            "params": {"keyword": "Python", "pages": 3},
        })

    assert resp.status_code == 201
    data = resp.json()
    assert data["task_type"] == "crawl"
    assert data["celery_task_id"] == "fake-celery-id-001"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_create_analysis_task(auth_client: AsyncClient):
    mock_result = MagicMock()
    mock_result.id = "fake-celery-id-002"

    with patch("app.api.tasks.dispatch_task") as mock_dispatch:
        mock_dispatch.delay.return_value = mock_result
        resp = await auth_client.post("/tasks", json={
            "task_type": "analyze",
        })

    assert resp.status_code == 201
    assert resp.json()["task_type"] == "analyze"


@pytest.mark.asyncio
async def test_create_report_task(auth_client: AsyncClient):
    mock_result = MagicMock()
    mock_result.id = "fake-celery-id-003"

    with patch("app.api.tasks.dispatch_task") as mock_dispatch:
        mock_dispatch.delay.return_value = mock_result
        resp = await auth_client.post("/tasks", json={
            "task_type": "report",
        })

    assert resp.status_code == 201
    assert resp.json()["task_type"] == "report"


@pytest.mark.asyncio
async def test_list_tasks(auth_client: AsyncClient):
    # 先创建几个任务
    mock_result = MagicMock()
    mock_result.id = "fake-list-001"
    with patch("app.api.tasks.dispatch_task") as mock_dispatch:
        mock_dispatch.delay.return_value = mock_result
        await auth_client.post("/tasks", json={"task_type": "crawl"})

    mock_result.id = "fake-list-002"
    with patch("app.api.tasks.dispatch_task") as mock_dispatch:
        mock_dispatch.delay.return_value = mock_result
        await auth_client.post("/tasks", json={"task_type": "analyze"})

    resp = await auth_client.get("/tasks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_list_tasks_filter_status(auth_client: AsyncClient):
    mock_result = MagicMock()
    mock_result.id = "fake-filter-001"
    with patch("app.api.tasks.dispatch_task") as mock_dispatch:
        mock_dispatch.delay.return_value = mock_result
        await auth_client.post("/tasks", json={"task_type": "crawl"})

    resp = await auth_client.get("/tasks", params={"status": "pending"})
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["status"] == "pending"


@pytest.mark.asyncio
async def test_get_task_detail(auth_client: AsyncClient):
    mock_result = MagicMock()
    mock_result.id = "fake-detail-001"
    with patch("app.api.tasks.dispatch_task") as mock_dispatch:
        mock_dispatch.delay.return_value = mock_result
        resp = await auth_client.post("/tasks", json={"task_type": "crawl"})
        task_id = resp.json()["id"]

    resp = await auth_client.get(f"/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == task_id


@pytest.mark.asyncio
async def test_get_task_not_found(auth_client: AsyncClient):
    resp = await auth_client.get("/tasks/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cancel_task(auth_client: AsyncClient):
    mock_result = MagicMock()
    mock_result.id = "fake-cancel-001"
    with patch("app.api.tasks.dispatch_task") as mock_dispatch:
        mock_dispatch.delay.return_value = mock_result
        resp = await auth_client.post("/tasks", json={"task_type": "crawl"})
        task_id = resp.json()["id"]

    with patch("app.api.tasks.celery_app") as mock_celery:
        resp = await auth_client.delete(f"/tasks/{task_id}")
        assert resp.status_code == 204


@pytest.mark.asyncio
async def test_cancel_task_not_found(auth_client: AsyncClient):
    with patch("app.api.tasks.celery_app"):
        resp = await auth_client.delete("/tasks/99999")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tasks_unauthorized(client: AsyncClient):
    resp = await client.get("/tasks")
    assert resp.status_code == 401

    resp = await client.post("/tasks", json={"task_type": "crawl"})
    assert resp.status_code == 401

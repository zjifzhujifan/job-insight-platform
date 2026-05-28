"""报告模块测试"""

import os
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from app.services.report import REPORTS_DIR


@pytest.mark.asyncio
async def test_generate_report_unauthorized(client: AsyncClient):
    resp = await client.post("/reports/generate")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_reports_unauthorized(client: AsyncClient):
    resp = await client.get("/reports/list")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_reports_empty(auth_client: AsyncClient):
    resp = await auth_client.get("/reports/list")
    assert resp.status_code == 200
    data = resp.json()
    assert "reports" in data


@pytest.mark.asyncio
async def test_download_report_not_found(auth_client: AsyncClient):
    resp = await auth_client.get("/reports/download/nonexistent.html")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_report_path_traversal(auth_client: AsyncClient):
    resp = await auth_client.get("/reports/download/%2E%2E/%2E%2E/%2E%2E/etc/passwd")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_generate_report(auth_client: AsyncClient, seed_jobs):
    """测试完整报告生成流程"""
    resp = await auth_client.post("/reports/generate")
    assert resp.status_code == 200
    data = resp.json()
    assert "filename" in data
    assert data["filename"].endswith(".html")
    assert "download_url" in data

    # 验证文件确实存在
    filepath = os.path.join(REPORTS_DIR, data["filename"])
    assert os.path.exists(filepath)

    # 清理
    os.remove(filepath)


@pytest.mark.asyncio
async def test_download_generated_report(auth_client: AsyncClient, seed_jobs):
    """生成后下载报告"""
    gen_resp = await auth_client.post("/reports/generate")
    filename = gen_resp.json()["filename"]

    resp = await auth_client.get(f"/reports/download/{filename}")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]

    # 清理
    filepath = os.path.join(REPORTS_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)

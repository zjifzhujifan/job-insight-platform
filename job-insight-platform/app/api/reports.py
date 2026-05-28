import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.report import ReportGenerator, REPORTS_DIR

router = APIRouter(prefix="/reports", tags=["报告"])


@router.post("/generate")
async def generate_report(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """同步生成报告（小数据量时直接调用，大数据量建议走异步任务）"""
    generator = ReportGenerator(db)
    filename = await generator.generate()
    return {"filename": filename, "download_url": f"/reports/download/{filename}"}


@router.get("/download/{filename:path}")
async def download_report(
    filename: str,
    _current_user: User = Depends(get_current_user),
):
    """下载报告 HTML 文件"""
    # 防止路径穿越
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="非法文件名")

    filepath = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="报告不存在")

    return FileResponse(filepath, media_type="text/html", filename=filename)


@router.get("/list")
async def list_reports(
    _current_user: User = Depends(get_current_user),
):
    """列出所有已生成的报告"""
    if not os.path.exists(REPORTS_DIR):
        return {"reports": []}

    files = sorted(
        [f for f in os.listdir(REPORTS_DIR) if f.endswith(".html")],
        reverse=True,
    )
    return {
        "reports": [
            {
                "filename": f,
                "download_url": f"/reports/download/{f}",
                "size_kb": round(os.path.getsize(os.path.join(REPORTS_DIR, f)) / 1024, 1),
            }
            for f in files
        ]
    }

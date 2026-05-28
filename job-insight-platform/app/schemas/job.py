from datetime import datetime
from pydantic import BaseModel


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    city: str
    salary_min: int | None = None
    salary_max: int | None = None
    experience: str | None = None
    education: str | None = None
    skills: str | None = None
    source: str
    crawled_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[JobResponse]


class SalaryAnalysis(BaseModel):
    city: str
    avg_salary: float
    median_salary: float
    job_count: int


class SkillRanking(BaseModel):
    skill: str
    count: int
    percentage: float


class TrendData(BaseModel):
    date: str
    job_count: int
    avg_salary: float

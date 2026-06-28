from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.financial import FinancialStatement


ParseJobStatus = Literal["queued", "running", "completed", "failed"]


class ParseJobSnapshot(BaseModel):
    job_id: str
    status: ParseJobStatus
    progress: int = Field(ge=0, le=100)
    stage: str
    message: str
    file_name: str | None = None
    statement: FinancialStatement | None = None
    error: str | None = None

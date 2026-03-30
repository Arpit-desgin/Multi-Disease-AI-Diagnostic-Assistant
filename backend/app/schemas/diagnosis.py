from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DiagnosisRecordResponse(BaseModel):
    id: UUID
    disease: str
    prediction: str
    confidence: float
    risk_level: str
    stage1_result: str | None
    stage2_result: str | None
    gradcam_image_url: str | None
    original_image_url: str | None
    report_explanation: dict | None
    created_at: datetime

    class Config:
        from_attributes = True


class DiagnosisHistoryPage(BaseModel):
    items: list[DiagnosisRecordResponse]
    page: int
    total: int

from pydantic import BaseModel
from uuid import UUID
from typing import Literal


class DiagnosisRequest(BaseModel):
    sessionId: UUID


class DiagnosisResponse(BaseModel):
    prediction: str
    confidence: float
    riskBadge: Literal["LOW", "MEDIUM", "HIGH"]
    gradcamUrl: str | None
    stage1: str | None
    stage2: str | None

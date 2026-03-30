import uuid

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DiagnosisRecord(Base):
    __tablename__ = "diagnosis_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=True
    )
    disease: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    prediction: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    stage1_result: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stage2_result: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gradcam_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    original_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    report_explanation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

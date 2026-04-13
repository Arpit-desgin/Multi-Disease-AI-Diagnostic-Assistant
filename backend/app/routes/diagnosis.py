"""
diagnosis.py — FastAPI routes for all disease diagnosis endpoints.

All prediction functions now come from ml_service which returns a flat,
frontend-ready dict. No post-processing needed here.
"""
from __future__ import annotations

import base64
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.models.diagnosis import DiagnosisRecord
from app.models.user import User
from app.rate_limiter import limiter
from app.schemas.diagnosis import DiagnosisHistoryPage, DiagnosisRecordResponse
from app.services.gradcam_service import generate_gradcam_for_disease
from app.services.ml_service import (
    get_loaded_model_for_disease,
    get_model_status,
    predict_diabetic_retinopathy,
    predict_lung_cancer,
    predict_skin_disease,
)
from app.services.storage_service import upload_to_cloudinary
from app.utils.auth_utils import get_current_user, get_optional_user
from app.utils.file_utils import sanitize_string, validate_image_upload

logger = logging.getLogger("app.diagnosis_routes")

router = APIRouter(prefix="/diagnosis")


# ─── DB helpers ───────────────────────────────────────────────────────────────

async def _get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        return session


async def _maybe_save_record(
    *,
    db: AsyncSession,
    user: User | None,
    disease: str,
    result: dict,
    gradcam_b64: str | None,
    image_bytes: bytes,
) -> None:
    if not user:
        return

    folder       = f"medintel/{user.id}/{disease}"
    original_url = upload_to_cloudinary(image_bytes, folder=folder, public_id="original")

    gradcam_url: str | None = None
    if gradcam_b64:
        try:
            gradcam_url = upload_to_cloudinary(
                base64.b64decode(gradcam_b64), folder=folder, public_id="gradcam"
            )
        except Exception:
            pass

    row = DiagnosisRecord(
        user_id=user.id,
        disease=disease,
        prediction=result.get("prediction", ""),
        confidence=float(result.get("confidence", 0.0)),
        risk_level=result.get("risk_level", "UNKNOWN"),
        stage1_result=result.get("stage1_result"),
        stage2_result=result.get("stage2_result"),
        gradcam_image_url=gradcam_url,
        original_image_url=original_url,
        report_explanation=None,
    )
    db.add(row)
    await db.commit()


# ─── Shared helpers ───────────────────────────────────────────────────────────

async def _read_and_validate(image: UploadFile) -> bytes:
    if not image or not image.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is required")
    image_bytes = await image.read()
    try:
        validate_image_upload(image, image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return image_bytes


def _attempt_gradcam(disease_slug: str, image_bytes: bytes) -> tuple[str | None, str | None]:
    try:
        model, kind = get_loaded_model_for_disease(disease_slug)
        if model and kind:
            b64, hint = generate_gradcam_for_disease(
                disease_slug, image_bytes, model=model, model_kind=kind
            )
            return b64, hint
    except Exception as exc:
        logger.warning(f"[ROUTE] Grad-CAM failed for {disease_slug}: {exc}")
    return None, None


# ─── Lung Cancer ──────────────────────────────────────────────────────────────

@router.post("/lung-cancer")
@limiter.limit("10/minute")
async def lung_cancer_diagnosis(
    request: Request,
    image: UploadFile = File(...),
    report_text: str | None = Form(default=None),
    user: User | None = Depends(get_optional_user),
):
    logger.info("[ROUTE] 🫁 Lung Cancer")
    image_bytes = await _read_and_validate(image)
    sanitize_string(report_text)

    try:
        result = predict_lung_cancer(image_bytes)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("[ROUTE] Lung prediction error", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")

    gradcam_b64, gradcam_hint = _attempt_gradcam("lung-cancer", image_bytes)

    try:
        db = await _get_db_session()
        await _maybe_save_record(
            db=db, user=user, disease="lung_cancer",
            result=result, gradcam_b64=gradcam_b64, image_bytes=image_bytes,
        )
    except Exception as exc:
        logger.warning(f"[ROUTE] DB save failed: {exc}")

    logger.info(f"[ROUTE] ✅ Lung: {result['prediction']} ({result['confidence']}%)")
    return {**result, "gradcam_image": gradcam_b64, "gradcam_regions": gradcam_hint}


# ─── Skin Disease ─────────────────────────────────────────────────────────────

@router.post("/skin-disease")
@limiter.limit("10/minute")
async def skin_disease_diagnosis(
    request: Request,
    image: UploadFile = File(...),
    report_text: str | None = Form(default=None),
    user: User | None = Depends(get_optional_user),
):
    logger.info("[ROUTE] 🔍 Skin Disease")
    image_bytes = await _read_and_validate(image)
    sanitize_string(report_text)

    try:
        result = predict_skin_disease(image_bytes)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("[ROUTE] Skin prediction error", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")

    gradcam_b64, gradcam_hint = _attempt_gradcam("skin-disease", image_bytes)

    try:
        db = await _get_db_session()
        await _maybe_save_record(
            db=db, user=user, disease="skin_disease",
            result=result, gradcam_b64=gradcam_b64, image_bytes=image_bytes,
        )
    except Exception as exc:
        logger.warning(f"[ROUTE] DB save failed: {exc}")

    logger.info(f"[ROUTE] ✅ Skin: {result['prediction']} ({result['confidence']}%)")
    return {**result, "gradcam_image": gradcam_b64, "gradcam_regions": gradcam_hint}


# ─── Diabetic Retinopathy ─────────────────────────────────────────────────────

@router.post("/diabetic-retinopathy")
@limiter.limit("10/minute")
async def diabetic_retinopathy_diagnosis(
    request: Request,
    image: UploadFile = File(...),
    report_text: str | None = Form(default=None),
    user: User | None = Depends(get_optional_user),
):
    logger.info("[ROUTE] 👁️  Diabetic Retinopathy")
    image_bytes = await _read_and_validate(image)
    sanitize_string(report_text)

    try:
        result = predict_diabetic_retinopathy(image_bytes)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("[ROUTE] DR prediction error", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")

    gradcam_b64, gradcam_hint = _attempt_gradcam("diabetic-retinopathy", image_bytes)

    try:
        db = await _get_db_session()
        await _maybe_save_record(
            db=db, user=user, disease="diabetic_retinopathy",
            result=result, gradcam_b64=gradcam_b64, image_bytes=image_bytes,
        )
    except Exception as exc:
        logger.warning(f"[ROUTE] DB save failed: {exc}")

    logger.info(f"[ROUTE] ✅ DR: {result['prediction']} ({result['confidence']}%)")
    return {**result, "gradcam_image": gradcam_b64, "gradcam_regions": gradcam_hint}


# ─── Grad-CAM standalone ──────────────────────────────────────────────────────

@router.post("/gradcam")
async def gradcam_only(
    disease: str = Form(...),
    image: UploadFile = File(...),
):
    logger.info(f"[ROUTE] 🎨 Grad-CAM for disease={disease}")
    image_bytes = await _read_and_validate(image)

    try:
        model, kind = get_loaded_model_for_disease(disease)
        if not model or not kind:
            raise HTTPException(status_code=503, detail=f"Model not available for disease: {disease}")
        b64, hint = generate_gradcam_for_disease(disease, image_bytes, model=model, model_kind=kind)
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("[ROUTE] Grad-CAM error", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Grad-CAM failed: {exc}")

    if not b64:
        raise HTTPException(status_code=503, detail=hint or "Grad-CAM generation failed")

    logger.info(f"[ROUTE] ✅ Grad-CAM done: {hint}")
    return {"gradcam_image": b64, "region_hint": hint}


# ─── History / CRUD ───────────────────────────────────────────────────────────

@router.get("/history", response_model=DiagnosisHistoryPage)
async def diagnosis_history(
    page: int = 1,
    disease: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be >= 1")
    page_size = 10
    stmt = select(DiagnosisRecord).where(DiagnosisRecord.user_id == current_user.id)
    if disease:
        stmt = stmt.where(DiagnosisRecord.disease == disease)
    stmt = stmt.order_by(DiagnosisRecord.created_at.desc())

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt  = stmt.offset((page - 1) * page_size).limit(page_size)
    items_result = await db.execute(stmt)
    records = items_result.scalars().all()

    return DiagnosisHistoryPage(
        items=[DiagnosisRecordResponse.model_validate(r) for r in records],
        page=page,
        total=total,
    )


@router.get("/{diagnosis_id}", response_model=DiagnosisRecordResponse)
async def get_diagnosis(
    diagnosis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt   = select(DiagnosisRecord).where(
        DiagnosisRecord.id == diagnosis_id,
        DiagnosisRecord.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Diagnosis record not found")
    return DiagnosisRecordResponse.model_validate(record)


@router.delete("/{diagnosis_id}")
async def delete_diagnosis(
    diagnosis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt   = select(DiagnosisRecord).where(
        DiagnosisRecord.id == diagnosis_id,
        DiagnosisRecord.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Diagnosis record not found")
    await db.delete(record)
    await db.commit()
    return {"message": "Record deleted"}


# ─── Model status (internal) ──────────────────────────────────────────────────

@router.get("/models/status")
async def models_status():
    return get_model_status()
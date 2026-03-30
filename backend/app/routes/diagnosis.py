import base64
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.diagnosis import DiagnosisRecord
from app.models.user import User
from app.rate_limiter import limiter
from app.schemas.diagnosis import DiagnosisHistoryPage, DiagnosisRecordResponse
from app.services.gradcam_service import generate_gradcam_for_disease
from app.services.ml_service import get_loaded_model_for_disease
from app.services.ml_service import predict_diabetic_retinopathy, predict_lung_cancer, predict_skin_disease
from app.services.storage_service import upload_to_cloudinary
from app.utils.auth_utils import get_current_user, get_optional_user
from app.utils.file_utils import sanitize_string, validate_image_upload

router = APIRouter(prefix="/diagnosis")

async def _maybe_save_record(
    *,
    db: AsyncSession,
    user: User | None,
    disease: str,
    prediction: dict,
    gradcam_image_b64: str | None,
    original_image_bytes: bytes,
    report_explanation: dict | None = None,
) -> None:
    if not user:
        return

    # Extract common fields from prediction dicts
    disease_key = disease
    if disease_key == "lung_cancer":
        pred_text = str(prediction.get("prediction"))
        confidence = float(prediction.get("confidence", 0.0))
        risk_level = str(prediction.get("risk_level", "UNKNOWN"))
        stage1 = None
        stage2 = None
    elif disease_key == "skin_disease":
        stage1 = prediction.get("stage1_result", {}) or {}
        stage2 = prediction.get("stage2_result", {}) or {}
        pred_text = str(stage1.get("label") or "Skin disease assessment")
        confidence = float(prediction.get("confidence", stage1.get("confidence", 0.0)))
        risk_level = "UNKNOWN"
        stage1 = stage1.get("label")
        stage2 = stage2.get("label") if stage2 else None
    elif disease_key == "diabetic_retinopathy":
        stage1 = prediction.get("stage1_result", {}) or {}
        stage2 = prediction.get("stage2_result", {}) or {}
        pred_text = str(stage1.get("label") or "Retinopathy assessment")
        confidence = float(prediction.get("confidence", stage1.get("confidence", 0.0)))
        risk_level = "UNKNOWN"
        stage1 = stage1.get("label")
        stage2 = stage2.get("label") if stage2 else None
    else:
        pred_text = "Diagnosis"
        confidence = 0.0
        risk_level = "UNKNOWN"
        stage1 = None
        stage2 = None

    # Upload images to Cloudinary
    folder = f"medintel/{user.id}/{disease_key}"
    original_url = upload_to_cloudinary(original_image_bytes, folder=folder, public_id="original")

    gradcam_url = None
    if gradcam_image_b64:
        try:
            heat_bytes = base64.b64decode(gradcam_image_b64)
            gradcam_url = upload_to_cloudinary(heat_bytes, folder=folder, public_id="gradcam")
        except Exception:
            gradcam_url = None

    row = DiagnosisRecord(
        user_id=user.id,
        disease=disease_key,
        prediction=pred_text,
        confidence=confidence,
        risk_level=risk_level,
        stage1_result=stage1,
        stage2_result=stage2,
        gradcam_image_url=gradcam_url,
        original_image_url=original_url,
        report_explanation=report_explanation,
    )
    db.add(row)
    await db.commit()


@router.post("/lung-cancer")
@limiter.limit("10/minute")
async def lung_cancer_diagnosis(
    request: Request,
    image: UploadFile = File(...),
    report_text: str | None = Form(default=None),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    image_bytes = await image.read()
    validate_image_upload(image, image_bytes)
    report_text = sanitize_string(report_text)
    prediction = predict_lung_cancer(image_bytes)
    model, kind = get_loaded_model_for_disease("lung-cancer")
    gradcam_image, gradcam_regions = generate_gradcam_for_disease(
        "lung-cancer", image_bytes, model=model, model_kind=kind
    )
    await _maybe_save_record(
        db=db,
        user=user,
        disease="lung_cancer",
        prediction=prediction,
        gradcam_image_b64=gradcam_image,
        original_image_bytes=image_bytes,
        report_explanation=None,
    )
    return {"prediction": prediction, "gradcam_image": gradcam_image, "gradcam_regions": gradcam_regions}


@router.post("/skin-disease")
@limiter.limit("10/minute")
async def skin_disease_diagnosis(
    request: Request,
    image: UploadFile = File(...),
    report_text: str | None = Form(default=None),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    image_bytes = await image.read()
    validate_image_upload(image, image_bytes)
    report_text = sanitize_string(report_text)
    prediction = predict_skin_disease(image_bytes)
    model, kind = get_loaded_model_for_disease("skin-disease")
    gradcam_image, gradcam_regions = generate_gradcam_for_disease(
        "skin-disease", image_bytes, model=model, model_kind=kind
    )
    await _maybe_save_record(
        db=db,
        user=user,
        disease="skin_disease",
        prediction=prediction,
        gradcam_image_b64=gradcam_image,
        original_image_bytes=image_bytes,
        report_explanation=None,
    )
    return {"prediction": prediction, "gradcam_image": gradcam_image, "gradcam_regions": gradcam_regions}


@router.post("/diabetic-retinopathy")
@limiter.limit("10/minute")
async def diabetic_retinopathy_diagnosis(
    request: Request,
    image: UploadFile = File(...),
    report_text: str | None = Form(default=None),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    image_bytes = await image.read()
    validate_image_upload(image, image_bytes)
    report_text = sanitize_string(report_text)
    prediction = predict_diabetic_retinopathy(image_bytes)
    model, kind = get_loaded_model_for_disease("diabetic-retinopathy")
    gradcam_image, gradcam_regions = generate_gradcam_for_disease(
        "diabetic-retinopathy", image_bytes, model=model, model_kind=kind
    )
    await _maybe_save_record(
        db=db,
        user=user,
        disease="diabetic_retinopathy",
        prediction=prediction,
        gradcam_image_b64=gradcam_image,
        original_image_bytes=image_bytes,
        report_explanation=None,
    )
    return {"prediction": prediction, "gradcam_image": gradcam_image, "gradcam_regions": gradcam_regions}


@router.post("/gradcam")
async def gradcam_only(
    disease: str = Form(...),
    image: UploadFile = File(...),
):
    image_bytes = await image.read()
    validate_image_upload(image, image_bytes)
    model, kind = get_loaded_model_for_disease(disease)
    gradcam_image, _regions = generate_gradcam_for_disease(disease, image_bytes, model=model, model_kind=kind)
    return {"gradcam_image": gradcam_image}


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

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
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
    stmt = select(DiagnosisRecord).where(
        DiagnosisRecord.id == diagnosis_id, DiagnosisRecord.user_id == current_user.id
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Diagnosis record not found")
    return DiagnosisRecordResponse.model_validate(record)


@router.delete("/{diagnosis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_diagnosis(
    diagnosis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(DiagnosisRecord).where(
        DiagnosisRecord.id == diagnosis_id, DiagnosisRecord.user_id == current_user.id
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Diagnosis record not found")

    await db.delete(record)
    await db.commit()
    return


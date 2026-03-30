import asyncio
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.services.gradcam_service import generate_gradcam_for_disease
from app.services.ml_service import (
    get_loaded_model_for_disease,
    predict_diabetic_retinopathy,
    predict_lung_cancer,
    predict_skin_disease,
)
from app.services.report_service import (
    correlate_report_with_scan,
    explain_medical_report,
    extract_text_from_image,
    extract_text_from_pdf,
)
from app.utils.file_utils import sanitize_string, validate_image_upload

logger = logging.getLogger("app.report_route")

router = APIRouter(prefix="/report")

_ALLOWED_IMAGE_CT = {"image/jpeg", "image/png"}
_ALLOWED_PDF_CT = {"application/pdf"}


def _ext(filename: str | None) -> str:
    name = (filename or "").lower()
    return name.rsplit(".", 1)[-1] if "." in name else ""


def _validate_file(file: UploadFile, file_bytes: bytes, *, allow_pdf: bool) -> None:
    # ✅ Extract file extension safely
    if not file.filename:
        logger.error(f"File validation failed: no filename provided")
        raise HTTPException(status_code=422, detail="File must have a name/extension.")
    
    ext = _ext(file.filename)
    logger.info(f"Processing file with extension: {ext}")
    
    if file.content_type in _ALLOWED_IMAGE_CT:
        # Full image validation including magic bytes
        validate_image_upload(file, file_bytes)
        return

    if allow_pdf and file.content_type in _ALLOWED_PDF_CT:
        if ext != "pdf":
            logger.warning(f"PDF file validation failed: expected .pdf extension, got .{ext}")
            raise HTTPException(status_code=422, detail="Invalid PDF file extension.")
        return

    logger.warning(f"File validation failed: unsupported content type {file.content_type}")
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Invalid file type. Upload a PDF or an image (jpg/jpeg/png).",
    )


def _extract_report_text(file: UploadFile, file_bytes: bytes) -> str:
    if file.content_type in _ALLOWED_PDF_CT:
        return extract_text_from_pdf(file_bytes)
    return extract_text_from_image(file_bytes)


def _run_diagnosis_for_disease(disease: str, image_bytes: bytes) -> dict:
    key = (disease or "").strip().lower()
    if key in {"lung-cancer", "lung_cancer"}:
        prediction = predict_lung_cancer(image_bytes)
        disease_key = "lung-cancer"
    elif key in {"skin-disease", "skin_disease"}:
        prediction = predict_skin_disease(image_bytes)
        disease_key = "skin-disease"
    elif key in {"diabetic-retinopathy", "diabetic_retinopathy", "dr"}:
        prediction = predict_diabetic_retinopathy(image_bytes)
        disease_key = "diabetic-retinopathy"
    else:
        raise HTTPException(status_code=422, detail="Unsupported disease. Use lung-cancer, skin-disease, diabetic-retinopathy.")

    model, kind = get_loaded_model_for_disease(disease_key)
    gradcam_image, gradcam_regions = generate_gradcam_for_disease(disease_key, image_bytes, model=model, model_kind=kind)
    return {"prediction": prediction, "gradcam_image": gradcam_image, "gradcam_regions": gradcam_regions}
@router.post("/explain")
async def explain_report(
    file: UploadFile = File(...),
    disease_context: str = Form(...),
):
    file_bytes = await file.read()
    _validate_file(file, file_bytes, allow_pdf=True)
    disease_context = sanitize_string(disease_context) or ""
    report_text = _extract_report_text(file, file_bytes)
    explanation = explain_medical_report(report_text, disease_context)
    return explanation


@router.post("/upload-with-scan")
async def upload_with_scan(
    scan_image: UploadFile = File(...),
    report_file: UploadFile = File(...),
    disease: str = Form(...),
):
    scan_bytes, report_bytes = await asyncio.gather(scan_image.read(), report_file.read())
    _validate_file(scan_image, scan_bytes, allow_pdf=False)
    _validate_file(report_file, report_bytes, allow_pdf=True)

    # Parallelize scan analysis and text extraction (Gemini calls depend on extracted text).
    disease = sanitize_string(disease) or ""
    diagnosis_task = asyncio.to_thread(_run_diagnosis_for_disease, disease, scan_bytes)
    extract_task = asyncio.to_thread(_extract_report_text, report_file, report_bytes)
    diagnosis_result, report_text = await asyncio.gather(diagnosis_task, extract_task)

    explanation = await asyncio.to_thread(explain_medical_report, report_text, disease)
    correlation = await asyncio.to_thread(
        correlate_report_with_scan, report_text, diagnosis_result.get("gradcam_regions") or "No heatmap region available."
    )

    return {
        "diagnosis": diagnosis_result,
        "report_text": report_text,
        "report_explanation": explanation,
        "correlation": correlation,
    }


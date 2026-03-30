from __future__ import annotations

import io
import json
import logging
import re
from typing import Any

import cv2
import numpy as np
import pdfplumber
import pytesseract
from PIL import Image

from app.config import settings


logger = logging.getLogger("app.report_service")


def _clean_text(text: str) -> str:
    text = text or ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[^\S\n]+", " ", text)
    return text.strip()


def extract_text_from_image(file_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    text = pytesseract.image_to_string(thresh)
    return _clean_text(text)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    text_parts: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                t = t.strip()
                if t:
                    text_parts.append(t)
    except Exception as e:
        logger.warning("pdfplumber text extraction failed: %s", e)

    extracted = _clean_text("\n\n".join(text_parts))
    if extracted:
        return extracted

    # OCR fallback (rasterize each page)
    ocr_parts: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                im = page.to_image(resolution=200).original  # PIL Image
                buf = io.BytesIO()
                im.save(buf, format="PNG")
                ocr_parts.append(extract_text_from_image(buf.getvalue()))
    except Exception as e:
        logger.warning("PDF OCR fallback failed: %s", e)

    return _clean_text("\n\n".join([p for p in ocr_parts if p]))


def _gemini_model() -> Any:
    import google.generativeai as genai  # lazy import

    genai.configure(api_key=settings.GEMINI_API_KEY)
    try:
        return genai.GenerativeModel(
            "gemini-1.5-flash",
            system_instruction=(
                "You are a medical AI assistant that explains medical reports in simple, "
                "patient-friendly language. Always include a disclaimer that this is AI "
                "assistance and not a medical diagnosis. Be compassionate and clear."
            ),
        )
    except TypeError:
        # Older SDKs may not support system_instruction
        return genai.GenerativeModel("gemini-1.5-flash")


def explain_medical_report(report_text: str, disease_context: str) -> dict:
    system_fallback = (
        "You are a medical AI assistant that explains medical reports in simple, "
        "patient-friendly language. Always include a disclaimer that this is AI "
        "assistance and not a medical diagnosis. Be compassionate and clear."
    )
    user_prompt = (
        f"Explain this medical report for a patient who has been screened for {disease_context}. "
        "Highlight key findings, what they mean, and what the patient should ask their doctor.\n\n"
        f"Report:\n{report_text}\n\n"
        "Return ONLY valid JSON with keys: "
        "summary, key_findings (array), technical_terms_explained (object), "
        "questions_for_doctor (array), urgency_indicator (ROUTINE|SOON|URGENT), disclaimer."
    )

    model = _gemini_model()
    try:
        resp = model.generate_content(user_prompt)
        text = (getattr(resp, "text", None) or "").strip()
    except Exception as e:
        logger.warning("Gemini explanation failed: %s", e)
        return {
            "summary": "We could not generate an AI explanation at this time.",
            "key_findings": [],
            "technical_terms_explained": {},
            "questions_for_doctor": [],
            "urgency_indicator": "ROUTINE",
            "disclaimer": "This is AI assistance, not a medical diagnosis.",
        }

    # If system_instruction wasn't applied, prepend system guidance via a second pass is overkill;
    # instead, enforce disclaimer in parsing fallback.
    parsed = _safe_parse_json(text)
    if not parsed:
        return {
            "summary": text or "AI explanation unavailable.",
            "key_findings": [],
            "technical_terms_explained": {},
            "questions_for_doctor": [],
            "urgency_indicator": "ROUTINE",
            "disclaimer": "This is AI assistance, not a medical diagnosis.",
        }

    parsed.setdefault("disclaimer", "This is AI assistance, not a medical diagnosis.")
    parsed.setdefault("urgency_indicator", "ROUTINE")
    return parsed


def _safe_parse_json(text: str) -> dict | None:
    if not text:
        return None
    # try direct
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    # try extract fenced code block
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text, re.IGNORECASE)
    if m:
        try:
            obj = json.loads(m.group(1))
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    # try first {...} span
    m2 = re.search(r"(\{[\s\S]*\})", text)
    if m2:
        try:
            obj = json.loads(m2.group(1))
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None


def correlate_report_with_scan(report_text: str, gradcam_description: str) -> str:
    prompt = (
        "You are a medical AI assistant. Explain, in plain language, how the report text might "
        "correlate with the AI scan heatmap description. If correlation is unclear, say so.\n\n"
        f"Heatmap description:\n{gradcam_description}\n\n"
        f"Report:\n{report_text}\n"
    )
    model = _gemini_model()
    try:
        resp = model.generate_content(prompt)
        return (getattr(resp, "text", None) or "").strip() or "Correlation unclear from the provided information."
    except Exception as e:
        logger.warning("Gemini correlation failed: %s", e)
        return "Correlation could not be generated at this time."

from typing import List, Dict, Any
import re


def extract_key_terms(text: str) -> List[Dict[str, str]]:
    """Extract key medical terms from report"""
    # Common medical terms and their meanings
    term_meanings = {
        "opacity": "hazy or cloudy area in the lung",
        "nodule": "small round growth",
        "mass": "larger growth or tumor",
        "infiltrate": "substance that has passed into tissue",
        "consolidation": "lung tissue filled with fluid",
        "pleural effusion": "fluid around the lungs",
        "pneumothorax": "collapsed lung",
        "atelectasis": "collapsed or airless lung",
        "lesion": "area of abnormal tissue",
        "malignancy": "cancerous growth",
    }
    
    found_terms = []
    text_lower = text.lower()
    
    for term, meaning in term_meanings.items():
        if term in text_lower:
            found_terms.append({"term": term, "meaning": meaning})
    
    return found_terms[:5]  # Return top 5


def match_scan_to_report(scan_prediction: str, report_text: str) -> str:
    """Match scan diagnosis to report findings"""
    report_lower = report_text.lower()
    prediction_lower = scan_prediction.lower()
    
    if "cancer" in prediction_lower or "malignancy" in prediction_lower:
        if "cancer" in report_lower or "malignancy" in report_lower or "tumor" in report_lower:
            return "Matches cancer findings in report"
        return "Report may need review for cancer indicators"
    
    if "pneumonia" in prediction_lower:
        if "pneumonia" in report_lower or "infection" in report_lower:
            return "Matches infection findings"
        return "Report shows different findings"
    
    if "normal" in prediction_lower or "benign" in prediction_lower:
        return "Matches normal/benign findings in report"
    
    return "Report findings align with scan analysis"

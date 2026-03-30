from __future__ import annotations

from app.schemas.risk_assessment import (
    DiabeticRetinopathyRiskInput,
    LungCancerRiskInput,
    SkinDiseaseRiskInput,
)


def _risk_level(score: int) -> str:
    if score >= 7:
        return "HIGH"
    if score >= 4:
        return "MODERATE"
    return "LOW"


def calculate_lung_cancer_risk(data: LungCancerRiskInput) -> dict:
    score = 0
    reasons: list[str] = []
    recommendations: list[str] = []

    if data.smoking_years > 20:
        score += 3
        reasons.append("Long-term smoking history (>20 years).")
    elif data.smoking_years > 10:
        score += 2
        reasons.append("Smoking history (>10 years).")

    if data.cigarettes_per_day > 20:
        score += 2
        reasons.append("High daily cigarette consumption (>20/day).")

    if data.chronic_cough:
        score += 2
        reasons.append("Chronic cough.")
    if data.chest_pain:
        score += 2
        reasons.append("Chest pain.")
    if data.family_history:
        score += 2
        reasons.append("Family history of lung cancer.")
    if data.weight_loss:
        score += 1
        reasons.append("Unexplained weight loss.")

    risk_level = _risk_level(score)

    if risk_level == "HIGH":
        recommendations.extend(
            [
                "Seek prompt evaluation by a pulmonologist or physician.",
                "Consider smoking cessation support immediately if currently smoking.",
            ]
        )
    elif risk_level == "MODERATE":
        recommendations.extend(
            [
                "Discuss symptoms and risk factors with a physician.",
                "Consider smoking cessation support if applicable.",
            ]
        )
    else:
        recommendations.extend(
            [
                "Maintain routine health check-ups and avoid smoke exposure.",
                "If symptoms persist or worsen, consult a physician.",
            ]
        )

    return {
        "risk_level": risk_level,
        "score": score,
        "reasons": reasons or ["No major risk factors reported."],
        "recommendations": recommendations,
        "suggested_scan": "Chest X-ray / CT Scan",
        "action_buttons": ["find_hospitals", "upload_scan"],
        "find_hospitals_query": "pulmonologist or lung cancer screening center",
    }


def calculate_skin_risk(data: SkinDiseaseRiskInput) -> dict:
    score = 0
    reasons: list[str] = []
    recommendations: list[str] = []

    if data.lesion_duration_weeks >= 4:
        score += 1
        reasons.append("Lesion present for 4 weeks or longer.")
    if data.size_change:
        score += 2
        reasons.append("Lesion size has changed.")
    if data.color_variation:
        score += 2
        reasons.append("Color variation in the lesion.")
    if data.bleeding:
        score += 2
        reasons.append("Lesion bleeding.")
    if data.itching:
        score += 1
        reasons.append("Persistent itching.")
    if data.irregular_border:
        score += 2
        reasons.append("Irregular lesion border.")

    risk_level = _risk_level(score)

    if risk_level == "HIGH":
        recommendations.extend(
            [
                "Book an urgent dermatology review for dermatoscopic assessment.",
                "Avoid picking/scratching and protect the area from sun exposure.",
            ]
        )
    elif risk_level == "MODERATE":
        recommendations.extend(
            [
                "Schedule a dermatology appointment for evaluation.",
                "Monitor for rapid changes in size, color, or bleeding.",
            ]
        )
    else:
        recommendations.extend(
            [
                "Continue to monitor the lesion for changes.",
                "Use sun protection and consider routine skin checks.",
            ]
        )

    return {
        "risk_level": risk_level,
        "score": score,
        "reasons": reasons or ["No high-risk skin changes reported."],
        "recommendations": recommendations,
        "suggested_scan": "Dermatoscopy / Skin biopsy",
        "action_buttons": ["find_hospitals", "upload_scan"],
        "find_hospitals_query": "dermatologist or dermatology clinic",
    }


def calculate_dr_risk(data: DiabeticRetinopathyRiskInput) -> dict:
    score = 0
    reasons: list[str] = []
    recommendations: list[str] = []

    if data.diabetes_duration_years > 10:
        score += 3
        reasons.append("Diabetes duration > 10 years.")
    elif data.diabetes_duration_years > 5:
        score += 2
        reasons.append("Diabetes duration > 5 years.")

    if data.hba1c is not None:
        if data.hba1c >= 8.0:
            score += 2
            reasons.append("Elevated HbA1c (≥ 8.0).")
        elif data.hba1c >= 7.0:
            score += 1
            reasons.append("HbA1c above target (≥ 7.0).")

    if data.vision_blurring:
        score += 2
        reasons.append("Vision blurring.")
    if data.floaters:
        score += 2
        reasons.append("New or increased floaters.")
    if data.difficulty_night_vision:
        score += 1
        reasons.append("Difficulty with night vision.")
    if data.blood_pressure_high:
        score += 1
        reasons.append("High blood pressure.")

    risk_level = _risk_level(score)

    if risk_level == "HIGH":
        recommendations.extend(
            [
                "Arrange a prompt dilated eye exam with an ophthalmologist.",
                "Work with your clinician to optimize glucose and blood pressure control.",
            ]
        )
    elif risk_level == "MODERATE":
        recommendations.extend(
            [
                "Schedule an eye screening exam in the near term.",
                "Aim for good diabetes and blood pressure control.",
            ]
        )
    else:
        recommendations.extend(
            [
                "Continue routine diabetic eye screening as recommended.",
                "Maintain good glucose and blood pressure control.",
            ]
        )

    return {
        "risk_level": risk_level,
        "score": score,
        "reasons": reasons or ["No major retinopathy risk indicators reported."],
        "recommendations": recommendations,
        "suggested_scan": "Fundus photography / Dilated eye exam",
        "action_buttons": ["find_hospitals", "upload_scan"],
        "find_hospitals_query": "ophthalmologist or eye clinic",
    }


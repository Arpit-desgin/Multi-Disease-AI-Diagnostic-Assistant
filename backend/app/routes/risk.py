from fastapi import APIRouter

from app.schemas.risk_assessment import (
    DiabeticRetinopathyRiskInput,
    LungCancerRiskInput,
    SkinDiseaseRiskInput,
)
from app.services.risk_service import calculate_dr_risk, calculate_lung_cancer_risk, calculate_skin_risk


router = APIRouter(prefix="/risk")


@router.post("/lung-cancer")
async def lung_cancer_risk(payload: LungCancerRiskInput):
    return calculate_lung_cancer_risk(payload)


@router.post("/skin-disease")
async def skin_disease_risk(payload: SkinDiseaseRiskInput):
    return calculate_skin_risk(payload)


@router.post("/diabetic-retinopathy")
async def diabetic_retinopathy_risk(payload: DiabeticRetinopathyRiskInput):
    return calculate_dr_risk(payload)


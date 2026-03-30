from pydantic import BaseModel, Field


class LungCancerRiskInput(BaseModel):
    age: int = Field(ge=0, le=130)
    smoking_years: int = Field(ge=0, description="0 if never smoked")
    cigarettes_per_day: int = Field(ge=0)
    chronic_cough: bool
    chest_pain: bool
    family_history: bool
    weight_loss: bool


class SkinDiseaseRiskInput(BaseModel):
    lesion_duration_weeks: int = Field(ge=0)
    size_change: bool
    color_variation: bool
    bleeding: bool
    itching: bool
    irregular_border: bool


class DiabeticRetinopathyRiskInput(BaseModel):
    diabetes_duration_years: int = Field(ge=0)
    hba1c: float | None = Field(default=None, ge=0, le=25)
    vision_blurring: bool
    floaters: bool
    difficulty_night_vision: bool
    blood_pressure_high: bool


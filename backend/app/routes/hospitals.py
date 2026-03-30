from fastapi import APIRouter, HTTPException, Query

from app.services.hospital_service import geocode_city, get_hospitals_by_disease
from app.utils.file_utils import sanitize_string

router = APIRouter(prefix="/hospitals")


@router.get("/nearby")
async def hospitals_nearby(
    lat: float = Query(...),
    lon: float = Query(...),
    disease: str = Query(...),
    radius: int = Query(10, ge=1, le=100),
):
    try:
        hospitals = await get_hospitals_by_disease(lat, lon, disease, radius_km=radius)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to query hospital service: {e}")
    return {"hospitals": hospitals}


@router.get("/search")
async def hospitals_search(
    city: str = Query(...),
    disease: str = Query(...),
    radius: int = Query(10, ge=1, le=100),
):
    city = sanitize_string(city) or ""
    disease = sanitize_string(disease) or ""
    coords = await geocode_city(city)
    if not coords:
        raise HTTPException(status_code=404, detail="City not found in Nominatim")
    lat, lon = coords
    try:
        hospitals = await get_hospitals_by_disease(lat, lon, disease, radius_km=radius)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to query hospital service: {e}")
    return {"city": city, "lat": lat, "lon": lon, "hospitals": hospitals}


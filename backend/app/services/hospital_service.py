from __future__ import annotations

import math
from typing import Any, Dict, List

import httpx


OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Great-circle distance between two points on Earth in kilometers.
    """
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def get_google_maps_url(name: str, lat: float, lon: float) -> str:
    return f"https://www.google.com/maps/search/{name}/@{lat},{lon},15z"


async def query_overpass(
    lat: float,
    lon: float,
    radius_meters: int,
    amenity_type: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Query Overpass API for hospitals/clinics/doctors around coordinates.
    amenity_type is currently unused but kept for future specialization.
    """
    radius = int(radius_meters)
    query = f"""
    [out:json];
    (
      node["amenity"="hospital"](around:{radius},{lat},{lon});
      node["amenity"="clinic"](around:{radius},{lat},{lon});
      node["healthcare"="doctor"](around:{radius},{lat},{lon});
    );
    out body;
    """

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(OVERPASS_URL, data={"data": query})
        resp.raise_for_status()
        data = resp.json()

    elements = data.get("elements", [])
    hospitals: List[Dict[str, Any]] = []
    for el in elements:
        if el.get("type") != "node":
            continue
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue
        lat2 = float(el.get("lat"))
        lon2 = float(el.get("lon"))
        distance_km = haversine(lat, lon, lat2, lon2)
        hospitals.append(
            {
                "name": name,
                "lat": lat2,
                "lon": lon2,
                "distance_km": distance_km,
                "tags": tags,
                "maps_url": get_google_maps_url(name, lat2, lon2),
            }
        )

    hospitals.sort(key=lambda x: x["distance_km"])
    return hospitals


_DELHI_FALLBACK = [
    {
        "name": "All India Institute of Medical Sciences (AIIMS)",
        "lat": 28.5672,
        "lon": 77.2100,
    },
    {
        "name": "Safdarjung Hospital",
        "lat": 28.5677,
        "lon": 77.2089,
    },
    {
        "name": "Sir Ganga Ram Hospital",
        "lat": 28.6402,
        "lon": 77.1890,
    },
    {
        "name": "Fortis Escorts Heart Institute",
        "lat": 28.5610,
        "lon": 77.2815,
    },
    {
        "name": "Max Super Speciality Hospital, Saket",
        "lat": 28.5285,
        "lon": 77.2190,
    },
]


def _apply_fallback(lat: float, lon: float) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for h in _DELHI_FALLBACK:
        d = haversine(lat, lon, h["lat"], h["lon"])
        results.append(
            {
                "name": h["name"],
                "lat": h["lat"],
                "lon": h["lon"],
                "distance_km": d,
                "maps_url": get_google_maps_url(h["name"], h["lat"], h["lon"]),
            }
        )
    results.sort(key=lambda x: x["distance_km"])
    return results


async def get_hospitals_by_disease(
    lat: float,
    lon: float,
    disease: str,
    radius_km: int = 10,
) -> List[Dict[str, Any]]:
    radius_m = radius_km * 1000
    all_results = await query_overpass(lat, lon, radius_meters=radius_m)

    key = (disease or "").strip().lower()
    speciality_tag = None
    if key in {"lung_cancer", "lung-cancer"}:
        speciality_tag = "pulmonology"
    elif key in {"skin_disease", "skin-disease"}:
        speciality_tag = "dermatology"
    elif key in {"diabetic_retinopathy", "diabetic-retinopathy", "dr"}:
        speciality_tag = "ophthalmology"

    def has_speciality(tags: Dict[str, Any]) -> bool:
        spec = tags.get("healthcare:speciality") or tags.get("speciality")
        if not spec or not speciality_tag:
            return False
        return speciality_tag.lower() in str(spec).lower()

    specialists = [h for h in all_results if speciality_tag and has_speciality(h.get("tags", {}))]
    chosen = specialists if specialists else all_results

    if not chosen:
        return _apply_fallback(lat, lon)

    # strip internal tags before returning
    for h in chosen:
        h.pop("tags", None)
    return chosen


async def geocode_city(city: str) -> tuple[float, float] | None:
    params = {"q": city, "format": "json", "limit": 1}
    headers = {"User-Agent": "MultiDiseaseAI/1.0"}
    async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
        resp = await client.get(NOMINATIM_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    if not data:
        return None
    first = data[0]
    return float(first["lat"]), float(first["lon"])


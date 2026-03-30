from fastapi import APIRouter


router = APIRouter(prefix="/health")


@router.get("")
async def api_health():
    return {"status": "healthy", "version": "1.0.0"}


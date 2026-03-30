import logging
import os
import time
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import engine
from app.rate_limiter import limiter
from app.routes import auth, diagnosis, risk, report, hospitals, chatbot, health
from app.services.ml_service import get_model_status


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("medintel.api")

app = FastAPI(
    title="MedIntel API",
    description="Multi-Disease AI Diagnostic Assistant API",
    version="1.0.0",
)

# Log startup info
logger.info(f"🚀 ALLOWED_ORIGINS configured: {settings.ALLOWED_ORIGINS}")
logger.info(f"Frontend running on: http://localhost:8080")
logger.info(f"Backend running on: http://localhost:8000")
logger.info(f"Chatbot endpoint: POST http://localhost:8000/api/v1/chatbot/message")

# Middleware to handle CORS preflight without rate limiting
class HandleOptionRequests(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            origin = request.headers.get("Origin", "*")
            logger.info(f"CORS preflight request from origin: {origin}")
            return JSONResponse(
                content={},
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
                    "Access-Control-Max-Age": "3600",
                    "Access-Control-Allow-Credentials": "true",
                },
            )
        return await call_next(request)


# CORS (add FIRST so it runs OUTERMOST)
logger.info(f"Configuring CORSMiddleware with origins: {settings.ALLOWED_ORIGINS}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS or ["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Handle OPTIONS before rate limiter (add SECOND)
app.add_middleware(HandleOptionRequests)

# Rate limiting (add THIRD so it runs after OPTIONS handling)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def add_security_headers_and_logging(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:  # pragma: no cover
        logger.error("Unhandled exception: %s %s - %s", request.method, request.url.path, exc)
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

    duration_ms = (time.time() - start) * 1000
    log_data: Dict[str, Any] = {
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "response_time_ms": round(duration_ms, 2),
    }
    if 500 <= response.status_code < 600:
        logger.error("Request: %s", log_data)
    else:
        logger.info("Request: %s", log_data)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Invalid input",
            "details": exc.errors(),
        },
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Invalid input",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled server error at %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(diagnosis.router, prefix="/api/v1", tags=["diagnosis"])
app.include_router(risk.router, prefix="/api/v1", tags=["risk"])
app.include_router(report.router, prefix="/api/v1", tags=["report"])
app.include_router(hospitals.router, prefix="/api/v1", tags=["hospitals"])
app.include_router(chatbot.router, prefix="/api/v1", tags=["chatbot"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])


# Explicit OPTIONS handler for all routes (bypasses rate limiting)
@app.options("/{full_path:path}")
async def preflight_handler(full_path: str):
    return JSONResponse(
        status_code=200,
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "3600",
        }
    )


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/ready")
async def readiness():
    # DB check
    db_ok = True
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning("Database connection failed: %s", str(e))
        db_ok = False

    models = get_model_status()

    # App is ready even without DB (DB is optional)
    status_code = 200
    return JSONResponse(
        status_code=status_code,
        content={
            "db_ok": db_ok,
            "models": models,
        },
    )


@app.get("/api/v1/models/status")
async def models_status():
    return get_model_status()

from __future__ import annotations

import html
import re
from typing import Iterable

from fastapi import HTTPException, UploadFile, status


_IMAGE_MIME_PREFIXES = ("image/jpeg", "image/png")
_MAX_BYTES = 10 * 1024 * 1024
_ALLOWED_EXTS = {"jpg", "jpeg", "png"}

# Magic bytes (file signatures) for image validation
# Pure Python alternative to libmagic - no system dependencies
_MAGIC_BYTES = {
    b'\xff\xd8\xff': 'image/jpeg',      # JPEG
    b'\x89\x50\x4e\x47': 'image/png',   # PNG
}


def sanitize_string(value: str | None) -> str | None:
    if value is None:
        return None
    value = html.unescape(value)
    # strip HTML tags
    value = re.sub(r"<[^>]+>", "", value)
    return value.strip()


def sanitize_strings(values: Iterable[str | None]) -> list[str | None]:
    return [sanitize_string(v) for v in values]


def _detect_image_type_from_bytes(data: bytes) -> str | None:
    """
    Detect image MIME type from file magic bytes (file signatures).
    
    This is a pure Python implementation that checks file headers
    without requiring system libraries like libmagic.
    
    Args:
        data: Raw file bytes
        
    Returns:
        Detected MIME type (e.g., 'image/jpeg') or None if not recognized
    """
    if not data or len(data) < 4:
        return None
    
    # Check for JPEG (must check 3-byte signature: FF D8 FF)
    if data[:3] == b'\xff\xd8\xff':
        return 'image/jpeg'
    
    # Check for PNG (4-byte signature: 89 50 4E 47)
    if data[:4] == b'\x89\x50\x4e\x47':
        return 'image/png'
    
    return None


def validate_image_upload(file: UploadFile, data: bytes) -> None:
    """
    Validates uploaded image using both declared MIME type and file magic bytes.
    Uses pure Python magic byte detection (no external system dependencies).
    
    Raises HTTPException 422 on invalid file.
    
    Args:
        file: Uploaded file object
        data: Raw file bytes
    """
    if len(data) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File too large. Max size is 10MB.",
        )

    filename = (file.filename or "").lower()
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in _ALLOWED_EXTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid file type. Only jpg, jpeg, png are allowed.",
        )

    declared = (file.content_type or "").lower()
    if declared not in _IMAGE_MIME_PREFIXES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid content type. Only image/jpeg and image/png are allowed.",
        )

    # Validate actual bytes using magic byte detection (pure Python)
    detected = _detect_image_type_from_bytes(data)
    
    if detected is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to determine file type.",
        )

    if not any(detected.startswith(p) for p in _IMAGE_MIME_PREFIXES):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is not a valid image.",
        )


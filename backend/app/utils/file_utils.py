from __future__ import annotations

import html
import re
from typing import Iterable

import magic
from fastapi import HTTPException, UploadFile, status


_IMAGE_MIME_PREFIXES = ("image/jpeg", "image/png")
_MAX_BYTES = 10 * 1024 * 1024
_ALLOWED_EXTS = {"jpg", "jpeg", "png"}


def sanitize_string(value: str | None) -> str | None:
    if value is None:
        return None
    value = html.unescape(value)
    # strip HTML tags
    value = re.sub(r"<[^>]+>", "", value)
    return value.strip()


def sanitize_strings(values: Iterable[str | None]) -> list[str | None]:
    return [sanitize_string(v) for v in values]


def validate_image_upload(file: UploadFile, data: bytes) -> None:
    """
    Validates uploaded image using both declared MIME type and magic bytes.
    Raises HTTPException 422 on invalid file.
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

    # Validate actual bytes
    try:
        detected = magic.from_buffer(data, mime=True)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to determine file type.",
        )

    if not any(detected.startswith(p) for p in _IMAGE_MIME_PREFIXES):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is not a valid image.",
        )


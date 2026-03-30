from __future__ import annotations

import cloudinary
import cloudinary.uploader

from app.config import settings


cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)


def upload_to_cloudinary(file_bytes: bytes, folder: str, public_id: str) -> str:
    """
    Uploads a file to Cloudinary and returns the secure URL.
    """
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        public_id=public_id,
        overwrite=True,
        resource_type="image",
    )
    return result.get("secure_url") or result.get("url")


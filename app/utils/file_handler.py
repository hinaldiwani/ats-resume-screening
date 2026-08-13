"""
app/utils/file_handler.py

Validates and persists uploaded resume files. No parsing or DB logic here —
just filesystem I/O and validation, kept separate so resume_service.py can
be tested without touching disk.
"""

import os
import uuid
from fastapi import UploadFile, HTTPException, status

from app.core.config import get_settings

settings = get_settings()


def validate_upload(file: UploadFile) -> str:
    """
    Validates the uploaded file's extension. Returns the lowercased
    extension (e.g. '.pdf') on success, raises 400 on failure.

    Size is validated separately in save_upload_file, since UploadFile
    doesn't expose a reliable size until the content is read.
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in settings.allowed_resume_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed types: {', '.join(settings.allowed_resume_extensions_list)}.",
        )
    return ext


def save_upload_file(file: UploadFile, ext: str) -> str:
    """
    Streams the upload to disk under settings.UPLOAD_DIR with a UUID-based
    filename (avoids collisions and avoids trusting user-supplied filenames
    for path construction). Returns the relative file path stored in the DB.

    Raises 413 if the file exceeds MAX_UPLOAD_SIZE_MB.
    """
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    unique_name = f"{uuid.uuid4().hex}{ext}"
    destination = os.path.join(settings.UPLOAD_DIR, unique_name)

    size = 0
    with open(destination, "wb") as out_file:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                out_file.close()
                os.remove(destination)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit.",
                )
            out_file.write(chunk)

    return destination

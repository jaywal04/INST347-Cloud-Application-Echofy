"""Azure Blob Storage helpers for profile images."""

from __future__ import annotations

import os
import uuid
from urllib.parse import urlparse

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContentSettings, PublicAccess

CONN_ENV = "AZURE_STORAGE_CONNECTION_STRING"
CONTAINER_ENV = "AZURE_STORAGE_CONTAINER_PROFILES"

_ALLOWED_CT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
_MAX_BYTES = 5 * 1024 * 1024


def profiles_container_name() -> str:
    name = os.environ.get(CONTAINER_ENV, "echofy-profiles").strip()
    return name or "echofy-profiles"


def get_blob_service() -> BlobServiceClient | None:
    conn = os.environ.get(CONN_ENV, "").strip()
    if not conn:
        return None
    return BlobServiceClient.from_connection_string(conn)


def ensure_profiles_container(service: BlobServiceClient) -> None:
    name = profiles_container_name()
    try:
        service.create_container(name, public_access=PublicAccess.Blob)
    except ResourceExistsError:
        pass


def upload_profile_image(user_id: int, file_storage) -> tuple[str | None, str]:
    """
    Upload multipart file to blob storage.
    Returns (public_url, error_message). error_message empty on success.
    """
    service = get_blob_service()
    if not service:
        return None, "Blob storage is not configured (set AZURE_STORAGE_CONNECTION_STRING)."

    content_type = (file_storage.content_type or "").split(";")[0].strip().lower()
    ext = _ALLOWED_CT.get(content_type)
    if not ext:
        return None, "Only JPEG, PNG, or WebP images are allowed."

    raw = file_storage.read()
    if len(raw) > _MAX_BYTES:
        return None, "Image must be 5 MB or smaller."

    ensure_profiles_container(service)
    container = service.get_container_client(profiles_container_name())
    blob_name = f"{user_id}/{uuid.uuid4().hex}{ext}"
    blob = container.get_blob_client(blob_name)
    blob.upload_blob(
        raw,
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type),
    )
    return blob.url, ""


def delete_blob_by_url(url: str | None) -> None:
    if not url:
        return
    service = get_blob_service()
    if not service:
        return
    parsed = urlparse(url)
    path = parsed.path or ""
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        return
    container_name = parts[0]
    blob_name = "/".join(parts[1:])
    if container_name != profiles_container_name():
        return
    try:
        container = service.get_container_client(container_name)
        container.delete_blob(blob_name)
    except Exception:
        pass

"""Azure Blob Storage helpers for profile images."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from azure.core.exceptions import HttpResponseError, ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    ContentSettings,
    PublicAccess,
    generate_blob_sas,
)

CONN_ENV = "AZURE_STORAGE_CONNECTION_STRING"
CONTAINER_ENV = "AZURE_STORAGE_CONTAINER_PROFILES"

_ALLOWED_CT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
_MAX_BYTES = 5 * 1024 * 1024


def profiles_container_name() -> str:
    name = os.environ.get(CONTAINER_ENV, "echofy-profiles").strip().lower()
    return name or "echofy-profiles"


def get_blob_service() -> BlobServiceClient | None:
    conn = os.environ.get(CONN_ENV, "").strip()
    if not conn:
        return None
    return BlobServiceClient.from_connection_string(conn)


def _account_name_key_from_connection_string(conn: str) -> tuple[str, str] | None:
    """Return (account_name, account_key) for SAS signing, or None if not a key-based string."""
    parts: dict[str, str] = {}
    for segment in conn.split(";"):
        segment = segment.strip()
        if "=" not in segment:
            continue
        k, v = segment.split("=", 1)
        parts[k.strip().lower()] = v.strip()
    name = parts.get("accountname")
    key = parts.get("accountkey")
    if name and key:
        return name, key
    return None


def signed_profile_image_url(url: str | None) -> str | None:
    """
    Append a time-limited read SAS for our profile container blobs so <img src> works
    when the storage account disallows anonymous public access (Azure default).
    """
    if not url:
        return None
    base = url.split("?", 1)[0].strip()
    if not base:
        return None
    conn = os.environ.get(CONN_ENV, "").strip()
    if not conn:
        return url
    creds = _account_name_key_from_connection_string(conn)
    if not creds:
        return url
    account_name, account_key = creds
    parsed = urlparse(base)
    path = (parsed.path or "").lstrip("/")
    if "/" not in path:
        return url
    container_name, blob_name = path.split("/", 1)
    if container_name.lower() != profiles_container_name().lower():
        return url
    expiry = datetime.now(timezone.utc) + timedelta(days=30)
    try:
        token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry,
        )
    except Exception:
        return url
    return f"{parsed.scheme}://{parsed.netloc}/{path}?{token}"


def ensure_profiles_container(service: BlobServiceClient) -> tuple[bool, str]:
    """
    Ensure the profile container exists. Tries blob-level public read first (for <img src>),
    then a private container if the storage account disallows public access.

    Returns (ok, error_message). error_message is empty when ok.
    """
    name = profiles_container_name()
    cc = service.get_container_client(name)

    if cc.exists():
        return True, ""

    def _try_create(*, public_blob: bool) -> None:
        if public_blob:
            cc.create_container(public_access=PublicAccess.Blob)
        else:
            cc.create_container()

    try:
        _try_create(public_blob=True)
    except ResourceExistsError:
        pass
    except HttpResponseError:
        try:
            _try_create(public_blob=False)
        except ResourceExistsError:
            pass
        except HttpResponseError:
            pass
    except Exception:
        try:
            _try_create(public_blob=False)
        except ResourceExistsError:
            pass
        except HttpResponseError:
            pass

    if not cc.exists():
        return (
            False,
            (
                f"Blob container {name!r} does not exist and could not be created. "
                "In Azure Portal, open the storage account → Containers → add container "
                f"{name!r}, or allow this app to create containers (account key connection string). "
                "If blob public access is disabled on the account, create the container manually; "
                "you may need to enable public blob access for anonymous image URLs."
            ),
        )

    return True, ""


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

    ok, ensure_err = ensure_profiles_container(service)
    if not ok:
        return None, ensure_err

    container = service.get_container_client(profiles_container_name())
    blob_name = f"{user_id}/{uuid.uuid4().hex}{ext}"
    blob = container.get_blob_client(blob_name)
    try:
        blob.upload_blob(
            raw,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
    except ResourceNotFoundError as e:
        code = getattr(e, "error_code", None) or "not_found"
        return None, (
            f"Blob upload failed ({code}). Create container {profiles_container_name()!r} "
            "in the Azure Portal (Storage account → Containers) and ensure the connection string "
            "has write access."
        )
    return blob.url, ""


def delete_blob_by_url(url: str | None) -> None:
    if not url:
        return
    url = url.split("?", 1)[0]
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
    if container_name.lower() != profiles_container_name().lower():
        return
    try:
        container = service.get_container_client(container_name)
        container.delete_blob(blob_name)
    except Exception:
        pass

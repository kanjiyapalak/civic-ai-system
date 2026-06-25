import logging
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
LOCAL_UPLOAD_DIR = Path("uploads") / "complaints"
S3_PREFIX = os.getenv("AWS_S3_PREFIX", "complaints").strip("/") or "complaints"


class StorageServiceError(Exception):
    pass


def is_s3_enabled() -> bool:
    return bool(
        os.getenv("AWS_S3_BUCKET_NAME")
        and os.getenv("AWS_ACCESS_KEY_ID")
        and os.getenv("AWS_SECRET_ACCESS_KEY")
    )


def _s3_bucket() -> str:
    bucket = os.getenv("AWS_S3_BUCKET_NAME", "").strip()
    if not bucket:
        raise StorageServiceError("AWS_S3_BUCKET_NAME is not configured")
    return bucket


def _s3_region() -> str:
    return os.getenv("AWS_REGION", "us-east-1").strip() or "us-east-1"


def _s3_client():
    return boto3.client(
        "s3",
        region_name=_s3_region(),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def _content_type_for_suffix(suffix: str) -> str:
    mapping = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    return mapping.get(suffix.lower(), "image/jpeg")


def _validate_suffix(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower() or ".jpg"
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Unsupported image format")
    return suffix


def _build_object_key(filename: str) -> str:
    return f"{S3_PREFIX}/{filename}"


def _build_s3_https_url(key: str) -> str:
    bucket = _s3_bucket()
    region = _s3_region()
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def _parse_s3_https_url(image_ref: str) -> Optional[tuple[str, str]]:
    parsed = urlparse(image_ref)
    if parsed.scheme not in {"http", "https"}:
        return None

    host = parsed.netloc.lower()
    bucket = _s3_bucket().lower()
    if host == f"{bucket}.s3.{_s3_region().lower()}.amazonaws.com":
        return bucket, parsed.path.lstrip("/")

    if host == f"{bucket}.s3.amazonaws.com":
        return bucket, parsed.path.lstrip("/")

    if ".s3." in host and host.startswith(f"{bucket}."):
        return bucket, parsed.path.lstrip("/")

    return None


def upload_complaint_image(file: UploadFile) -> str:
    suffix = _validate_suffix(file.filename or "")
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty image file")

    filename = f"{uuid.uuid4()}{suffix}"
    content_type = _content_type_for_suffix(suffix)

    if is_s3_enabled():
        key = _build_object_key(filename)
        extra_args = {"ContentType": content_type}
        if os.getenv("AWS_S3_PUBLIC_READ", "false").lower() in {"1", "true", "yes"}:
            extra_args["ACL"] = "public-read"

        try:
            _s3_client().put_object(
                Bucket=_s3_bucket(),
                Key=key,
                Body=content,
                **extra_args,
            )
        except ClientError as exc:
            logger.exception("S3 upload failed key=%s", key)
            raise HTTPException(status_code=500, detail=f"S3 upload failed: {exc}") from exc

        url = _build_s3_https_url(key)
        logger.info("Image uploaded to S3 key=%s", key)
        return url

    LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = LOCAL_UPLOAD_DIR / filename
    path.write_bytes(content)
    local_ref = str(path.as_posix())
    logger.info("Image saved locally path=%s", local_ref)
    return local_ref


def resolve_public_url(image_ref: Optional[str]) -> Optional[str]:
    if not image_ref:
        return None

    if image_ref.startswith(("http://", "https://")):
        parsed = _parse_s3_https_url(image_ref)
        if parsed and os.getenv("AWS_S3_USE_PRESIGNED", "false").lower() in {"1", "true", "yes"}:
            _, key = parsed
            try:
                return _s3_client().generate_presigned_url(
                    "get_object",
                    Params={"Bucket": _s3_bucket(), "Key": key},
                    ExpiresIn=int(os.getenv("AWS_S3_PRESIGNED_EXPIRY", "3600")),
                )
            except ClientError:
                return image_ref
        return image_ref

    if is_s3_enabled() and not Path(image_ref).exists():
        key = image_ref.lstrip("/")
        if not key.startswith(f"{S3_PREFIX}/"):
            key = _build_object_key(Path(key).name)
        if os.getenv("AWS_S3_USE_PRESIGNED", "false").lower() in {"1", "true", "yes"}:
            try:
                return _s3_client().generate_presigned_url(
                    "get_object",
                    Params={"Bucket": _s3_bucket(), "Key": key},
                    ExpiresIn=int(os.getenv("AWS_S3_PRESIGNED_EXPIRY", "3600")),
                )
            except ClientError:
                pass
        return _build_s3_https_url(key)

    if image_ref.startswith(("http://", "https://")):
        return image_ref

    # Local relative path (legacy) — served via /uploads static mount
    return image_ref


def load_image_bytes(image_ref: str) -> bytes:
    if not image_ref:
        raise StorageServiceError("Image reference is empty")

    if image_ref.startswith(("http://", "https://")):
        parsed = _parse_s3_https_url(image_ref)
        if parsed and is_s3_enabled():
            _, key = parsed
            try:
                response = _s3_client().get_object(Bucket=_s3_bucket(), Key=key)
                data = response["Body"].read()
                if not data:
                    raise StorageServiceError(f"S3 object is empty: {key}")
                return data
            except ClientError as exc:
                raise StorageServiceError(f"Failed to read S3 object {key}: {exc}") from exc

        import requests

        response = requests.get(image_ref, timeout=30)
        response.raise_for_status()
        if not response.content:
            raise StorageServiceError(f"Image is empty: {image_ref}")
        return response.content

    file_path = Path(image_ref)
    if file_path.exists():
        data = file_path.read_bytes()
        if not data:
            raise StorageServiceError(f"Image is empty: {image_ref}")
        return data

    if is_s3_enabled():
        key = image_ref.replace("\\", "/").lstrip("/")
        if not key.startswith(f"{S3_PREFIX}/"):
            key = _build_object_key(Path(key).name)
        try:
            response = _s3_client().get_object(Bucket=_s3_bucket(), Key=key)
            return response["Body"].read()
        except ClientError as exc:
            raise StorageServiceError(f"Image not found: {image_ref}") from exc

    raise StorageServiceError(f"Image not found: {image_ref}")


def guess_mime_type(image_ref: str, default: str = "image/jpeg") -> str:
    mime_type = mimetypes.guess_type(image_ref)[0]
    return mime_type or default

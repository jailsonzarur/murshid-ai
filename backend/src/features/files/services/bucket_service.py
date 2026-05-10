from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from decouple import config
from fastapi import HTTPException, status


@dataclass(frozen=True)
class BucketUploadResult:
    key: str
    file_url: str
    content_type: str | None
    size: int


@dataclass(frozen=True)
class BucketObject:
    key: str
    file_url: str
    content: bytes
    content_type: str | None
    size: int


@dataclass(frozen=True)
class MinioEndpointConfig:
    endpoint: str
    public_url: str
    secure: bool


class BucketConfigurationError(RuntimeError):
    pass


class BucketKeyError(ValueError):
    pass


def get_config_value(names: tuple[str, ...], default: str = "") -> str:
    for name in names:
        value = str(config(name, default="")).strip()
        if value:
            return value

    return default


def get_minio_public_endpoint() -> str:
    endpoint = get_config_value(
        ("MINIO_PUBLIC_ENDPOINT", "BUCKET_ENDPOINT_URL", "MINIO_ENDPOINT_URL", "MINIO_ENDPOINT")
    )
    if endpoint:
        return endpoint

    host = get_config_value(("MINIO_PUBLIC_HOST",))
    port = get_config_value(("MINIO_PUBLIC_PORT", "PORT"))

    if not host:
        return ""

    scheme = "https" if port == "443" else "http"

    if port:
        return f"{scheme}://{host}:{port}"

    return f"{scheme}://{host}"


def get_minio_endpoint_config() -> MinioEndpointConfig:
    public_url = get_minio_public_endpoint().rstrip("/")

    if not public_url:
        raise BucketConfigurationError("MINIO_PUBLIC_ENDPOINT is required")

    parsed = urlparse(public_url)

    if parsed.scheme:
        endpoint = parsed.netloc
        secure = parsed.scheme == "https"
    else:
        endpoint = public_url
        secure = endpoint.endswith(":443")
        scheme = "https" if secure else "http"
        public_url = f"{scheme}://{endpoint}"

    if not endpoint:
        raise BucketConfigurationError("MINIO_PUBLIC_ENDPOINT is invalid")

    return MinioEndpointConfig(endpoint=endpoint, public_url=public_url, secure=secure)


def normalize_bucket_key(key: str) -> str:
    normalized = PurePosixPath(key.strip().lstrip("/"))

    if not str(normalized) or str(normalized) == ".":
        raise BucketKeyError("Bucket key cannot be empty")

    if normalized.is_absolute() or ".." in normalized.parts:
        raise BucketKeyError("Bucket key cannot contain path traversal")

    return normalized.as_posix()


class MinioBucketService:
    def __init__(
        self,
        *,
        client: Any,
        bucket_name: str,
        public_base_url: str = "",
    ) -> None:
        if not bucket_name:
            raise BucketConfigurationError("BUCKET_NAME is required")

        self.client = client
        self.bucket_name = bucket_name
        self.public_base_url = public_base_url.rstrip("/")

    def upload(
        self,
        content: bytes,
        original_name: str,
        *,
        folder: str | None = None,
        content_type: str | None = None,
        key: str | None = None,
    ) -> BucketUploadResult:
        object_key = self._build_key(original_name, folder=folder, key=key)
        self.client.put_object(
            self.bucket_name,
            object_key,
            data=BytesIO(content),
            length=len(content),
            content_type=content_type,
        )

        return BucketUploadResult(
            key=object_key,
            file_url=self.get_file_url(object_key),
            content_type=content_type,
            size=len(content),
        )

    def upload_bytes(
        self,
        content: bytes,
        original_name: str,
        *,
        folder: str | None = None,
        content_type: str | None = None,
        key: str | None = None,
    ) -> BucketUploadResult:
        return self.upload(
            content,
            original_name,
            folder=folder,
            content_type=content_type,
            key=key,
        )

    def get(self, key: str) -> BucketObject:
        object_key = self._extract_key(key)

        try:
            response = self.client.get_object(self.bucket_name, object_key)
        except Exception as error:
            error_code = self._get_client_error_code(error)

            if error_code in {"NoSuchKey", "NoSuchBucket", "404"}:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"success": False, "errors": ["Arquivo nao encontrado"], "data": None},
                ) from error

            raise

        try:
            content = response.read()
            content_type = response.headers.get("content-type") if response.headers else None
        finally:
            response.close()
            response.release_conn()

        return BucketObject(
            key=object_key,
            file_url=self.get_file_url(object_key),
            content=content,
            content_type=content_type,
            size=len(content),
        )

    def download_file(self, key_or_url: str, destination_path: str | Path) -> BucketObject:
        bucket_object = self.get(key_or_url)
        Path(destination_path).write_bytes(bucket_object.content)
        return bucket_object

    def delete(self, key_or_url: str) -> None:
        object_key = self._extract_key(key_or_url)

        try:
            self.client.remove_object(self.bucket_name, object_key)
        except Exception as error:
            error_code = self._get_client_error_code(error)

            if error_code in {"NoSuchKey", "NoSuchBucket", "404"}:
                return

            raise

    def delete_many(self, keys_or_urls: list[str]) -> None:
        for key_or_url in keys_or_urls:
            self.delete(key_or_url)

    def verify_exists(self, key_or_url: str) -> bool:
        object_key = self._extract_key(key_or_url)

        try:
            self.client.stat_object(self.bucket_name, object_key)
        except Exception as error:
            error_code = self._get_client_error_code(error)

            if error_code in {"NoSuchKey", "NoSuchBucket", "404"}:
                return False

            raise

        return True

    def get_file_url(self, key: str) -> str:
        object_key = normalize_bucket_key(key)

        if self.public_base_url:
            return f"{self.public_base_url}/{object_key}"

        return object_key

    def get_presigned_url(self, key_or_url: str, *, expires_in_seconds: int = 3600) -> str:
        object_key = self._extract_key(key_or_url)
        return self.client.presigned_get_object(
            self.bucket_name,
            object_key,
            expires=timedelta(seconds=expires_in_seconds),
        )

    def _build_key(self, original_name: str, *, folder: str | None, key: str | None) -> str:
        if key is not None:
            return normalize_bucket_key(key)

        filename = Path(original_name).name.strip()
        if not filename:
            raise BucketKeyError("Original file name cannot be empty")

        generated_name = f"{uuid4().hex}-{filename}"

        if folder is None:
            return normalize_bucket_key(generated_name)

        return normalize_bucket_key(f"{folder}/{generated_name}")

    def _extract_key(self, key_or_url: str) -> str:
        if self.public_base_url and key_or_url.startswith(f"{self.public_base_url}/"):
            return normalize_bucket_key(key_or_url.removeprefix(f"{self.public_base_url}/"))

        return normalize_bucket_key(key_or_url)

    def _get_client_error_code(self, error: Exception) -> str | None:
        code = getattr(error, "code", None)
        if code:
            return str(code)

        response = getattr(error, "response", None)
        if not isinstance(response, dict):
            return None

        error_data = response.get("Error")
        if not isinstance(error_data, dict):
            return None

        code = error_data.get("Code")
        return str(code) if code else None


def create_minio_client() -> Any:
    endpoint_config = get_minio_endpoint_config()
    access_key_id = get_config_value(
        ("BUCKET_ACCESS_KEY_ID", "AWS_ACCESS_KEY_ID", "MINIO_ACCESS_KEY", "MINIO_ROOT_USER")
    )
    secret_access_key = get_config_value(
        ("BUCKET_SECRET_ACCESS_KEY", "AWS_SECRET_ACCESS_KEY", "MINIO_SECRET_KEY", "MINIO_ROOT_PASSWORD")
    )

    if not access_key_id:
        raise BucketConfigurationError("MINIO_ROOT_USER is required")
    if not secret_access_key:
        raise BucketConfigurationError("MINIO_ROOT_PASSWORD is required")

    from minio import Minio

    return Minio(
        endpoint_config.endpoint,
        access_key=access_key_id,
        secret_key=secret_access_key,
        secure=endpoint_config.secure,
    )


def get_bucket_service() -> MinioBucketService:
    bucket_name = get_config_value(("BUCKET_NAME", "MINIO_BUCKET", "AWS_BUCKET_NAME"))
    public_base_url = get_config_value(
        ("BUCKET_PUBLIC_BASE_URL", "MINIO_PUBLIC_URL"),
        default=get_minio_endpoint_config().public_url,
    )

    return MinioBucketService(
        client=create_minio_client(),
        bucket_name=bucket_name,
        public_base_url=public_base_url,
    )

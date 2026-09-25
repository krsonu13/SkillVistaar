from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base exception for storage errors."""
    pass


class BaseStorageService(ABC):
    """Abstract base class for modular file storage providers."""

    @abstractmethod
    async def store_file(
        self,
        path_key: str,
        content: bytes,
        mime_type: str = "application/octet-stream",
    ) -> str:
        """Store file content at path_key and return the storage identifier/path."""
        pass

    @abstractmethod
    async def read_file(self, path_key: str) -> bytes:
        """Retrieve file content bytes for path_key."""
        pass

    @abstractmethod
    async def delete_file(self, path_key: str) -> bool:
        """Delete file at path_key."""
        pass

    @abstractmethod
    async def get_download_url(
        self,
        path_key: str,
        filename: Optional[str] = None,
        expires_in: int = 3600,
    ) -> Optional[str]:
        """Generate a presigned or public download URL if supported by the provider."""
        pass

    @property
    @abstractmethod
    def is_cloud(self) -> bool:
        """Return True if this is a cloud object storage provider, False if local filesystem."""
        pass


class LocalStorageService(BaseStorageService):
    """Local filesystem storage driver (default for development and testing)."""

    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = Path(root_dir or settings.STORAGE_ROOT).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_cloud(self) -> bool:
        return False

    def _resolve_path(self, path_key: str) -> Path:
        clean_key = path_key.lstrip("/\\")
        target = (self.root_dir / clean_key).resolve()
        try:
            target.relative_to(self.root_dir)
        except ValueError as exc:
            raise StorageError(f"Path traversal detected: {path_key}") from exc
        return target

    async def store_file(
        self,
        path_key: str,
        content: bytes,
        mime_type: str = "application/octet-stream",
    ) -> str:
        target = self._resolve_path(path_key)

        def _write():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

        try:
            await asyncio.to_thread(_write)
            return str(target)
        except OSError as exc:
            raise StorageError(f"Local storage write failed: {exc}") from exc

    async def read_file(self, path_key: str) -> bytes:
        target = self._resolve_path(path_key)
        if not target.exists():
            raise StorageError(f"File not found: {path_key}")

        try:
            return await asyncio.to_thread(target.read_bytes)
        except OSError as exc:
            raise StorageError(f"Local storage read failed: {exc}") from exc

    async def delete_file(self, path_key: str) -> bool:
        target = self._resolve_path(path_key)
        if not target.exists():
            return False

        try:
            await asyncio.to_thread(target.unlink, True)
            return True
        except OSError as exc:
            logger.warning("Local storage delete failed for %s: %s", path_key, exc)
            return False

    async def get_download_url(
        self,
        path_key: str,
        filename: Optional[str] = None,
        expires_in: int = 3600,
    ) -> Optional[str]:
        # Local files are streamed directly via FastAPI FileResponse, no presigned URL needed
        return None


class S3StorageService(BaseStorageService):
    """
    S3-compatible Object Storage driver.
    Seamlessly supports:
      - Cloudflare R2 (10 GB free forever, zero egress fee)
      - Supabase Storage (1 GB free)
      - AWS S3 (5 GB free tier)
      - MinIO / LocalStack
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        region_name: Optional[str] = None,
        public_url_prefix: Optional[str] = None,
    ):
        self.bucket_name = bucket_name or settings.STORAGE_S3_BUCKET_NAME
        self.endpoint_url = endpoint_url or settings.STORAGE_S3_ENDPOINT_URL or None
        self.access_key_id = access_key_id or settings.STORAGE_S3_ACCESS_KEY_ID
        self.secret_access_key = secret_access_key or settings.STORAGE_S3_SECRET_ACCESS_KEY
        self.region_name = region_name or settings.STORAGE_S3_REGION or "auto"
        self.public_url_prefix = public_url_prefix or settings.STORAGE_S3_PUBLIC_URL_PREFIX

        if not self.bucket_name:
            raise StorageError("STORAGE_S3_BUCKET_NAME is required for S3 object storage.")

        try:
            import boto3
            from botocore.config import Config

            client_config = Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            )

            kwargs = {
                "service_name": "s3",
                "aws_access_key_id": self.access_key_id or None,
                "aws_secret_access_key": self.secret_access_key or None,
                "region_name": self.region_name,
                "config": client_config,
            }
            if self.endpoint_url:
                kwargs["endpoint_url"] = self.endpoint_url

            self.s3_client = boto3.client(**kwargs)
            logger.info(
                "S3StorageService initialized (bucket: %s, endpoint: %s, region: %s)",
                self.bucket_name,
                self.endpoint_url or "aws-default",
                self.region_name,
            )
        except ImportError as exc:
            raise StorageError(
                "boto3 is required for S3/Cloudflare R2 storage. Install it via pip install boto3."
            ) from exc

    @property
    def is_cloud(self) -> bool:
        return True

    def _normalize_key(self, path_key: str) -> str:
        return path_key.lstrip("/\\")

    async def store_file(
        self,
        path_key: str,
        content: bytes,
        mime_type: str = "application/octet-stream",
    ) -> str:
        key = self._normalize_key(path_key)

        def _upload():
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                ContentType=mime_type,
            )

        try:
            await asyncio.to_thread(_upload)
            logger.info("Uploaded object to cloud storage: s3://%s/%s (%d bytes)", self.bucket_name, key, len(content))
            return key
        except Exception as exc:
            logger.error("Cloud storage upload failed for %s: %s", key, exc)
            raise StorageError(f"Cloud storage upload error: {exc}") from exc

    async def read_file(self, path_key: str) -> bytes:
        key = self._normalize_key(path_key)

        def _download():
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            return response["Body"].read()

        try:
            return await asyncio.to_thread(_download)
        except Exception as exc:
            logger.error("Cloud storage download failed for %s: %s", key, exc)
            raise StorageError(f"Cloud storage read error: {exc}") from exc

    async def delete_file(self, path_key: str) -> bool:
        key = self._normalize_key(path_key)

        def _delete():
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key,
            )

        try:
            await asyncio.to_thread(_delete)
            return True
        except Exception as exc:
            logger.warning("Cloud storage delete failed for %s: %s", key, exc)
            return False

    async def get_download_url(
        self,
        path_key: str,
        filename: Optional[str] = None,
        expires_in: int = 3600,
    ) -> Optional[str]:
        key = self._normalize_key(path_key)

        if self.public_url_prefix:
            prefix = self.public_url_prefix.rstrip("/")
            return f"{prefix}/{key}"

        def _generate():
            params = {
                "Bucket": self.bucket_name,
                "Key": key,
            }
            if filename:
                params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
            return self.s3_client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expires_in,
            )

        try:
            return await asyncio.to_thread(_generate)
        except Exception as exc:
            logger.warning("Presigned URL generation failed for %s: %s", key, exc)
            return None


_storage_singleton: Optional[BaseStorageService] = None


def get_storage_service() -> BaseStorageService:
    """
    Factory function returning the active modular storage provider.
    Automatically selects S3 (Cloudflare R2 / Supabase) when configured,
    or LocalStorageService when operating in local development or test mode.
    """
    global _storage_singleton
    if _storage_singleton is not None:
        return _storage_singleton

    backend = (settings.STORAGE_BACKEND or "local").lower().strip()

    if backend in {"s3", "r2", "cloudflare_r2", "supabase"} or bool(settings.STORAGE_S3_BUCKET_NAME):
        try:
            _storage_singleton = S3StorageService()
            return _storage_singleton
        except Exception as exc:
            logger.warning(
                "Failed to initialize S3 storage driver (%s). Falling back to LocalStorageService.",
                exc,
            )

    _storage_singleton = LocalStorageService()
    return _storage_singleton

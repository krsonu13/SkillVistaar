import hashlib
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import (
    DocumentScanStatus,
    DocumentType,
    PrivateDocument,
)
from app.services.audit_log_service import AuditLogService
from app.models.audit_log import AuditAction
from app.services.storage_service import get_storage_service, BaseStorageService


class DocumentServiceError(Exception):
    pass


class DocumentNotFoundError(DocumentServiceError):
    pass


class DocumentAccessDeniedError(DocumentServiceError):
    pass


class DocumentValidationError(DocumentServiceError):
    pass


class DocumentStorageError(DocumentServiceError):
    pass


class DocumentService:
    MAX_FILE_SIZE = 10 * 1024 * 1024

    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "image/jpeg",
        "image/png",
    }

    ALLOWED_EXTENSIONS = {
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
    }

    def __init__(
        self,
        db: AsyncSession,
        storage_root: str = "storage/documents",
    ):
        self.db = db
        self.storage_root = Path(storage_root).resolve()
        self.storage: BaseStorageService = get_storage_service()

    def validate_file(
        self,
        filename: str,
        mime_type: str,
        file_size: int,
    ) -> None:
        if not filename or not filename.strip():
            raise DocumentValidationError(
                "Filename is required."
            )

        if len(filename) > 255:
            raise DocumentValidationError(
                "Filename is too long."
            )

        extension = Path(filename).suffix.lower()

        if extension not in self.ALLOWED_EXTENSIONS:
            raise DocumentValidationError(
                "Unsupported file extension."
            )

        normalized_mime = mime_type.strip().lower()

        if normalized_mime not in self.ALLOWED_MIME_TYPES:
            raise DocumentValidationError(
                "Unsupported MIME type."
            )

        if file_size <= 0:
            raise DocumentValidationError(
                "File cannot be empty."
            )

        if file_size > self.MAX_FILE_SIZE:
            raise DocumentValidationError(
                "File exceeds the 10 MB limit."
            )

    @staticmethod
    def calculate_hash(
        content: bytes,
    ) -> str:
        return hashlib.sha256(content).hexdigest()

    def _safe_filename(self, filename: str) -> str:
        """
        Return only the final filename component.

        This prevents path traversal such as:
        ../../private/file.pdf
        """
        safe_name = Path(filename).name.strip()

        if (
            not safe_name
            or safe_name in {".", ".."}
            or safe_name != filename
        ):
            raise DocumentValidationError(
                "Invalid filename."
            )

        return safe_name

    def _safe_storage_path(
        self,
        owner_user_id: UUID,
        document_id: UUID,
        extension: str,
    ) -> Path:
        """
        Build a storage path and verify that it remains underneath
        the configured document storage root.
        """
        owner_directory = (
            self.storage_root
            / str(owner_user_id)
        ).resolve()

        storage_path = (
            owner_directory
            / f"{document_id}{extension}"
        ).resolve()

        try:
            storage_path.relative_to(
                self.storage_root
            )
        except ValueError as exc:
            raise DocumentStorageError(
                "Invalid document storage path."
            ) from exc

        return storage_path

    async def create(
        self,
        owner_user_id: UUID,
        document_type: str,
        filename: str,
        mime_type: str,
        content: bytes,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> PrivateDocument:
        safe_filename = self._safe_filename(filename)

        normalized_mime = mime_type.strip().lower()

        self.validate_file(
            filename=safe_filename,
            mime_type=normalized_mime,
            file_size=len(content),
        )

        try:
            document_type = DocumentType(
                document_type.upper()
            ).value
        except ValueError as exc:
            raise DocumentValidationError(
                "Invalid document type."
            ) from exc

        document_id = uuid4()

        extension = Path(
            safe_filename
        ).suffix.lower()

        storage_key = f"documents/{owner_user_id}/{document_id}{extension}"

        try:
            stored_path = await self.storage.store_file(
                storage_key,
                content,
                mime_type=normalized_mime,
            )
        except Exception as exc:
            raise DocumentStorageError(
                f"Unable to store the document: {exc}"
            ) from exc

        document_hash = self.calculate_hash(content)

        document = PrivateDocument(
            id=document_id,
            owner_user_id=owner_user_id,
            document_type=document_type,
            original_filename=safe_filename,
            storage_path=stored_path,
            mime_type=normalized_mime,
            file_size=len(content),
            sha256_hash=document_hash,
            scan_status=DocumentScanStatus.PENDING.value,
            is_private=True,
            is_active=True,
        )

        self.db.add(document)

        audit_service = AuditLogService(self.db)

        await audit_service.record(
            actor_user_id=owner_user_id,
            action=AuditAction.UPLOAD,
            resource_type="PrivateDocument",
            resource_id=document_id,
            description="Private document uploaded.",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            metadata_json={
                "document_type": document_type,
                "mime_type": normalized_mime,
                "file_size": len(content),
                "sha256_hash": document_hash,
                "scan_status": DocumentScanStatus.PENDING.value,
            },
        )

        try:
            await self.db.commit()
            await self.db.refresh(document)
        except Exception:
            await self.db.rollback()

            # Remove the physical file when the database transaction
            # fails so orphaned private documents are not left behind.
            try:
                await self.storage.delete_file(stored_path)
            except Exception:
                pass

            raise

        return document

    async def get(
        self,
        document_id: UUID,
    ) -> PrivateDocument:
        result = await self.db.execute(
            select(PrivateDocument).where(
                PrivateDocument.id == document_id,
                PrivateDocument.is_active.is_(True),
            )
        )

        document = result.scalar_one_or_none()

        if document is None:
            raise DocumentNotFoundError(
                "Document not found."
            )

        return document

    async def get_owned(
        self,
        user_id: UUID,
        document_id: UUID,
    ) -> PrivateDocument:
        document = await self.get(document_id)

        if document.owner_user_id != user_id:
            raise DocumentAccessDeniedError(
                "You do not have access to this document."
            )

        return document

    async def verify_storage_path(
        self,
        document: PrivateDocument,
    ) -> Path:
        """
        Validate the database path before allowing filesystem access for local storage.
        """
        if self.storage.is_cloud:
            raise DocumentStorageError("Cloud-stored document must be retrieved via get_document_content.")

        storage_path = Path(
            document.storage_path
        ).resolve()

        try:
            storage_path.relative_to(
                self.storage_root
            )
        except ValueError as exc:
            raise DocumentStorageError(
                "Document storage path is outside the permitted storage root."
            ) from exc

        if not storage_path.is_file():
            raise DocumentStorageError(
                "Document file is unavailable."
            )

        return storage_path

    async def get_document_content(
        self,
        document: PrivateDocument,
    ) -> bytes:
        """
        Retrieve document bytes from either local or cloud object storage.
        """
        try:
            return await self.storage.read_file(document.storage_path)
        except Exception as exc:
            raise DocumentStorageError(
                f"Document file is unavailable: {exc}"
            ) from exc

    async def mark_clean(
        self,
        document_id: UUID,
        *,
        actor_user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> PrivateDocument:
        document = await self.get(document_id)

        document.scan_status = (
            DocumentScanStatus.CLEAN.value
        )

        if actor_user_id is not None:
            audit_service = AuditLogService(self.db)

            await audit_service.record(
                actor_user_id=actor_user_id,
                action=AuditAction.VERIFY,
                resource_type="PrivateDocument",
                resource_id=document.id,
                description="Document security scan marked the document clean.",
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                metadata_json={
                    "scan_status": DocumentScanStatus.CLEAN.value,
                },
            )

        await self.db.commit()
        await self.db.refresh(document)

        return document

    async def mark_infected(
        self,
        document_id: UUID,
        *,
        actor_user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> PrivateDocument:
        document = await self.get(document_id)

        document.scan_status = (
            DocumentScanStatus.INFECTED.value
        )
        document.is_active = False

        if actor_user_id is not None:
            audit_service = AuditLogService(self.db)

            await audit_service.record(
                actor_user_id=actor_user_id,
                action=AuditAction.REVOKE,
                resource_type="PrivateDocument",
                resource_id=document.id,
                description="Document was disabled after a security scan.",
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                metadata_json={
                    "scan_status": DocumentScanStatus.INFECTED.value,
                    "is_active": False,
                },
            )

        await self.db.commit()
        await self.db.refresh(document)

        return document

    async def record_view(
        self,
        document: PrivateDocument,
        *,
        actor_user_id: UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> None:
        audit_service = AuditLogService(self.db)

        await audit_service.record(
            actor_user_id=actor_user_id,
            action=AuditAction.VIEW,
            resource_type="PrivateDocument",
            resource_id=document.id,
            description="Private document metadata viewed.",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        await self.db.commit()

    async def record_download(
        self,
        document: PrivateDocument,
        *,
        actor_user_id: UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> None:
        audit_service = AuditLogService(self.db)

        await audit_service.record(
            actor_user_id=actor_user_id,
            action=AuditAction.DOWNLOAD,
            resource_type="PrivateDocument",
            resource_id=document.id,
            description="Private document downloaded.",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            metadata_json={
                "file_size": document.file_size,
                "mime_type": document.mime_type,
                "sha256_hash": document.sha256_hash,
            },
        )

        await self.db.commit()
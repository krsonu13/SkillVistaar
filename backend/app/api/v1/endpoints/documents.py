import io
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    DOWNLOAD_DOCUMENT,
    UPLOAD_DOCUMENT,
    VIEW_DOCUMENT,
    get_permissions_for_roles,
)
from app.core.security import get_current_user_with_roles
from app.db.session import get_db
from app.models.document import DocumentScanStatus
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.services.document_service import (
    DocumentAccessDeniedError,
    DocumentNotFoundError,
    DocumentService,
    DocumentStorageError,
    DocumentValidationError,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


def require_permission(
    roles: list[str],
    permission: str,
) -> None:
    permissions = get_permissions_for_roles(roles)

    if permission not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )


def get_request_ip(request: Request) -> str | None:
    if request.client is None:
        return None

    return request.client.host


def get_request_user_agent(
    request: Request,
) -> str | None:
    user_agent = request.headers.get("user-agent")

    if not user_agent:
        return None

    return user_agent[:1000]


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    request: Request,
    document_type: str = Query(
        ...,
        min_length=1,
        max_length=50,
    ),
    file: UploadFile = File(...),
    auth: tuple[User, list[str]] = Depends(
        get_current_user_with_roles
    ),
    db: AsyncSession = Depends(get_db),
):
    user, roles = auth

    require_permission(
        roles,
        UPLOAD_DOCUMENT,
    )

    content = await file.read()

    service = DocumentService(db)

    try:
        return await service.create(
            owner_user_id=user.id,
            document_type=document_type,
            filename=file.filename or "",
            mime_type=(
                file.content_type
                or "application/octet-stream"
            ),
            content=content,
            ip_address=get_request_ip(request),
            user_agent=get_request_user_agent(request),
        )
    except DocumentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except DocumentStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
)
async def get_document(
    request: Request,
    document_id: UUID,
    auth: tuple[User, list[str]] = Depends(
        get_current_user_with_roles
    ),
    db: AsyncSession = Depends(get_db),
):
    user, roles = auth

    require_permission(
        roles,
        VIEW_DOCUMENT,
    )

    service = DocumentService(db)

    try:
        document = await service.get_owned(
            user.id,
            document_id,
        )

        await service.record_view(
            document,
            actor_user_id=user.id,
            ip_address=get_request_ip(request),
            user_agent=get_request_user_agent(request),
        )

        return document

    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DocumentAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except DocumentStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/{document_id}/download",
)
async def download_document(
    request: Request,
    document_id: UUID,
    auth: tuple[User, list[str]] = Depends(
        get_current_user_with_roles
    ),
    db: AsyncSession = Depends(get_db),
):
    user, roles = auth

    require_permission(
        roles,
        DOWNLOAD_DOCUMENT,
    )

    service = DocumentService(db)

    try:
        document = await service.get_owned(
            user.id,
            document_id,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DocumentAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    if document.scan_status != (
        DocumentScanStatus.CLEAN.value
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Document is not available for download "
                "until security scanning is complete."
            ),
        )

    if service.storage.is_cloud:
        # Check if presigned download URL is available
        presigned_url = await service.storage.get_download_url(
            document.storage_path,
            filename=document.original_filename,
        )
        if presigned_url:
            await service.record_download(
                document,
                actor_user_id=user.id,
                ip_address=get_request_ip(request),
                user_agent=get_request_user_agent(request),
            )
            return RedirectResponse(
                url=presigned_url,
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            )

        # Direct streaming fallback for private cloud buckets
        try:
            file_bytes = await service.get_document_content(document)
        except DocumentStorageError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

        await service.record_download(
            document,
            actor_user_id=user.id,
            ip_address=get_request_ip(request),
            user_agent=get_request_user_agent(request),
        )

        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type=document.mime_type,
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Disposition": (
                    f'attachment; filename="{document.original_filename}"'
                ),
            },
        )
    else:
        try:
            storage_path = await service.verify_storage_path(
                document
            )
        except DocumentStorageError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

        await service.record_download(
            document,
            actor_user_id=user.id,
            ip_address=get_request_ip(request),
            user_agent=get_request_user_agent(request),
        )

        return FileResponse(
            path=storage_path,
            media_type=document.mime_type,
            filename=document.original_filename,
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Disposition": (
                    f'attachment; filename="{document.original_filename}"'
                ),
            },
        )
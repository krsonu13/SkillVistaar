from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    MANAGE_OWN_SKILLS,
    UPLOAD_CREDENTIALS,
    get_permissions_for_roles,
    require_permission,
    require_role,
)
from app.core.security import get_current_user_with_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.candidate_credential import (
    CandidateCredentialListResponse,
    CandidateCredentialResponse,
)
from app.services.candidate_credential_service import (
    CandidateCredentialAccessDeniedError,
    CandidateCredentialNotFoundError,
    CandidateCredentialService,
    CandidateCredentialServiceError,
    CandidateCredentialValidationError,
)


router = APIRouter(
    prefix="/candidate/credentials",
    tags=["Candidate Credentials"],
)


def _get_request_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return None


def _get_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _get_request_id(request: Request) -> str | None:
    return request.headers.get("x-request-id")


def _require_candidate_role(
    current_user_and_roles,
):
    current_user, roles = current_user_and_roles

    require_role(
        roles,
        "CANDIDATE",
    )

    return current_user, roles


@router.post(
    "",
    response_model=CandidateCredentialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_candidate_credential(
    request: Request,
    title: str = Form(...),
    credential_type: str = Form(...),
    issuing_organization_name: str = Form(...),
    issuing_organization_id: uuid.UUID | None = Form(None),
    credential_number: str | None = Form(None),
    issue_date: datetime | None = Form(None),
    expiry_date: datetime | None = Form(None),
    document: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user_and_roles=Depends(get_current_user_with_roles),
):
    current_user, roles = _require_candidate_role(
        current_user_and_roles
    )

    permissions = get_permissions_for_roles(roles)

    require_permission(
        permissions,
        UPLOAD_CREDENTIALS,
    )

    try:
        return await CandidateCredentialService.create_candidate_credential(
            db=db,
            current_user=current_user,
            title=title,
            credential_type=credential_type,
            issuing_organization_name=issuing_organization_name,
            issuing_organization_id=issuing_organization_id,
            credential_number=credential_number,
            issue_date=issue_date,
            expiry_date=expiry_date,
            document=document,
            ip_address=_get_request_ip(request),
            user_agent=_get_user_agent(request),
            request_id=_get_request_id(request),
        )

    except CandidateCredentialValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except CandidateCredentialAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except CandidateCredentialServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=CandidateCredentialListResponse,
)
async def list_candidate_credentials(
    db: AsyncSession = Depends(get_db),
    current_user_and_roles=Depends(get_current_user_with_roles),
):
    current_user, roles = _require_candidate_role(
        current_user_and_roles
    )

    permissions = get_permissions_for_roles(roles)

    require_permission(
        permissions,
        MANAGE_OWN_SKILLS,
    )

    try:
        credentials = (
            await CandidateCredentialService.list_candidate_credentials(
                db=db,
                current_user=current_user,
            )
        )

        return CandidateCredentialListResponse(
            items=credentials,
            total=len(credentials),
        )

    except CandidateCredentialValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{credential_id}/request-verification",
    response_model=CandidateCredentialResponse,
)
async def request_credential_verification(
    credential_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user_and_roles=Depends(get_current_user_with_roles),
):
    current_user, roles = _require_candidate_role(
        current_user_and_roles
    )

    permissions = get_permissions_for_roles(roles)

    require_permission(
        permissions,
        UPLOAD_CREDENTIALS,
    )

    try:
        return await CandidateCredentialService.request_credential_verification(
            db=db,
            current_user=current_user,
            credential_id=credential_id,
        )

    except CandidateCredentialNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except CandidateCredentialValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except CandidateCredentialAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
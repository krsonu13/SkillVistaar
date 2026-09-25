from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.assessment_invitation import (
    AssessmentInvitationCandidateListResponse,
    AssessmentInvitationCandidateResponse,
    AssessmentInvitationCreate,
    AssessmentInvitationListResponse,
    AssessmentInvitationResponse,
)
from app.services.assessment_invitation_service import (
    AssessmentInvitationAccessDeniedError,
    AssessmentInvitationNotFoundError,
    AssessmentInvitationService,
    AssessmentInvitationValidationError,
)


router = APIRouter(
    prefix="/assessment-invitations",
    tags=["Assessment Invitations"],
)


def _request_metadata(request):
    return {
        "ip_address": (
            request.client.host
            if request.client
            else None
        ),
        "user_agent": request.headers.get(
            "user-agent"
        ),
        "request_id": request.headers.get(
            "x-request-id"
        ),
    }


# ---------------------------------------------------------------------------
# EMPLOYER - CREATE
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=AssessmentInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assessment_invitation(
    data: AssessmentInvitationCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentInvitationResponse:
    service = AssessmentInvitationService(db)

    try:
        invitation = await service.create_invitation(
            user=current_user,
            data=data,
            **_request_metadata(request),
        )

        return AssessmentInvitationResponse.model_validate(
            invitation
        )

    except AssessmentInvitationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except AssessmentInvitationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except AssessmentInvitationValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# CANDIDATE - MINE
# ---------------------------------------------------------------------------


@router.get(
    "/mine",
    response_model=AssessmentInvitationCandidateListResponse,
)
async def get_my_assessment_invitations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentInvitationCandidateListResponse:
    service = AssessmentInvitationService(db)

    try:
        invitations = await service.get_candidate_invitations(
            user=current_user,
        )

        items = [
            AssessmentInvitationCandidateResponse.model_validate(
                invitation
            )
            for invitation in invitations
        ]

        return AssessmentInvitationCandidateListResponse(
            items=items,
            total=len(items),
        )

    except AssessmentInvitationAccessDeniedError:
        return AssessmentInvitationCandidateListResponse(
            items=[],
            total=0,
        )


# ---------------------------------------------------------------------------
# EMPLOYER - LIST
# ---------------------------------------------------------------------------


@router.get(
    "/employer",
    response_model=AssessmentInvitationListResponse,
)
async def get_employer_assessment_invitations(
    assessment_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentInvitationListResponse:
    service = AssessmentInvitationService(db)

    try:
        invitations = await service.get_employer_invitations(
            user=current_user,
            assessment_id=assessment_id,
        )

        items = [
            AssessmentInvitationResponse.model_validate(
                invitation
            )
            for invitation in invitations
        ]

        return AssessmentInvitationListResponse(
            items=items,
            total=len(items),
        )

    except AssessmentInvitationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except AssessmentInvitationValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# CANDIDATE - START
# ---------------------------------------------------------------------------


@router.post(
    "/{invitation_id}/start",
    response_model=AssessmentInvitationCandidateResponse,
)
async def start_assessment_invitation(
    invitation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentInvitationCandidateResponse:
    service = AssessmentInvitationService(db)

    try:
        invitation = await service.start_invitation(
            user=current_user,
            invitation_id=invitation_id,
        )

        return AssessmentInvitationCandidateResponse.model_validate(
            invitation
        )

    except AssessmentInvitationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except AssessmentInvitationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except AssessmentInvitationValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# EMPLOYER - CANCEL
# ---------------------------------------------------------------------------


@router.post(
    "/{invitation_id}/cancel",
    response_model=AssessmentInvitationResponse,
)
async def cancel_assessment_invitation(
    invitation_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentInvitationResponse:
    service = AssessmentInvitationService(db)

    try:
        invitation = await service.cancel_invitation(
            user=current_user,
            invitation_id=invitation_id,
            **_request_metadata(request),
        )

        return AssessmentInvitationResponse.model_validate(
            invitation
        )

    except AssessmentInvitationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except AssessmentInvitationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except AssessmentInvitationValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# GET SINGLE - EMPLOYER
# ---------------------------------------------------------------------------


@router.get(
    "/{invitation_id}",
    response_model=AssessmentInvitationResponse,
)
async def get_assessment_invitation(
    invitation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentInvitationResponse:
    service = AssessmentInvitationService(db)

    try:
        invitation = await service.get_invitation(
            invitation_id
        )

        await service.ensure_employer_invitation_access(
            user=current_user,
            invitation=invitation,
        )

        invitation = await service.expire_if_needed(
            invitation
        )

        return AssessmentInvitationResponse.model_validate(
            invitation
        )

    except AssessmentInvitationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except AssessmentInvitationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except AssessmentInvitationValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

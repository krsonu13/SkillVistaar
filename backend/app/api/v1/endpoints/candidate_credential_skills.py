from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_optional_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.candidate_credential_skill import (
    CandidateCredentialSkillCreate,
    CandidateCredentialSkillListResponse,
    CandidateCredentialSkillRemoveResponse,
    CandidateCredentialSkillResponse,
)
from app.services.candidate_credential_skill_service import (
    CandidateCredentialSkillAccessDeniedError,
    CandidateCredentialSkillNotFoundError,
    CandidateCredentialSkillService,
    CandidateCredentialSkillValidationError,
)

router = APIRouter(
    prefix="/candidate/credentials",
    tags=["Candidate Credential Skills"],
)


@router.post(
    "/{credential_id}/skills",
    response_model=CandidateCredentialSkillResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_skill_to_credential(
    credential_id: uuid.UUID,
    payload: CandidateCredentialSkillCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateCredentialSkillResponse:
    try:
        mapping = await CandidateCredentialSkillService.add_skill_to_credential(
            db=db,
            current_user=current_user,
            credential_id=credential_id,
            skill_id=payload.skill_id,
            is_primary=payload.is_primary,
        )

        return CandidateCredentialSkillResponse.model_validate(mapping)

    except CandidateCredentialSkillNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except CandidateCredentialSkillAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except CandidateCredentialSkillValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{credential_id}/skills",
    response_model=CandidateCredentialSkillListResponse,
)
async def list_credential_skills(
    credential_id: uuid.UUID,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateCredentialSkillListResponse:
    try:
        credential = await CandidateCredentialSkillService.get_credential(
            db=db,
            credential_id=credential_id,
        )

        # Credential mappings can only be viewed by the credential owner
        # unless a future permissioned verifier/admin endpoint is introduced.
        if current_user is None:
            raise CandidateCredentialSkillAccessDeniedError(
                "Authentication is required to view credential skill mappings."
            )

        CandidateCredentialSkillService.ensure_candidate_owns_credential(
            current_user=current_user,
            credential=credential,
        )

        items = await CandidateCredentialSkillService.list_credential_skills(
            db=db,
            credential_id=credential_id,
        )

        return CandidateCredentialSkillListResponse(
            items=[
                CandidateCredentialSkillResponse.model_validate(item)
                for item in items
            ],
            total=len(items),
        )

    except CandidateCredentialSkillNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except CandidateCredentialSkillAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.delete(
    "/skill-mappings/{mapping_id}",
    response_model=CandidateCredentialSkillRemoveResponse,
)
async def remove_skill_from_credential(
    mapping_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateCredentialSkillRemoveResponse:
    try:
        await CandidateCredentialSkillService.remove_skill_from_credential(
            db=db,
            current_user=current_user,
            mapping_id=mapping_id,
        )

        return CandidateCredentialSkillRemoveResponse()

    except CandidateCredentialSkillNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except CandidateCredentialSkillAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except CandidateCredentialSkillValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
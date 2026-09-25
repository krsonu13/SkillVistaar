from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.employer_matching import (
    EmployerJobMatchesResponse,
)
from app.services.employer_matching_service import (
    EmployerMatchingAccessDeniedError,
    EmployerMatchingError,
    EmployerMatchingNotFoundError,
    EmployerMatchingService,
)

router = APIRouter(
    prefix="/employer/matching",
    tags=["Employer Matching"],
)


@router.get(
    "/jobs/{job_id}/candidates",
    response_model=EmployerJobMatchesResponse,
)
async def find_candidates(
    job_id: UUID,
    limit: int = Query(
        50,
        ge=1,
        le=100,
    ),
    minimum_score: float = Query(
        0,
        ge=0,
        le=100,
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = EmployerMatchingService(db)

    try:
        return await service.find_candidates(
            user_id=user.id,
            job_id=job_id,
            limit=limit,
            minimum_score=minimum_score,
        )

    except EmployerMatchingNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except EmployerMatchingAccessDeniedError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        ) from exc

    except EmployerMatchingError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
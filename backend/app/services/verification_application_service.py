from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.government_unit import GovernmentUnit
from app.models.verification_application import (
    VerificationApplication,
    VerificationStatus,
)
from app.schemas.verification_application import (
    VerificationApplicationCreate,
    VerificationReviewRequest,
)


class VerificationApplicationError(Exception):
    """Base verification application error."""


class VerificationApplicationNotFoundError(
    VerificationApplicationError
):
    """Application does not exist."""


class InvalidVerificationReviewError(
    VerificationApplicationError
):
    """Review action is invalid."""


async def create_application(db, user, data):
    if data.application_type.value in {
        "GOVERNMENT",
        "TRAINING_INSTITUTE",
    } and data.government_unit_id is None:
        raise VerificationApplicationError(
            "Government jurisdiction is required for this application type."
        )

    if data.government_unit_id is not None:
        government_unit = await db.get(
            GovernmentUnit,
            data.government_unit_id,
        )

        if government_unit is None:
            raise VerificationApplicationError(
                "Government unit not found."
            )

        if not government_unit.is_active:
            raise VerificationApplicationError(
                "Government unit is inactive."
            )

    existing_result = await db.execute(
        select(VerificationApplication).where(
            VerificationApplication.applicant_user_id == user.id,
            VerificationApplication.application_type
            == data.application_type.value,
            VerificationApplication.status
            == VerificationStatus.PENDING.value,
        )
    )

    if existing_result.scalar_one_or_none() is not None:
        raise VerificationApplicationError(
            "A pending verification application already exists."
        )

    application = VerificationApplication(
        applicant_user_id=user.id,
        government_unit_id=data.government_unit_id,
        application_type=data.application_type.value,
        submitted_data=data.submitted_data,
        status=VerificationStatus.PENDING.value,
    )

    db.add(application)
    await db.commit()
    await db.refresh(application)

    return application


async def get_application(
    db: AsyncSession,
    application_id: UUID,
) -> VerificationApplication:
    application = await db.get(
        VerificationApplication,
        application_id,
    )

    if application is None:
        raise VerificationApplicationNotFoundError(
            "Verification application not found."
        )

    return application


async def list_my_applications(
    db: AsyncSession,
    user: User,
) -> list[VerificationApplication]:
    result = await db.execute(
        select(VerificationApplication)
        .where(
            VerificationApplication.applicant_user_id == user.id
        )
        .order_by(
            VerificationApplication.created_at.desc()
        )
    )

    return list(result.scalars().all())


async def review_application(
    db: AsyncSession,
    application_id: UUID,
    verifier: User,
    data: VerificationReviewRequest,
) -> VerificationApplication:
    application = await get_application(
        db,
        application_id,
    )

    if application.applicant_user_id == verifier.id:
        raise InvalidVerificationReviewError(
            "A user cannot review their own application."
        )

    if application.status != VerificationStatus.PENDING.value:
        raise InvalidVerificationReviewError(
            "Only pending applications can be reviewed."
        )

    allowed_statuses = {
        VerificationStatus.APPROVED,
        VerificationStatus.MORE_INFORMATION_REQUIRED,
        VerificationStatus.REJECTED,
    }

    if data.status not in allowed_statuses:
        raise InvalidVerificationReviewError(
            "Invalid review status."
        )

    if (
        data.status == VerificationStatus.REJECTED
        and not data.rejection_reason
    ):
        raise InvalidVerificationReviewError(
            "Rejection reason is required."
        )

    now = datetime.now(timezone.utc)

    application.verifier_user_id = verifier.id
    application.status = data.status.value
    application.remarks = data.remarks
    application.rejection_reason = data.rejection_reason
    application.reviewed_at = now

    await db.commit()
    await db.refresh(application)

    return application
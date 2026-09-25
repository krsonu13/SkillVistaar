from __future__ import annotations

import math
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.institution_profile import (
    InstitutionProfile,
    InstitutionVerificationStatus,
)
from app.models.organization import (
    Organization,
    OrganizationType,
    OrganizationVerificationStatus,
)
from app.models.organization_member import (
    OrganizationMember,
    OrganizationMemberRole,
)
from app.models.user import User
from app.schemas.institution import InstitutionCreate, InstitutionUpdate


class InstitutionServiceError(Exception):
    """Base exception for institution service errors."""


class InstitutionNotFoundError(InstitutionServiceError):
    pass


class InstitutionAccessDeniedError(InstitutionServiceError):
    pass


class InstitutionValidationError(InstitutionServiceError):
    pass


class InstitutionService:
    MANAGER_ROLES = {
        OrganizationMemberRole.ORG_ADMIN.value,
        OrganizationMemberRole.INSTITUTION_ADMIN.value,
    }

    @staticmethod
    async def get_institution(
        db: AsyncSession,
        institution_profile_id: uuid.UUID,
    ) -> InstitutionProfile:
        result = await db.execute(
            select(InstitutionProfile).where(
                InstitutionProfile.id == institution_profile_id
            )
        )

        institution = result.scalar_one_or_none()

        if institution is None:
            raise InstitutionNotFoundError(
                "Institution profile not found."
            )

        return institution

    @staticmethod
    async def get_institution_by_organization(
        db: AsyncSession,
        organization_id: uuid.UUID,
    ) -> InstitutionProfile | None:
        result = await db.execute(
            select(InstitutionProfile).where(
                InstitutionProfile.organization_id == organization_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_organization(
        db: AsyncSession,
        organization_id: uuid.UUID,
    ) -> Organization:
        result = await db.execute(
            select(Organization).where(
                Organization.id == organization_id
            )
        )

        organization = result.scalar_one_or_none()

        if organization is None:
            raise InstitutionValidationError(
                "Organization not found."
            )

        return organization

    @staticmethod
    async def ensure_institution_organization(
        db: AsyncSession,
        organization_id: uuid.UUID,
    ) -> Organization:
        organization = await InstitutionService.get_organization(
            db,
            organization_id,
        )

        if organization.organization_type != (
            OrganizationType.TRAINING_INSTITUTE.value
        ):
            raise InstitutionValidationError(
                "The organization must be a training institute."
            )

        if not organization.is_active:
            raise InstitutionValidationError(
                "The organization is inactive."
            )

        if organization.verification_status in {
            OrganizationVerificationStatus.SUSPENDED.value,
            OrganizationVerificationStatus.REVOKED.value,
        }:
            raise InstitutionValidationError(
                "The organization is suspended or revoked."
            )

        return organization

    @staticmethod
    async def ensure_manager_access(
        db: AsyncSession,
        current_user: User,
        organization_id: uuid.UUID,
    ) -> Organization:
        organization = await InstitutionService.ensure_institution_organization(
            db,
            organization_id,
        )

        result = await db.execute(
            select(OrganizationMember.id).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.role_code.in_(
                    InstitutionService.MANAGER_ROLES
                ),
                OrganizationMember.is_active.is_(True),
            )
        )

        if result.scalar_one_or_none() is None:
            raise InstitutionAccessDeniedError(
                "You are not authorized to manage this institution."
            )

        return organization

    @staticmethod
    async def ensure_institution_manager(
        db: AsyncSession,
        current_user: User,
        institution: InstitutionProfile,
    ) -> Organization:
        return await InstitutionService.ensure_manager_access(
            db,
            current_user,
            institution.organization_id,
        )

    @staticmethod
    def validate_text(
        value: str | None,
        field_name: str,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        if len(value) > 10000:
            raise InstitutionValidationError(
                f"{field_name} is too long."
            )

        return value

    @staticmethod
    async def ensure_unique_code(
        db: AsyncSession,
        institution_code: str | None,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        if not institution_code:
            return

        query = select(InstitutionProfile.id).where(
            func.lower(InstitutionProfile.institution_code)
            == institution_code.lower()
        )

        if exclude_id is not None:
            query = query.where(
                InstitutionProfile.id != exclude_id
            )

        result = await db.execute(query)

        if result.scalar_one_or_none() is not None:
            raise InstitutionValidationError(
                "Institution code is already in use."
            )

    @staticmethod
    async def create_institution(
        db: AsyncSession,
        current_user: User,
        data: InstitutionCreate,
    ) -> InstitutionProfile:
        organization = await InstitutionService.ensure_manager_access(
            db,
            current_user,
            data.organization_id,
        )

        existing = await InstitutionService.get_institution_by_organization(
            db,
            data.organization_id,
        )

        if existing is not None:
            raise InstitutionValidationError(
                "An institution profile already exists for this organization."
            )

        institution_code = (
            data.institution_code.strip()
            if data.institution_code
            else None
        )

        await InstitutionService.ensure_unique_code(
            db,
            institution_code,
        )

        institution = InstitutionProfile(
            organization_id=organization.id,
            institution_code=institution_code,
            accreditation_body=InstitutionService.validate_text(
                data.accreditation_body,
                "Accreditation body",
            ),
            accreditation_number=InstitutionService.validate_text(
                data.accreditation_number,
                "Accreditation number",
            ),
            institution_type=InstitutionService.validate_text(
                data.institution_type,
                "Institution type",
            ),
            description=InstitutionService.validate_text(
                data.description,
                "Description",
            ),
            website=InstitutionService.validate_text(
                data.website,
                "Website",
            ),
            email=InstitutionService.validate_text(
                data.email,
                "Email",
            ),
            phone=InstitutionService.validate_text(
                data.phone,
                "Phone",
            ),
            address=InstitutionService.validate_text(
                data.address,
                "Address",
            ),
            city=InstitutionService.validate_text(
                data.city,
                "City",
            ),
            state=InstitutionService.validate_text(
                data.state,
                "State",
            ),
            country=(
                data.country.strip()
                if data.country
                else "India"
            ),
            verification_status=(
                InstitutionVerificationStatus.PENDING.value
            ),
            is_active=True,
        )

        db.add(institution)
        await db.commit()
        await db.refresh(institution)

        return institution

    @staticmethod
    async def update_institution(
        db: AsyncSession,
        current_user: User,
        institution_profile_id: uuid.UUID,
        data: InstitutionUpdate,
    ) -> InstitutionProfile:
        institution = await InstitutionService.get_institution(
            db,
            institution_profile_id,
        )

        await InstitutionService.ensure_institution_manager(
            db,
            current_user,
            institution,
        )

        if not institution.is_active:
            raise InstitutionValidationError(
                "Inactive institution profiles cannot be updated."
            )

        if institution.verification_status in {
            InstitutionVerificationStatus.SUSPENDED.value,
            InstitutionVerificationStatus.REVOKED.value,
        }:
            raise InstitutionValidationError(
                "Suspended or revoked institutions cannot be updated."
            )

        values = data.model_dump(exclude_unset=True)

        if "institution_code" in values:
            code = values["institution_code"]

            if code is not None:
                code = code.strip() or None

            await InstitutionService.ensure_unique_code(
                db,
                code,
                exclude_id=institution.id,
            )

            institution.institution_code = code

        editable_fields = {
            "accreditation_body",
            "accreditation_number",
            "institution_type",
            "description",
            "website",
            "email",
            "phone",
            "address",
            "city",
            "state",
            "country",
        }

        for field_name in editable_fields:
            if field_name not in values:
                continue

            value = values[field_name]

            if isinstance(value, str):
                value = value.strip()

            setattr(
                institution,
                field_name,
                value,
            )

        # Profile changes require re-review if the institution
        # was already approved.
        if (
            institution.verification_status
            == InstitutionVerificationStatus.APPROVED.value
        ):
            institution.verification_status = (
                InstitutionVerificationStatus.PENDING.value
            )
            institution.verified_at = None

        await db.commit()
        await db.refresh(institution)

        return institution

    @staticmethod
    async def get_for_user(
        db: AsyncSession,
        current_user: User,
        institution_profile_id: uuid.UUID,
    ) -> InstitutionProfile:
        institution = await InstitutionService.get_institution(
            db,
            institution_profile_id,
        )

        if (
            institution.verification_status
            == InstitutionVerificationStatus.APPROVED.value
            and institution.is_active
        ):
            return institution

        await InstitutionService.ensure_institution_manager(
            db,
            current_user,
            institution,
        )

        return institution

    @classmethod
    async def list_institutions(
        cls,
        db: AsyncSession,
        keyword: str | None = None,
        institution_type: str | None = None,
        city: str | None = None,
        state: str | None = None,
        verification_status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[InstitutionProfile], int]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)

        # Public institution discovery must never expose pending,
        # rejected, suspended, or revoked institutions.
        conditions = [
            InstitutionProfile.is_active.is_(True),
            Organization.is_active.is_(True),
            Organization.organization_type
            == OrganizationType.TRAINING_INSTITUTE.value,
            InstitutionProfile.verification_status
            == InstitutionVerificationStatus.APPROVED.value,
        ]

        if keyword:
            pattern = f"%{keyword.strip()}%"
            conditions.append(
                or_(
                    InstitutionProfile.institution_code.ilike(pattern),
                    InstitutionProfile.institution_type.ilike(pattern),
                    InstitutionProfile.description.ilike(pattern),
                    InstitutionProfile.city.ilike(pattern),
                    InstitutionProfile.state.ilike(pattern),
                )
            )

        if institution_type:
            conditions.append(
                func.lower(InstitutionProfile.institution_type)
                == institution_type.strip().lower()
            )

        if city:
            conditions.append(
                func.lower(InstitutionProfile.city)
                == city.strip().lower()
            )

        if state:
            conditions.append(
                func.lower(InstitutionProfile.state)
                == state.strip().lower()
            )

        base_query = (
            select(InstitutionProfile)
            .join(
                Organization,
                Organization.id == InstitutionProfile.organization_id,
            )
            .where(*conditions)
        )

        count_query = (
            select(func.count(InstitutionProfile.id))
            .join(
                Organization,
                Organization.id == InstitutionProfile.organization_id,
            )
            .where(*conditions)
        )

        total = (await db.execute(count_query)).scalar_one()

        result = await db.execute(
            base_query
            .order_by(InstitutionProfile.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        return list(result.scalars().all()), total

    @staticmethod
    def calculate_pages(
        total: int,
        page_size: int,
    ) -> int:
        if total == 0:
            return 0

        return math.ceil(total / page_size)

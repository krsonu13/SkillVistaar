from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_with_roles
from app.db.session import get_db
from app.models.organization import Organization
from app.models.organization_document import OrganizationDocument
from app.models.user import User
from app.schemas.organization_document import (
    OrgDocumentAction,
    OrgDocumentCreate,
    OrgDocumentResponse,
    OrgDocumentUpdate,
)
from app.services.jurisdiction_service import (
    can_user_verify_jurisdiction,
    enforce_verification_authority,
)
from app.services.organization_document_service import OrganizationDocumentService

router = APIRouter(
    prefix="/organization-documents",
    tags=["Organization Documents"],
)


@router.post("", response_model=OrgDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_organization_document(
    payload: OrgDocumentCreate,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> OrganizationDocument:
    """
    Register and submit a document for statutory verification on behalf of caller's organization.
    """
    user, roles = current_user_and_roles
    service = OrganizationDocumentService(db)

    org = await service.get_user_organization(user.id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registered organization found for your user account. Please register your organization first.",
        )

    return await service.create_document(
        organization_id=org.id,
        uploaded_by_user_id=user.id,
        document_type=payload.document_type,
        title=payload.title,
        document_number=payload.document_number,
        issuing_authority=payload.issuing_authority,
        issue_date=payload.issue_date,
        expiry_date=payload.expiry_date,
        file_name=payload.file_name,
        file_url=payload.file_url,
        file_size=payload.file_size,
        mime_type=payload.mime_type,
        document_id=payload.document_id,
    )


@router.get("/mine", response_model=list[OrgDocumentResponse])
async def list_my_organization_documents(
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationDocument]:
    """
    List all documents and their verification history for the authenticated user's organization.
    """
    user, _ = current_user_and_roles
    service = OrganizationDocumentService(db)

    org = await service.get_user_organization(user.id)
    if not org:
        return []

    return await service.list_documents_for_organization(org.id)


@router.get("/organization/{org_id}", response_model=list[OrgDocumentResponse])
async def list_documents_for_organization(
    org_id: uuid.UUID,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationDocument]:
    """
    List documents for a specific organization.
    Caller must be the owner, an authorized government verifier in jurisdiction, or Super Admin.
    """
    user, roles = current_user_and_roles
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found.",
        )

    is_owner = org.owner_user_id == user.id
    is_admin = user.account_type == "SUPER_ADMIN" or "SUPER_ADMIN" in roles

    if not is_owner and not is_admin:
        # Check government verifier authority
        authorized = await can_user_verify_jurisdiction(
            db=db,
            user=user,
            roles=roles,
            target_unit_id=org.government_unit_id,
        )
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have jurisdiction authority to view documents for this organization.",
            )

    service = OrganizationDocumentService(db)
    return await service.list_documents_for_organization(org_id)


@router.get("/{doc_id}", response_model=OrgDocumentResponse)
async def get_organization_document(
    doc_id: uuid.UUID,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> OrganizationDocument:
    """
    Get document details and full verification history.
    """
    service = OrganizationDocumentService(db)
    doc = await service.get_document(doc_id)
    org = await db.get(Organization, doc.organization_id)

    user, roles = current_user_and_roles
    is_owner = org and org.owner_user_id == user.id
    is_admin = user.account_type == "SUPER_ADMIN" or "SUPER_ADMIN" in roles

    if not is_owner and not is_admin:
        authorized = await can_user_verify_jurisdiction(
            db=db,
            user=user,
            roles=roles,
            target_unit_id=org.government_unit_id if org else None,
        )
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this document.",
            )

    return doc


@router.patch("/{doc_id}", response_model=OrgDocumentResponse)
async def update_organization_document(
    doc_id: uuid.UUID,
    payload: OrgDocumentUpdate,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> OrganizationDocument:
    """
    Update document metadata by the organization owner.
    """
    service = OrganizationDocumentService(db)
    doc = await service.get_document(doc_id)
    org = await db.get(Organization, doc.organization_id)

    user, _ = current_user_and_roles
    if not org or org.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organization owner can edit document metadata.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(doc, field, val)

    await db.commit()
    return await service.get_document(doc.id)


@router.post("/{doc_id}/action", response_model=OrgDocumentResponse)
async def review_organization_document(
    doc_id: uuid.UUID,
    payload: OrgDocumentAction,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> OrganizationDocument:
    """
    Perform statutory review action on an organization document.
    Enforces the exact multi-tier jurisdiction verification rules.
    """
    user, roles = current_user_and_roles
    service = OrganizationDocumentService(db)

    return await service.perform_verification_action(
        document_id=doc_id,
        verifier_user=user,
        verifier_roles=roles,
        action=payload.action,
        remarks=payload.remarks,
        reason=payload.reason,
    )

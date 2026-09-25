from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit_log import AuditAction
from app.models.notification import Notification, NotificationPriority
from app.models.organization import Organization
from app.models.organization_document import (
    OrgDocumentStatus,
    OrgDocumentType,
    OrganizationDocument,
    OrganizationDocumentHistory,
)
from app.models.user import User
from app.services.audit_log_service import AuditLogService
from app.services.jurisdiction_service import (
    enforce_verification_authority,
    get_ancestor_unit_ids,
)


class OrganizationDocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_organization(self, user_id: uuid.UUID) -> Organization | None:
        result = await self.db.execute(
            select(Organization).where(Organization.owner_user_id == user_id)
        )
        return result.scalars().first()

    async def create_document(
        self,
        *,
        organization_id: uuid.UUID,
        uploaded_by_user_id: uuid.UUID,
        document_type: str,
        title: str,
        document_number: str | None = None,
        issuing_authority: str | None = None,
        issue_date: date | None = None,
        expiry_date: date | None = None,
        file_name: str | None = None,
        file_url: str | None = None,
        file_size: int | None = None,
        mime_type: str | None = None,
        document_id: uuid.UUID | None = None,
    ) -> OrganizationDocument:
        org = await self.db.get(Organization, organization_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization '{organization_id}' not found.",
            )

        doc = OrganizationDocument(
            organization_id=organization_id,
            document_id=document_id,
            document_type=document_type,
            title=title,
            document_number=document_number,
            issuing_authority=issuing_authority,
            issue_date=issue_date,
            expiry_date=expiry_date,
            file_name=file_name,
            file_url=file_url,
            file_size=file_size,
            mime_type=mime_type,
            status=OrgDocumentStatus.PENDING.value,
            uploaded_by_user_id=uploaded_by_user_id,
        )
        self.db.add(doc)
        await self.db.flush()

        # Add initial history entry
        history = OrganizationDocumentHistory(
            document_id=doc.id,
            actor_user_id=uploaded_by_user_id,
            action="UPLOAD",
            previous_status=None,
            new_status=OrgDocumentStatus.PENDING.value,
            remarks="Document uploaded and queued for statutory verification.",
            reason=None,
        )
        self.db.add(history)

        # Audit log
        audit = AuditLogService(self.db)
        await audit.record(
            actor_user_id=uploaded_by_user_id,
            action=AuditAction.UPLOAD,
            resource_type="organization_document",
            resource_id=doc.id,
            description=f"Document '{title}' ({document_type}) uploaded for {org.legal_name}.",
            metadata_json={
                "organization_id": str(organization_id),
                "document_type": document_type,
                "document_number": document_number,
                "status": OrgDocumentStatus.PENDING.value,
            },
        )

        # Notify eligible verifiers in this jurisdiction
        await self._notify_verifiers_new_document(org=org, doc=doc)

        await self.db.commit()
        return await self.get_document(doc.id)

    async def list_documents_for_organization(
        self,
        organization_id: uuid.UUID,
    ) -> list[OrganizationDocument]:
        result = await self.db.execute(
            select(OrganizationDocument)
            .options(selectinload(OrganizationDocument.history))
            .where(OrganizationDocument.organization_id == organization_id)
            .order_by(OrganizationDocument.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_document(self, document_id: uuid.UUID) -> OrganizationDocument:
        result = await self.db.execute(
            select(OrganizationDocument)
            .options(selectinload(OrganizationDocument.history))
            .where(OrganizationDocument.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization document '{document_id}' not found.",
            )
        return doc

    async def perform_verification_action(
        self,
        *,
        document_id: uuid.UUID,
        verifier_user: User,
        verifier_roles: list[str],
        action: str,
        remarks: str | None = None,
        reason: str | None = None,
    ) -> OrganizationDocument:
        doc = await self.get_document(document_id)
        org = await self.db.get(Organization, doc.organization_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated organization not found.",
            )

        # Strict jurisdiction and verifier tier enforcement
        await enforce_verification_authority(
            db=self.db,
            verifier_user=verifier_user,
            verifier_roles=verifier_roles,
            target_entity_type=org.organization_type,
            target_unit_id=org.government_unit_id,
            action_label=f"{action} document '{doc.title}'",
        )

        now = datetime.now(timezone.utc)
        prev_status = doc.status
        action_upper = action.upper()

        status_mapping = {
            "START_REVIEW": OrgDocumentStatus.UNDER_REVIEW.value,
            "APPROVE": OrgDocumentStatus.VERIFIED.value,
            "VERIFY": OrgDocumentStatus.VERIFIED.value,
            "REJECT": OrgDocumentStatus.REJECTED.value,
            "REQUEST_INFORMATION": OrgDocumentStatus.REQUEST_INFORMATION.value,
            "REQUEST_INFO": OrgDocumentStatus.REQUEST_INFORMATION.value,
            "REVOKE": OrgDocumentStatus.REVOKED.value,
        }

        if action_upper not in status_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid action '{action}'. Allowed actions: "
                    "START_REVIEW, APPROVE, REJECT, REQUEST_INFORMATION, REVOKE."
                ),
            )

        new_status = status_mapping[action_upper]

        if new_status in (OrgDocumentStatus.REJECTED.value, OrgDocumentStatus.REVOKED.value) and not reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A formal reason is required to {action_upper.lower()} this document.",
            )

        if new_status == OrgDocumentStatus.REQUEST_INFORMATION.value and not remarks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Remarks explaining what additional information is required must be provided.",
            )

        doc.status = new_status
        doc.verifier_user_id = verifier_user.id
        doc.verification_remarks = remarks
        if reason:
            doc.rejection_reason = reason

        if new_status == OrgDocumentStatus.VERIFIED.value:
            doc.verified_at = now
            doc.rejection_reason = None

        # Add history record
        history = OrganizationDocumentHistory(
            document_id=doc.id,
            actor_user_id=verifier_user.id,
            action=action_upper,
            previous_status=prev_status,
            new_status=new_status,
            remarks=remarks,
            reason=reason,
            metadata_json={
                "verifier_name": verifier_user.email,
                "verifier_unit_id": str(verifier_user.government_unit_id) if verifier_user.government_unit_id else None,
            },
        )
        self.db.add(history)

        # Audit log
        audit_action = AuditAction.APPROVE if new_status == "VERIFIED" else (
            AuditAction.REJECT if new_status == "REJECTED" else (
                AuditAction.REVOKE if new_status == "REVOKED" else AuditAction.UPDATE
            )
        )
        audit = AuditLogService(self.db)
        await audit.record(
            actor_user_id=verifier_user.id,
            action=audit_action,
            resource_type="organization_document",
            resource_id=doc.id,
            description=f"Document '{doc.title}' ({doc.document_type}) status changed: {prev_status} -> {new_status}.",
            metadata_json={
                "organization_id": str(org.id),
                "previous_status": prev_status,
                "new_status": new_status,
                "remarks": remarks,
                "reason": reason,
                "verifier_user_id": str(verifier_user.id),
                "verifier_jurisdiction_id": str(verifier_user.government_unit_id) if verifier_user.government_unit_id else None,
            },
        )

        # Send in-app notification to the organization owner
        await self._notify_applicant_document_status(
            org=org,
            doc=doc,
            new_status=new_status,
            remarks=remarks,
            reason=reason,
        )

        await self.db.commit()
        return await self.get_document(doc.id)

    async def _notify_verifiers_new_document(
        self,
        org: Organization,
        doc: OrganizationDocument,
    ) -> None:
        """
        Notify eligible verifiers in this jurisdiction that a new document needs review.
        """
        target_unit_id = org.government_unit_id
        if not target_unit_id:
            # Query Super Admins
            super_admin_q = select(User).where(User.account_type == "SUPER_ADMIN", User.is_active.is_(True))
            verifiers = (await self.db.execute(super_admin_q)).scalars().all()
        else:
            # Ancestors of target unit (target unit itself, its parent state, and central gov)
            ancestor_ids = await get_ancestor_unit_ids(self.db, target_unit_id)
            verifiers_q = select(User).where(
                User.is_active.is_(True),
                (User.account_type == "SUPER_ADMIN") | (
                    (User.account_type == "GOVERNMENT") & (User.government_unit_id.in_(ancestor_ids))
                ),
            )
            verifiers = (await self.db.execute(verifiers_q)).scalars().all()

        for v in verifiers[:15]:  # limit to prominent verifiers
            notif = Notification(
                user_id=v.id,
                notification_type="VERIFICATION_DOCUMENT_PENDING",
                priority=NotificationPriority.NORMAL,
                title=f"New Document Verification: {doc.title}",
                message=(
                    f"{org.legal_name} submitted a new document ({doc.document_type}) "
                    f"requiring statutory review."
                ),
                entity_type="organization_document",
                entity_id=doc.id,
                action_url="/government/organizations",
                translation_params={
                    "organization_id": str(org.id),
                    "document_id": str(doc.id),
                    "document_type": doc.document_type,
                    "jurisdiction_id": str(target_unit_id) if target_unit_id else None,
                },
            )
            self.db.add(notif)

    async def _notify_applicant_document_status(
        self,
        org: Organization,
        doc: OrganizationDocument,
        new_status: str,
        remarks: str | None,
        reason: str | None,
    ) -> None:
        """
        Notify the applicant organization owner of the updated document status.
        """
        priority = (
            NotificationPriority.CRITICAL if new_status in ("REJECTED", "REVOKED") else (
                NotificationPriority.HIGH if new_status == "REQUEST_INFORMATION" else NotificationPriority.NORMAL
            )
        )
        msg = f"Your document '{doc.title}' has been {new_status}."
        if remarks:
            msg += f" Remarks: {remarks}"
        if reason:
            msg += f" Reason: {reason}"

        notif = Notification(
            user_id=org.owner_user_id,
            notification_type=f"DOCUMENT_{new_status}",
            priority=priority,
            title=f"Document Update: {doc.title} is {new_status}",
            message=msg,
            entity_type="organization_document",
            entity_id=doc.id,
            action_url="/institution/documents" if org.organization_type == "TRAINING_INSTITUTE" else "/employer/documents",
            translation_params={
                "document_id": str(doc.id),
                "new_status": new_status,
                "remarks": remarks,
                "reason": reason,
            },
        )
        self.db.add(notif)

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction, AuditLog


class AuditLogServiceError(Exception):
    pass


class AuditLogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(
        self,
        *,
        actor_user_id: UUID | None,
        action: str | AuditAction,
        resource_type: str,
        resource_id: UUID | None = None,
        description: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        metadata_json: dict | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            actor_user_id=actor_user_id,
            action=(
                action.value
                if isinstance(action, AuditAction)
                else action
            ),
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            metadata_json=metadata_json,
        )

        self.db.add(audit_log)
        await self.db.flush()

        return audit_log

    async def list_logs(
        self,
        *,
        actor_user_id: UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        conditions = []

        if actor_user_id is not None:
            conditions.append(
                AuditLog.actor_user_id == actor_user_id
            )

        if action:
            conditions.append(
                AuditLog.action == action
            )

        if resource_type:
            conditions.append(
                AuditLog.resource_type == resource_type
            )

        if resource_id is not None:
            conditions.append(
                AuditLog.resource_id == resource_id
            )

        if start_date:
            conditions.append(
                AuditLog.created_at >= start_date
            )

        if end_date:
            conditions.append(
                AuditLog.created_at <= end_date
            )

        count_query = select(
            func.count(AuditLog.id)
        )

        if conditions:
            count_query = count_query.where(*conditions)

        total = await self.db.scalar(count_query)

        query = (
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if conditions:
            query = query.where(*conditions)

        result = await self.db.execute(query)

        return list(result.scalars().all()), int(total or 0)

    async def get_resource_history(
        self,
        *,
        resource_type: str,
        resource_id: UUID,
        limit: int = 100,
    ) -> list[AuditLog]:
        result = await self.db.execute(
            select(AuditLog)
            .where(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id,
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )

        return list(result.scalars().all())
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.following import (
    Following,
    FollowNotificationPreference,
    FollowTargetType,
)
from app.models.user import User


class FollowingServiceError(Exception):
    pass


class FollowingNotFoundError(FollowingServiceError):
    pass


class FollowingValidationError(FollowingServiceError):
    pass


class FollowingAccessDeniedError(FollowingServiceError):
    pass


class FollowingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_active_user(self, user_id: UUID) -> User:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise FollowingAccessDeniedError("User not found.")

        if not getattr(user, "is_active", True):
            raise FollowingAccessDeniedError("User account is inactive.")

        if getattr(user, "is_suspended", False):
            raise FollowingAccessDeniedError("User account is suspended.")

        return user

    @staticmethod
    def _validate_target(
        target_type: FollowTargetType,
        target_id: UUID | None,
        target_key: str | None,
    ) -> None:
        if target_id is None and not target_key:
            raise FollowingValidationError(
                "Either target_id or target_key is required."
            )

        if target_type in {
            FollowTargetType.USER,
            FollowTargetType.ORGANIZATION,
            FollowTargetType.INSTITUTION,
            FollowTargetType.GOVERNMENT_DEPARTMENT,
        } and target_id is None:
            raise FollowingValidationError(
                f"{target_type.value} requires target_id."
            )

        if target_type in {
            FollowTargetType.SECTOR,
            FollowTargetType.OCCUPATION,
        } and not target_key:
            raise FollowingValidationError(
                f"{target_type.value} requires target_key."
            )

    async def follow(
        self,
        *,
        user_id: UUID,
        target_type: FollowTargetType,
        target_id: UUID | None = None,
        target_key: str | None = None,
        notification_preference: FollowNotificationPreference = (
            FollowNotificationPreference.ALL
        ),
    ) -> Following:
        current_user = await self._get_active_user(user_id)

        self._validate_target(
            target_type,
            target_id,
            target_key,
        )

        # Self-follow prevention
        if target_type == FollowTargetType.USER and target_id == user_id:
            raise FollowingValidationError("You cannot follow your own account.")

        if target_type in {FollowTargetType.ORGANIZATION, FollowTargetType.INSTITUTION} and target_id:
            from app.models.organization import Organization
            org_res = await self.db.execute(
                select(Organization.id).where(
                    Organization.id == target_id,
                    Organization.owner_user_id == user_id,
                ).limit(1)
            )
            if org_res.scalar_one_or_none():
                raise FollowingValidationError("You cannot follow your own organization.")

        result = await self.db.execute(
            select(Following).where(
                Following.user_id == user_id,
                Following.target_type == target_type.value,
                Following.target_id == target_id,
                Following.target_key == target_key,
            )
        )
        following = result.scalar_one_or_none()

        if following is not None:
            if following.is_active:
                raise FollowingValidationError(
                    "You are already following this target."
                )

            following.is_active = True
            following.notification_preference = (
                notification_preference.value
            )

            await self.db.commit()
            await self.db.refresh(following)
        else:
            following = Following(
                user_id=user_id,
                target_type=target_type.value,
                target_id=target_id,
                target_key=target_key,
                notification_preference=notification_preference.value,
                is_active=True,
            )
            self.db.add(following)
            try:
                await self.db.commit()
                await self.db.refresh(following)
            except Exception:
                await self.db.rollback()
                raise

        # Send follow notification to target account
        try:
            from app.models.notification import NotificationType
            from app.services.notification_service import NotificationService
            from app.models.organization import Organization

            recipient_user_id = None
            if target_type == FollowTargetType.USER:
                recipient_user_id = target_id
            elif target_type in {FollowTargetType.ORGANIZATION, FollowTargetType.INSTITUTION} and target_id:
                org_owner = await self.db.execute(
                    select(Organization.owner_user_id).where(Organization.id == target_id).limit(1)
                )
                recipient_user_id = org_owner.scalar_one_or_none()

            if recipient_user_id and recipient_user_id != user_id:
                u_handle = f"@{current_user.username}" if current_user.username else "Someone"
                notif_svc = NotificationService(self.db)
                await notif_svc.create_notification(
                    user_id=recipient_user_id,
                    notification_type=NotificationType.FOLLOW_RECEIVED,
                    title=f"New Follower: {u_handle}",
                    message=f"{u_handle} started following you on SkillVistaar.",
                    action_url=f"/profile/@{current_user.username}" if current_user.username else None,
                )
        except Exception:
            pass

        return following

    async def toggle_follow(
        self,
        *,
        user_id: UUID,
        target_type: FollowTargetType,
        target_id: UUID | None = None,
        target_key: str | None = None,
        notification_preference: FollowNotificationPreference = (
            FollowNotificationPreference.ALL
        ),
    ) -> dict[str, Any]:
        await self._get_active_user(user_id)
        self._validate_target(target_type, target_id, target_key)

        result = await self.db.execute(
            select(Following).where(
                Following.user_id == user_id,
                Following.target_type == target_type.value,
                Following.target_id == target_id,
                Following.target_key == target_key,
            )
        )
        following = result.scalar_one_or_none()

        if following is not None and following.is_active:
            following.is_active = False
            await self.db.commit()
            
            f_count = 0
            if target_id:
                f_count_res = await self.db.execute(
                    select(func.count(Following.id)).where(
                        Following.target_id == target_id,
                        Following.is_active.is_(True),
                    )
                )
                f_count = f_count_res.scalar() or 0

            my_fing_res = await self.db.execute(
                select(func.count(Following.id)).where(
                    Following.user_id == user_id,
                    Following.is_active.is_(True),
                )
            )
            my_fing_count = my_fing_res.scalar() or 0

            from app.core.events import event_manager
            await event_manager.send_to_user(
                user_id,
                "FOLLOW_UPDATED",
                {
                    "target_id": str(target_id) if target_id else None,
                    "target_type": target_type.value,
                    "is_following": False,
                    "followers_count": f_count,
                    "following_count": my_fing_count,
                },
            )
            if target_id and target_type == FollowTargetType.USER:
                await event_manager.send_to_user(
                    target_id,
                    "FOLLOW_UPDATED",
                    {
                        "follower_user_id": str(user_id),
                        "followers_count": f_count,
                    },
                )

            return {
                "is_following": False,
                "following_id": None,
                "followers_count": f_count,
                "following_count": my_fing_count,
            }

        active_f = await self.follow(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            target_key=target_key,
            notification_preference=notification_preference,
        )

        f_count = 0
        if target_id:
            f_count_res = await self.db.execute(
                select(func.count(Following.id)).where(
                    Following.target_id == target_id,
                    Following.is_active.is_(True),
                )
            )
            f_count = f_count_res.scalar() or 0

        my_fing_res = await self.db.execute(
            select(func.count(Following.id)).where(
                Following.user_id == user_id,
                Following.is_active.is_(True),
            )
        )
        my_fing_count = my_fing_res.scalar() or 0

        from app.core.events import event_manager
        await event_manager.send_to_user(
            user_id,
            "FOLLOW_UPDATED",
            {
                "target_id": str(target_id) if target_id else None,
                "target_type": target_type.value,
                "is_following": True,
                "followers_count": f_count,
                "following_count": my_fing_count,
            },
        )
        if target_id and target_type == FollowTargetType.USER:
            await event_manager.send_to_user(
                target_id,
                "FOLLOW_UPDATED",
                {
                    "follower_user_id": str(user_id),
                    "followers_count": f_count,
                },
            )

        return {
            "is_following": True,
            "following_id": str(active_f.id),
            "followers_count": f_count,
            "following_count": my_fing_count,
        }

    async def unfollow(
        self,
        *,
        user_id: UUID,
        following_id: UUID,
    ) -> None:
        await self._get_active_user(user_id)

        result = await self.db.execute(
            select(Following).where(
                (Following.id == following_id) | (Following.target_id == following_id),
                Following.user_id == user_id,
                Following.is_active.is_(True),
            ).limit(1)
        )
        following = result.scalar_one_or_none()

        if following is None:
            raise FollowingNotFoundError(
                "Following record not found."
            )

        following.is_active = False
        await self.db.commit()

    async def update_preference(
        self,
        *,
        user_id: UUID,
        following_id: UUID,
        notification_preference: FollowNotificationPreference,
    ) -> Following:
        await self._get_active_user(user_id)

        result = await self.db.execute(
            select(Following).where(
                Following.id == following_id,
                Following.user_id == user_id,
                Following.is_active.is_(True),
            )
        )
        following = result.scalar_one_or_none()

        if following is None:
            raise FollowingNotFoundError(
                "Active following record not found."
            )

        following.notification_preference = (
            notification_preference.value
        )

        await self.db.commit()
        await self.db.refresh(following)

        return following

    async def get_following(
        self,
        *,
        user_id: UUID,
        include_inactive: bool = False,
    ) -> list[Following]:
        await self._get_active_user(user_id)

        query = select(Following).where(
            Following.user_id == user_id,
        )

        if not include_inactive:
            query = query.where(Following.is_active.is_(True))

        query = query.order_by(Following.created_at.desc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_one(
        self,
        *,
        user_id: UUID,
        following_id: UUID,
    ) -> Following:
        await self._get_active_user(user_id)

        result = await self.db.execute(
            select(Following).where(
                Following.id == following_id,
                Following.user_id == user_id,
            )
        )
        following = result.scalar_one_or_none()

        if following is None:
            raise FollowingNotFoundError(
                "Following record not found."
            )

        return following

    async def count_active(
        self,
        *,
        user_id: UUID,
    ) -> int:
        await self._get_active_user(user_id)

        result = await self.db.execute(
            select(func.count(Following.id)).where(
                Following.user_id == user_id,
                Following.is_active.is_(True),
            )
        )

        return int(result.scalar_one())

    async def list_followers(self, target_id: UUID) -> list[dict[str, Any]]:
        """
        List all active followers of a given target (User or Organization).
        """
        from app.models.candidate_profile import CandidateProfile
        from app.models.organization import Organization

        result = await self.db.execute(
            select(Following, User)
            .join(User, Following.user_id == User.id)
            .where(
                Following.target_id == target_id,
                Following.is_active.is_(True),
                User.is_active.is_(True),
            )
            .order_by(Following.created_at.desc())
        )
        rows = result.all()
        followers = []
        for following_rec, u in rows:
            display_name = u.username or "User"
            headline = ""
            avatar_url = None

            cand_res = await self.db.execute(
                select(CandidateProfile).where(CandidateProfile.user_id == u.id).limit(1)
            )
            cand = cand_res.scalar_one_or_none()
            if cand:
                display_name = f"{cand.first_name} {cand.last_name}".strip() or display_name
                headline = cand.headline or cand.professional_summary or ""
                avatar_url = cand.profile_photo_path

            if not cand:
                org_res = await self.db.execute(
                    select(Organization).where(Organization.owner_user_id == u.id).limit(1)
                )
                org = org_res.scalar_one_or_none()
                if org:
                    display_name = org.display_name or org.legal_name
                    headline = org.industry or ""
                    avatar_url = org.logo_path

            followers.append({
                "id": str(u.id),
                "user_id": str(u.id),
                "username": u.username,
                "name": display_name,
                "account_type": u.account_type,
                "headline": headline,
                "avatar_url": avatar_url,
                "is_following": True,
                "created_at": following_rec.created_at.isoformat() if following_rec.created_at else None,
            })
        return followers

    async def list_following_users(self, user_id: UUID) -> list[dict[str, Any]]:
        """
        List all targets (users/organizations) that user_id is actively following.
        """
        from app.models.candidate_profile import CandidateProfile
        from app.models.organization import Organization

        result = await self.db.execute(
            select(Following)
            .where(
                Following.user_id == user_id,
                Following.is_active.is_(True),
            )
            .order_by(Following.created_at.desc())
        )
        followings = result.scalars().all()
        following_list = []
        for f in followings:
            display_name = f.target_key or "Target"
            headline = ""
            avatar_url = None
            username = None
            account_type = f.target_type

            if f.target_type == FollowTargetType.USER.value and f.target_id:
                u_res = await self.db.execute(select(User).where(User.id == f.target_id).limit(1))
                u = u_res.scalar_one_or_none()
                if u:
                    username = u.username
                    display_name = u.username or "User"
                    cand_res = await self.db.execute(
                        select(CandidateProfile).where(CandidateProfile.user_id == u.id).limit(1)
                    )
                    cand = cand_res.scalar_one_or_none()
                    if cand:
                        display_name = f"{cand.first_name} {cand.last_name}".strip() or display_name
                        headline = cand.headline or cand.professional_summary or ""
                        avatar_url = cand.profile_photo_path

            elif f.target_type in (FollowTargetType.ORGANIZATION.value, FollowTargetType.INSTITUTION.value) and f.target_id:
                org_res = await self.db.execute(select(Organization).where(Organization.id == f.target_id).limit(1))
                org = org_res.scalar_one_or_none()
                if org:
                    display_name = org.display_name or org.legal_name
                    headline = org.industry or ""
                    avatar_url = org.logo_path

            following_list.append({
                "id": str(f.target_id or f.id),
                "target_id": str(f.target_id) if f.target_id else None,
                "target_type": f.target_type,
                "username": username,
                "name": display_name,
                "account_type": account_type,
                "headline": headline,
                "avatar_url": avatar_url,
                "is_following": True,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            })
        return following_list
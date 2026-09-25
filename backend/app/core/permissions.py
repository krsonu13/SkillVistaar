from __future__ import annotations

from collections.abc import Iterable
from functools import wraps
from typing import Any, Awaitable, Callable

from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user_with_roles
from app.models.user import User


# ============================================================
# SkillVistaar Role Definitions
# ============================================================

SUPER_ADMIN = "SUPER_ADMIN"

# Government
GOVERNMENT_ADMIN = "GOVERNMENT_ADMIN"
GOVERNMENT_VERIFIER = "GOVERNMENT_VERIFIER"

# Employer / Industry
ORG_ADMIN = "ORG_ADMIN"
HR = "HR"
JOB_POSTER = "JOB_POSTER"
ASSESSMENT_MANAGER = "ASSESSMENT_MANAGER"

# Training Institution
INSTITUTION_ADMIN = "INSTITUTION_ADMIN"

# Candidate
CANDIDATE = "CANDIDATE"


# ============================================================
# Permission Definitions
# ============================================================

# ------------------------------------------------------------
# Authentication / Account
# ------------------------------------------------------------

VIEW_OWN_PROFILE = "VIEW_OWN_PROFILE"
UPDATE_OWN_PROFILE = "UPDATE_OWN_PROFILE"


# ------------------------------------------------------------
# Verification
# ------------------------------------------------------------

VIEW_VERIFICATION = "VIEW_VERIFICATION"
CREATE_VERIFICATION = "CREATE_VERIFICATION"
REVIEW_VERIFICATION = "REVIEW_VERIFICATION"
APPROVE_VERIFICATION = "APPROVE_VERIFICATION"
REJECT_VERIFICATION = "REJECT_VERIFICATION"
REQUEST_VERIFICATION_INFO = "REQUEST_VERIFICATION_INFO"


# ------------------------------------------------------------
# Organization
# ------------------------------------------------------------

VIEW_ORGANIZATION = "VIEW_ORGANIZATION"
MANAGE_ORGANIZATION = "MANAGE_ORGANIZATION"
MANAGE_ORGANIZATION_MEMBERS = "MANAGE_ORGANIZATION_MEMBERS"


# ------------------------------------------------------------
# Jobs
# ------------------------------------------------------------

VIEW_JOBS = "VIEW_JOBS"
CREATE_JOB = "CREATE_JOB"
UPDATE_JOB = "UPDATE_JOB"
PUBLISH_JOB = "PUBLISH_JOB"
CLOSE_JOB = "CLOSE_JOB"

# Candidate application permissions
APPLY_FOR_JOB = "APPLY_FOR_JOB"
VIEW_OWN_APPLICATIONS = "VIEW_OWN_APPLICATIONS"

# Employer application permissions
VIEW_JOB_APPLICATIONS = "VIEW_JOB_APPLICATIONS"
MANAGE_JOB_APPLICATIONS = "MANAGE_JOB_APPLICATIONS"

# Candidate-management permissions
SHORTLIST_CANDIDATES = "SHORTLIST_CANDIDATES"
SELECT_CANDIDATES = "SELECT_CANDIDATES"


# ------------------------------------------------------------
# Backward-compatible application permission aliases
# ------------------------------------------------------------
#
# Older modules may still import these names.
# Keep them mapped to the canonical permissions above so that
# existing code does not break and we do not maintain two
# separate permission systems.
#

APPLY_TO_JOB = APPLY_FOR_JOB
VIEW_APPLICATIONS = VIEW_JOB_APPLICATIONS
MANAGE_APPLICATIONS = MANAGE_JOB_APPLICATIONS


# ------------------------------------------------------------
# Assessments
# ------------------------------------------------------------

VIEW_ASSESSMENT = "VIEW_ASSESSMENT"
CREATE_ASSESSMENT = "CREATE_ASSESSMENT"
UPDATE_ASSESSMENT = "UPDATE_ASSESSMENT"
MANAGE_ASSESSMENT_INVITATIONS = "MANAGE_ASSESSMENT_INVITATIONS"
VIEW_ASSESSMENT_RESULTS = "VIEW_ASSESSMENT_RESULTS"
VIEW_OWN_ASSESSMENT_RESULTS = "VIEW_OWN_ASSESSMENT_RESULTS"
TAKE_ASSESSMENT = "TAKE_ASSESSMENT"


# ------------------------------------------------------------
# Candidate Skills / Credentials
# ------------------------------------------------------------

VIEW_SKILLS = "VIEW_SKILLS"
MANAGE_OWN_SKILLS = "MANAGE_OWN_SKILLS"
VERIFY_SKILLS = "VERIFY_SKILLS"

VIEW_CREDENTIALS = "VIEW_CREDENTIALS"
UPLOAD_CREDENTIALS = "UPLOAD_CREDENTIALS"
VERIFY_CREDENTIALS = "VERIFY_CREDENTIALS"


# ------------------------------------------------------------
# Courses / Institutions
# ------------------------------------------------------------

VIEW_COURSES = "VIEW_COURSES"
CREATE_COURSE = "CREATE_COURSE"
UPDATE_COURSE = "UPDATE_COURSE"
PUBLISH_COURSE = "PUBLISH_COURSE"


# ------------------------------------------------------------
# Labour-Market Intelligence
# ------------------------------------------------------------

VIEW_LABOUR_MARKET = "VIEW_LABOUR_MARKET"
ANALYZE_LABOUR_MARKET = "ANALYZE_LABOUR_MARKET"
MANAGE_LABOUR_MARKET = "MANAGE_LABOUR_MARKET"


# ------------------------------------------------------------
# Government Analytics
# ------------------------------------------------------------

VIEW_GOVERNMENT_ANALYTICS = "VIEW_GOVERNMENT_ANALYTICS"
ANALYZE_GOVERNMENT_DATA = "ANALYZE_GOVERNMENT_DATA"
MANAGE_GOVERNMENT_DATA_ACCESS = "MANAGE_GOVERNMENT_DATA_ACCESS"


# ------------------------------------------------------------
# Following / Notifications
# ------------------------------------------------------------

MANAGE_FOLLOWING = "MANAGE_FOLLOWING"
VIEW_NOTIFICATIONS = "VIEW_NOTIFICATIONS"


# ------------------------------------------------------------
# Documents
# ------------------------------------------------------------

UPLOAD_DOCUMENT = "UPLOAD_DOCUMENT"
VIEW_DOCUMENT = "VIEW_DOCUMENT"
DOWNLOAD_DOCUMENT = "DOWNLOAD_DOCUMENT"


# ------------------------------------------------------------
# Audit
# ------------------------------------------------------------

VIEW_AUDIT_LOGS = "VIEW_AUDIT_LOGS"


# ------------------------------------------------------------
# Administration
# ------------------------------------------------------------

MANAGE_USERS = "MANAGE_USERS"
MANAGE_ROLES = "MANAGE_ROLES"
MANAGE_VERIFIERS = "MANAGE_VERIFIERS"


# ============================================================
# Role -> Permission Matrix
# ============================================================

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {

    # ========================================================
    # SUPER ADMIN
    # ========================================================

    SUPER_ADMIN: frozenset(
        {
            # Account
            VIEW_OWN_PROFILE,
            UPDATE_OWN_PROFILE,

            # Verification
            VIEW_VERIFICATION,
            CREATE_VERIFICATION,
            REVIEW_VERIFICATION,
            APPROVE_VERIFICATION,
            REJECT_VERIFICATION,
            REQUEST_VERIFICATION_INFO,

            # Organization
            VIEW_ORGANIZATION,
            MANAGE_ORGANIZATION,
            MANAGE_ORGANIZATION_MEMBERS,

            # Jobs
            VIEW_JOBS,
            CREATE_JOB,
            UPDATE_JOB,
            PUBLISH_JOB,
            CLOSE_JOB,

            # Applications
            APPLY_FOR_JOB,
            VIEW_OWN_APPLICATIONS,
            VIEW_JOB_APPLICATIONS,
            MANAGE_JOB_APPLICATIONS,
            SHORTLIST_CANDIDATES,
            SELECT_CANDIDATES,

            # Assessments
            VIEW_ASSESSMENT,
            CREATE_ASSESSMENT,
            UPDATE_ASSESSMENT,
            MANAGE_ASSESSMENT_INVITATIONS,
            VIEW_ASSESSMENT_RESULTS,
            TAKE_ASSESSMENT,
            VIEW_OWN_ASSESSMENT_RESULTS,

            # Skills / Credentials
            VIEW_SKILLS,
            MANAGE_OWN_SKILLS,
            VERIFY_SKILLS,
            VIEW_CREDENTIALS,
            UPLOAD_CREDENTIALS,
            VERIFY_CREDENTIALS,

            # Courses
            VIEW_COURSES,
            CREATE_COURSE,
            UPDATE_COURSE,
            PUBLISH_COURSE,

            # Labour market
            VIEW_LABOUR_MARKET,
            ANALYZE_LABOUR_MARKET,
            MANAGE_LABOUR_MARKET,

            # Government analytics
            VIEW_GOVERNMENT_ANALYTICS,
            ANALYZE_GOVERNMENT_DATA,
            MANAGE_GOVERNMENT_DATA_ACCESS,

            # Following / notifications
            MANAGE_FOLLOWING,
            VIEW_NOTIFICATIONS,

            # Documents
            UPLOAD_DOCUMENT,
            VIEW_DOCUMENT,
            DOWNLOAD_DOCUMENT,

            # Audit
            VIEW_AUDIT_LOGS,

            # Administration
            MANAGE_USERS,
            MANAGE_ROLES,
            MANAGE_VERIFIERS,
        }
    ),


    # ========================================================
    # GOVERNMENT ADMIN
    # ========================================================

    GOVERNMENT_ADMIN: frozenset(
        {
            VIEW_OWN_PROFILE,
            UPDATE_OWN_PROFILE,

            VIEW_VERIFICATION,
            CREATE_VERIFICATION,
            REVIEW_VERIFICATION,
            APPROVE_VERIFICATION,
            REJECT_VERIFICATION,
            REQUEST_VERIFICATION_INFO,

            VIEW_ORGANIZATION,

            VIEW_JOBS,

            VIEW_SKILLS,
            VERIFY_SKILLS,

            VIEW_CREDENTIALS,
            VERIFY_CREDENTIALS,

            VIEW_COURSES,

            VIEW_LABOUR_MARKET,
            ANALYZE_LABOUR_MARKET,

            VIEW_GOVERNMENT_ANALYTICS,
            ANALYZE_GOVERNMENT_DATA,

            MANAGE_FOLLOWING,
            VIEW_NOTIFICATIONS,

            VIEW_DOCUMENT,
            DOWNLOAD_DOCUMENT,

            VIEW_AUDIT_LOGS,
        }
    ),


    # ========================================================
    # GOVERNMENT VERIFIER
    # ========================================================

    GOVERNMENT_VERIFIER: frozenset(
        {
            VIEW_OWN_PROFILE,
            UPDATE_OWN_PROFILE,

            VIEW_VERIFICATION,
            REVIEW_VERIFICATION,
            APPROVE_VERIFICATION,
            REJECT_VERIFICATION,
            REQUEST_VERIFICATION_INFO,

            VIEW_ORGANIZATION,
            VIEW_JOBS,

            VIEW_SKILLS,
            VERIFY_SKILLS,

            VIEW_CREDENTIALS,
            VERIFY_CREDENTIALS,

            VIEW_COURSES,

            VIEW_LABOUR_MARKET,
            VIEW_GOVERNMENT_ANALYTICS,

            MANAGE_FOLLOWING,
            VIEW_NOTIFICATIONS,

            VIEW_DOCUMENT,
            DOWNLOAD_DOCUMENT,
        }
    ),


    # ========================================================
    # EMPLOYER - ORGANIZATION ADMIN
    # ========================================================

    ORG_ADMIN: frozenset(
        {
            VIEW_OWN_PROFILE,
            UPDATE_OWN_PROFILE,

            VIEW_ORGANIZATION,
            MANAGE_ORGANIZATION,
            MANAGE_ORGANIZATION_MEMBERS,

            # Jobs
            VIEW_JOBS,
            CREATE_JOB,
            UPDATE_JOB,
            PUBLISH_JOB,
            CLOSE_JOB,

            # Applications
            VIEW_JOB_APPLICATIONS,
            MANAGE_JOB_APPLICATIONS,
            SHORTLIST_CANDIDATES,
            SELECT_CANDIDATES,

            # Assessments
            VIEW_ASSESSMENT,
            CREATE_ASSESSMENT,
            UPDATE_ASSESSMENT,
            MANAGE_ASSESSMENT_INVITATIONS,
            VIEW_ASSESSMENT_RESULTS,

            # Candidate information
            VIEW_SKILLS,
            VIEW_CREDENTIALS,
            VERIFY_CREDENTIALS,

            # Courses / labour market
            VIEW_COURSES,
            VIEW_LABOUR_MARKET,

            # Following / notifications
            MANAGE_FOLLOWING,
            VIEW_NOTIFICATIONS,

            # Documents
            UPLOAD_DOCUMENT,
            VIEW_DOCUMENT,
            DOWNLOAD_DOCUMENT,
        }
    ),


    # ========================================================
    # EMPLOYER - HR
    # ========================================================

    HR: frozenset(
        {
            VIEW_OWN_PROFILE,
            UPDATE_OWN_PROFILE,

            VIEW_ORGANIZATION,

            # Jobs
            VIEW_JOBS,
            CREATE_JOB,
            UPDATE_JOB,
            PUBLISH_JOB,
            CLOSE_JOB,

            # Applications
            VIEW_JOB_APPLICATIONS,
            MANAGE_JOB_APPLICATIONS,
            SHORTLIST_CANDIDATES,
            SELECT_CANDIDATES,

            # Assessments
            VIEW_ASSESSMENT,
            CREATE_ASSESSMENT,
            UPDATE_ASSESSMENT,
            MANAGE_ASSESSMENT_INVITATIONS,
            VIEW_ASSESSMENT_RESULTS,

            # Candidate information
            VIEW_SKILLS,
            VIEW_CREDENTIALS,
            VERIFY_CREDENTIALS,

            # Courses / labour market
            VIEW_COURSES,
            VIEW_LABOUR_MARKET,

            MANAGE_FOLLOWING,
            VIEW_NOTIFICATIONS,

            VIEW_DOCUMENT,
            DOWNLOAD_DOCUMENT,
        }
    ),


    # ========================================================
    # EMPLOYER - JOB POSTER
    # ========================================================

    JOB_POSTER: frozenset(
        {
            VIEW_OWN_PROFILE,
            UPDATE_OWN_PROFILE,

            VIEW_ORGANIZATION,

            # Jobs
            VIEW_JOBS,
            CREATE_JOB,
            UPDATE_JOB,
            PUBLISH_JOB,
            CLOSE_JOB,

            # Applications
            VIEW_JOB_APPLICATIONS,
            MANAGE_JOB_APPLICATIONS,
            SHORTLIST_CANDIDATES,
            SELECT_CANDIDATES,

            # Candidate information
            VIEW_SKILLS,
            VIEW_CREDENTIALS,

            VIEW_COURSES,

            MANAGE_FOLLOWING,
            VIEW_NOTIFICATIONS,
        }
    ),


    # ========================================================
    # ASSESSMENT MANAGER
    # ========================================================

    ASSESSMENT_MANAGER: frozenset(
        {
            VIEW_OWN_PROFILE,
            UPDATE_OWN_PROFILE,

            VIEW_ORGANIZATION,
            VIEW_JOBS,

            VIEW_ASSESSMENT,
            CREATE_ASSESSMENT,
            UPDATE_ASSESSMENT,
            MANAGE_ASSESSMENT_INVITATIONS,
            VIEW_ASSESSMENT_RESULTS,

            VIEW_SKILLS,
            VIEW_CREDENTIALS,

            # Needed to work with candidates associated
            # with employer applications.
            VIEW_JOB_APPLICATIONS,

            MANAGE_FOLLOWING,
            VIEW_NOTIFICATIONS,
        }
    ),


    # ========================================================
    # TRAINING INSTITUTION ADMIN
    # ========================================================

    INSTITUTION_ADMIN: frozenset(
        {
            VIEW_OWN_PROFILE,
            UPDATE_OWN_PROFILE,

            VIEW_ORGANIZATION,
            MANAGE_ORGANIZATION,
            MANAGE_ORGANIZATION_MEMBERS,

            # Courses
            VIEW_COURSES,
            CREATE_COURSE,
            UPDATE_COURSE,
            PUBLISH_COURSE,

            # Skills / credentials
            VIEW_SKILLS,
            VERIFY_SKILLS,
            VIEW_CREDENTIALS,
            VERIFY_CREDENTIALS,

            # Labour market
            VIEW_LABOUR_MARKET,
            ANALYZE_LABOUR_MARKET,

            MANAGE_FOLLOWING,
            VIEW_NOTIFICATIONS,

            # Documents
            UPLOAD_DOCUMENT,
            VIEW_DOCUMENT,
            DOWNLOAD_DOCUMENT,
        }
    ),


    # ========================================================
    # CANDIDATE
    # ========================================================

    CANDIDATE: frozenset(
        {
            VIEW_OWN_PROFILE,
            UPDATE_OWN_PROFILE,

            # Jobs
            VIEW_JOBS,

            # Applications
            APPLY_FOR_JOB,
            VIEW_OWN_APPLICATIONS,

            # Skills
            VIEW_SKILLS,
            MANAGE_OWN_SKILLS,

            # Credentials
            VIEW_CREDENTIALS,
            UPLOAD_CREDENTIALS,

            # Courses
            VIEW_COURSES,

            # Assessments
            TAKE_ASSESSMENT,

            # Following / notifications
            MANAGE_FOLLOWING,
            VIEW_NOTIFICATIONS,

            # Documents
            UPLOAD_DOCUMENT,
            VIEW_DOCUMENT,
            DOWNLOAD_DOCUMENT,
        }
    ),
}


# ============================================================
# Permission Utility Functions
# ============================================================

def get_permissions_for_roles(
    roles: Iterable[str],
) -> set[str]:
    """
    Return the union of all permissions granted
    by the supplied roles.
    """

    permissions: set[str] = set()

    for role in roles:
        permissions.update(
            ROLE_PERMISSIONS.get(
                role,
                frozenset(),
            )
        )

    return permissions


def has_role(
    roles: Iterable[str],
    required_role: str,
) -> bool:
    """
    Check whether a user has a specific role.
    """

    return required_role in set(roles)


def has_any_role(
    roles: Iterable[str],
    required_roles: Iterable[str],
) -> bool:
    """
    Check whether the user has at least one
    of the supplied roles.
    """

    current_roles = set(roles)
    required_roles_set = set(required_roles)

    return bool(
        current_roles.intersection(
            required_roles_set
        )
    )


def has_permission(
    roles: Iterable[str],
    permission: str,
) -> bool:
    """
    Check whether any supplied role grants
    the requested permission.
    """

    return permission in get_permissions_for_roles(
        roles
    )


def require_permission(
    roles: Iterable[str],
    permission: str,
) -> None:
    """
    Raise HTTP 403 when permission is missing.
    """

    if not has_permission(
        roles,
        permission,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You do not have permission to perform "
                f"this action: {permission}."
            ),
        )


def require_role(
    roles: Iterable[str],
    required_role: str,
) -> None:
    """
    Raise HTTP 403 when a required role is missing.
    """

    if not has_role(
        roles,
        required_role,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Required role is missing: "
                f"{required_role}."
            ),
        )


def require_any_role(
    roles: Iterable[str],
    required_roles: Iterable[str],
) -> None:
    """
    Raise HTTP 403 unless at least one required
    role is present.
    """

    required_roles_set = set(required_roles)

    if not has_any_role(
        roles,
        required_roles_set,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You do not have any of the required "
                "roles: "
                + ", ".join(
                    sorted(required_roles_set)
                )
                + "."
            ),
        )


# ============================================================
# FastAPI Authentication Dependency
# ============================================================

async def get_authenticated_user_and_roles(
    current_user_and_roles: tuple[
        User,
        list[str],
    ] = Depends(
        get_current_user_with_roles
    ),
) -> tuple[User, list[str]]:
    """
    Return the authenticated user and their
    active database roles.
    """

    return current_user_and_roles


# ============================================================
# FastAPI Permission Dependency Factory
# ============================================================

def require_permissions(
    *permissions: str,
) -> Callable[
    ...,
    Awaitable[tuple[User, list[str]]],
]:
    """
    FastAPI dependency factory.

    All supplied permissions are required.

    Example:

        current_user = Depends(
            require_permissions(
                APPLY_FOR_JOB
            )
        )
    """

    if not permissions:
        raise ValueError(
            "At least one permission is required."
        )

    async def dependency(
        current_user_and_roles: tuple[
            User,
            list[str],
        ] = Depends(
            get_current_user_with_roles
        ),
    ) -> tuple[User, list[str]]:

        current_user, roles = (
            current_user_and_roles
        )

        user_permissions = (
            get_permissions_for_roles(
                roles
            )
        )

        missing_permissions = [
            permission
            for permission in permissions
            if permission not in user_permissions
        ]

        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have the required "
                    "permission(s): "
                    + ", ".join(
                        missing_permissions
                    )
                    + "."
                ),
            )

        return current_user, roles

    return dependency


# ============================================================
# FastAPI Role Dependency Factory
# ============================================================

def require_roles(
    *required_roles: str,
) -> Callable[
    ...,
    Awaitable[tuple[User, list[str]]],
]:
    """
    FastAPI dependency factory.

    Access is granted when the authenticated
    user has at least one supplied role.
    """

    if not required_roles:
        raise ValueError(
            "At least one role is required."
        )

    async def dependency(
        current_user_and_roles: tuple[
            User,
            list[str],
        ] = Depends(
            get_current_user_with_roles
        ),
    ) -> tuple[User, list[str]]:

        current_user, roles = (
            current_user_and_roles
        )

        if not has_any_role(
            roles,
            required_roles,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have any of the "
                    "required roles: "
                    + ", ".join(
                        required_roles
                    )
                    + "."
                ),
            )

        return current_user, roles

    return dependency


# ============================================================
# Convenience Dependencies
# ============================================================

require_super_admin = require_roles(
    SUPER_ADMIN
)

require_government_admin = require_roles(
    GOVERNMENT_ADMIN
)

require_government_verifier = require_roles(
    GOVERNMENT_ADMIN,
    GOVERNMENT_VERIFIER,
    SUPER_ADMIN,
)

require_employer_manager = require_roles(
    ORG_ADMIN,
    HR,
    JOB_POSTER,
    ASSESSMENT_MANAGER,
    SUPER_ADMIN,
)

require_institution_admin = require_roles(
    INSTITUTION_ADMIN,
    SUPER_ADMIN,
)

require_candidate = require_roles(
    CANDIDATE
)

require_verification_reviewer = require_permissions(
    REVIEW_VERIFICATION
)

require_verification_approval = require_permissions(
    APPROVE_VERIFICATION
)

require_job_creation = require_permissions(
    CREATE_JOB
)

require_job_management = require_permissions(
    UPDATE_JOB
)

require_assessment_management = require_permissions(
    CREATE_ASSESSMENT
)

require_candidate_assessment = require_permissions(
    TAKE_ASSESSMENT
)

require_course_management = require_permissions(
    CREATE_COURSE
)

require_government_analytics = require_permissions(
    VIEW_GOVERNMENT_ANALYTICS
)

require_government_data_analysis = require_permissions(
    ANALYZE_GOVERNMENT_DATA
)

require_audit_access = require_permissions(
    VIEW_AUDIT_LOGS
)

# Candidate application
require_job_application = require_permissions(
    APPLY_FOR_JOB
)

require_own_applications = require_permissions(
    VIEW_OWN_APPLICATIONS
)

# Employer application management
require_job_application_view = require_permissions(
    VIEW_JOB_APPLICATIONS
)

require_job_application_management = require_permissions(
    MANAGE_JOB_APPLICATIONS
)


# ============================================================
# Permission Decorator
# ============================================================

def permission_required(
    *permissions: str,
) -> Callable[
    [Callable[..., Awaitable[Any]]],
    Callable[..., Awaitable[Any]],
]:
    """
    Optional service-layer permission decorator.

    The decorated function must receive a `roles`
    keyword argument containing an iterable of role codes.

    FastAPI dependencies remain preferred for API-level
    authorization.
    """

    if not permissions:
        raise ValueError(
            "At least one permission is required."
        )

    def decorator(
        function: Callable[..., Awaitable[Any]],
    ) -> Callable[..., Awaitable[Any]]:

        @wraps(function)
        async def wrapper(
            *args: Any,
            **kwargs: Any,
        ) -> Any:

            roles = kwargs.get("roles")

            if roles is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        "Authorization context is missing."
                    ),
                )

            user_permissions = (
                get_permissions_for_roles(
                    roles
                )
            )

            missing_permissions = [
                permission
                for permission in permissions
                if permission not in user_permissions
            ]

            if missing_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        "You do not have the required "
                        "permission(s): "
                        + ", ".join(
                            missing_permissions
                        )
                        + "."
                    ),
                )

            return await function(
                *args,
                **kwargs,
            )

        return wrapper

    return decorator
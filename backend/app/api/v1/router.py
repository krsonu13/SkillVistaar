from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from fastapi import APIRouter
from fastapi.routing import APIRoute, compile_path
import fastapi.routing as fr

from app.api.v1.endpoints import (
    admin,
    assessment_attempts,
    assessment_invitations,
    assessment_questions,
    assessment_results,
    assessments,
    audit_logs,
    auth,
    blockchain,
    candidate_credential_skills,
    candidate_credential_verification,
    candidate_credentials,
    candidate_skill_verification,
    candidate_skills,
    candidates,
    course_alignments,
    course_skills,
    courses,
    documents,
    emerging_skills,
    employer_matching,
    following,
    government,
    government_analytics,
    government_data_access,
    government_units,
    institutions,
    job_applications,
    job_matching,
    job_screening,
    jobs,
    labour_market,
    messages,
    notifications,
    organization_documents,
    organization_members,
    organizations,
    password,
    placement_outcomes,
    public_stats,
    recommendations,
    search,
    skill_gap,
    users,
    verification,
    verification_applications,
    verifier_authorizations,
    ws,
)

if TYPE_CHECKING:
    from fastapi import FastAPI


# ===========================================================================
# Master API v1 Router Definition
# ===========================================================================

api_router = APIRouter()

# ---------------------------------------------------------------------------
# Health Check (API v1)
# ---------------------------------------------------------------------------


@api_router.get("/health", tags=["Health"])
async def api_v1_health():
    """
    API v1 health status endpoint.
    """
    from app.core.config import settings
    from app.db.init_db import check_database_connection
    from app.services.otp_delivery_service import (
        validate_sms_configuration,
        validate_smtp_configuration,
    )

    database_healthy = await check_database_connection()
    smtp_status = validate_smtp_configuration()
    sms_status = validate_sms_configuration()

    overall_healthy = database_healthy

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "project": settings.PROJECT_NAME,
        "database": "connected" if database_healthy else "disconnected",
        "email_service": {
            "ready": smtp_status["ready"],
            "host": smtp_status["host"],
            "is_gmail": smtp_status["is_gmail"],
            "status": "configured" if smtp_status["ready"] else "unconfigured",
            "message": smtp_status["message"],
        },
        "sms_service": {
            "ready": sms_status["ready"],
            "provider": sms_status["provider"],
            "is_sandbox": sms_status.get("is_sandbox", False),
            "status": "configured" if sms_status["ready"] else "unconfigured",
            "message": sms_status["message"],
        },
    }


# ---------------------------------------------------------------------------
# Authentication & Users
# ---------------------------------------------------------------------------

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(search.router)
api_router.include_router(password.router)

# ---------------------------------------------------------------------------
# Government Hierarchy & Administration
# ---------------------------------------------------------------------------

api_router.include_router(government_units.router)
api_router.include_router(government.router)
api_router.include_router(admin.router)

# ---------------------------------------------------------------------------
# Verification & Authorizations
# ---------------------------------------------------------------------------

api_router.include_router(verification.router)
api_router.include_router(verification_applications.router)
api_router.include_router(verifier_authorizations.router)

# ---------------------------------------------------------------------------
# Organizations & Institutions
# ---------------------------------------------------------------------------

api_router.include_router(organizations.router)
api_router.include_router(organization_members.router)
api_router.include_router(institutions.router)

# ---------------------------------------------------------------------------
# Jobs & Applications
# ---------------------------------------------------------------------------

api_router.include_router(jobs.router)
api_router.include_router(job_applications.router)
api_router.include_router(job_screening.router)

# ---------------------------------------------------------------------------
# Candidates, Skills & Credentials
# ---------------------------------------------------------------------------

api_router.include_router(candidates.router)
api_router.include_router(candidate_skills.router)
api_router.include_router(candidate_skill_verification.router)
api_router.include_router(candidate_credentials.router)
api_router.include_router(candidate_credential_skills.router)
api_router.include_router(candidate_credential_verification.router)

# ---------------------------------------------------------------------------
# Courses & Course Alignments
# ---------------------------------------------------------------------------

api_router.include_router(courses.router)
api_router.include_router(course_skills.router)
api_router.include_router(course_alignments.router)

# ---------------------------------------------------------------------------
# Assessments & Invitations
# ---------------------------------------------------------------------------

api_router.include_router(assessments.router)
api_router.include_router(assessment_questions.router)
api_router.include_router(assessment_attempts.router)
api_router.include_router(assessment_results.router)
api_router.include_router(assessment_invitations.router)

# ---------------------------------------------------------------------------
# Notifications, Followings & Messaging
# ---------------------------------------------------------------------------

api_router.include_router(notifications.router)
api_router.include_router(following.router)
api_router.include_router(messages.router)
api_router.include_router(ws.router)

# ---------------------------------------------------------------------------
# Government Data Access & Audit Logs
# ---------------------------------------------------------------------------

api_router.include_router(government_data_access.router)
api_router.include_router(audit_logs.router)

# ---------------------------------------------------------------------------
# Public Platform Stats & Analytics
# ---------------------------------------------------------------------------

api_router.include_router(public_stats.router)
api_router.include_router(recommendations.router)
api_router.include_router(labour_market.router)
api_router.include_router(government_analytics.router)
api_router.include_router(emerging_skills.router)
api_router.include_router(skill_gap.router)
api_router.include_router(job_matching.router)
api_router.include_router(employer_matching.router)
api_router.include_router(placement_outcomes.router)

# ---------------------------------------------------------------------------
# Documents & Blockchain
# ---------------------------------------------------------------------------

api_router.include_router(documents.router)
api_router.include_router(organization_documents.router)
api_router.include_router(blockchain.router)


# ===========================================================================
# Router Registration Helper
# ===========================================================================


def register_api_router(app: FastAPI, router: APIRouter, prefix: str = "/api/v1") -> None:
    """
    Register all routes from an APIRouter directly onto the FastAPI application
    as concrete APIRoutes with compiled paths.

    In FastAPI 0.141+, calling `app.include_router(router, prefix=...)` inserts
    an `_IncludedRouter` into `app.routes`. Because `_IncludedRouter` lacks a
    `.path` attribute, route inspection tools and scripts filtering for `hasattr(r, 'path')`
    see only root endpoints.

    This function flattens and mounts each route as a full APIRoute instance with
    its complete prefix in `app.router.routes`. All dependencies, tags, response
    models, validation, and handlers are perfectly preserved.
    """
    clean_prefix = prefix.rstrip("/")

    for orig_route, ctx in fr._iter_routes_with_context(router.routes):
        if isinstance(orig_route, APIRoute):
            sub_path = ctx.path if ctx else orig_route.path
            full_path = f"{clean_prefix}{sub_path}".replace("//", "/")

            route_copy = copy.copy(orig_route)
            route_copy.path = full_path
            (
                route_copy.path_regex,
                route_copy.path_format,
                route_copy.param_convertors,
            ) = compile_path(route_copy.path)

            if ctx and ctx.tags:
                route_copy.tags = list(
                    dict.fromkeys(list(route_copy.tags or []) + list(ctx.tags))
                )

            app.router.routes.append(route_copy)
        elif isinstance(orig_route, fr.APIWebSocketRoute):
            sub_path = ctx.path if ctx else orig_route.path
            full_path = f"{clean_prefix}{sub_path}".replace("//", "/")

            ws_copy = copy.copy(orig_route)
            ws_copy.path = full_path
            (
                ws_copy.path_regex,
                ws_copy.path_format,
                ws_copy.param_convertors,
            ) = compile_path(ws_copy.path)
            app.router.routes.append(ws_copy)
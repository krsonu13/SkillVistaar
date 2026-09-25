"""Import all SQLAlchemy models for metadata discovery.

This module must be imported after app.db.base.Base exists.
"""

from app.models.assessment import Assessment
from app.models.assessment_answer import AssessmentAnswer
from app.models.assessment_attempt import AssessmentAttempt
from app.models.assessment_invitation import AssessmentInvitation
from app.models.assessment_question import AssessmentQuestion
from app.models.audit_log import AuditLog
from app.models.auth_session import AuthSession

from app.models.candidate_credential import CandidateCredential
from app.models.candidate_credential_skill import CandidateCredentialSkill
from app.models.candidate_profile import CandidateProfile
from app.models.candidate_skill import CandidateSkill

from app.models.course import Course
from app.models.course_alignment import CourseAlignment
from app.models.course_skill import CourseSkill

from app.models.document import PrivateDocument
from app.models.emerging_skill_trend import EmergingSkillTrend
from app.models.following import Following

from app.models.government_data_access_authorization import (
    GovernmentDataAccessAuthorization,
)
from app.models.government_unit import GovernmentUnit

from app.models.institution_profile import InstitutionProfile

# Employer / job models.
from app.models.job import Job
from app.models.job_skill_requirement import JobSkillRequirement
from app.models.job_screening_question import JobScreeningQuestion

# Import the status-history model before JobApplication so that the
# relationship target is registered during SQLAlchemy model discovery.
from app.models.application_status_history import ApplicationStatusHistory
from app.models.job_application import JobApplication

from app.models.labour_market_snapshot import LabourMarketSnapshot
from app.models.labour_market_source import LabourMarketSource
from app.models.notification import Notification
from app.models.user_notification_preference import UserNotificationPreference
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.placement_outcome import PlacementOutcome
from app.models.role import Role
from app.models.skill import Skill
from app.models.user import User
from app.models.user_role import UserRole
from app.models.signup_session import SignupVerificationSession
from app.models.verification_application import VerificationApplication
from app.models.verification_challenge import VerificationChallenge
from app.models.verifier_authorization import VerifierAuthorization


__all__ = [
    "Assessment",
    "AssessmentAnswer",
    "AssessmentAttempt",
    "AssessmentInvitation",
    "AssessmentQuestion",
    "AuditLog",
    "AuthSession",
    "CandidateCredential",
    "CandidateCredentialSkill",
    "CandidateProfile",
    "CandidateSkill",
    "Course",
    "CourseAlignment",
    "CourseSkill",
    "PrivateDocument",
    "EmergingSkillTrend",
    "Following",
    "GovernmentDataAccessAuthorization",
    "GovernmentUnit",
    "InstitutionProfile",
    "Job",
    "JobSkillRequirement",
    "JobScreeningQuestion",
    "ApplicationStatusHistory",
    "JobApplication",
    "LabourMarketSnapshot",
    "LabourMarketSource",
    "Notification",
    "Organization",
    "OrganizationMember",
    "PlacementOutcome",
    "Role",
    "SignupVerificationSession",
    "Skill",
    "User",
    "UserRole",
    "VerificationApplication",
    "VerificationChallenge",
    "VerifierAuthorization",
]

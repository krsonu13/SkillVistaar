"""SkillVistaar SQLAlchemy model registry.

Importing this package registers every ORM model with the shared
DeclarativeBase metadata. Individual model modules should import
Base from app.db.base and should not import this package.
"""

from app.models.application_status_history import ApplicationStatusHistory
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
from app.models.conversation import Conversation, ConversationStatus
from app.models.course import Course
from app.models.course_alignment import CourseAlignment
from app.models.course_skill import CourseSkill
from app.models.document import PrivateDocument
from app.models.emerging_skill_trend import EmergingSkillTrend
from app.models.following import Following
from app.models.message import Message
from app.models.government_data_access_authorization import (
    GovernmentDataAccessAuthorization,
)
from app.models.government_unit import GovernmentUnit
from app.models.institution_profile import InstitutionProfile
from app.models.job import Job
from app.models.job_application import JobApplication
from app.models.job_screening_question import JobScreeningQuestion
from app.models.job_skill_requirement import JobSkillRequirement
from app.models.labour_market_snapshot import LabourMarketSnapshot
from app.models.labour_market_source import LabourMarketSource
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.organization_document import (
    OrgDocumentStatus,
    OrgDocumentType,
    OrganizationDocument,
    OrganizationDocumentHistory,
)
from app.models.organization_member import OrganizationMember
from app.models.placement_outcome import PlacementOutcome
from app.models.role import Role
from app.models.skill import Skill
from app.models.user import User
from app.models.user_notification_preference import UserNotificationPreference
from app.models.user_role import UserRole
from app.models.platform_config import PlatformConfig
from app.models.signup_session import SignupVerificationSession
from app.models.user_warning import UserWarning
from app.models.verification_application import VerificationApplication
from app.models.verification_challenge import VerificationChallenge
from app.models.verifier_authorization import VerifierAuthorization

__all__ = [
    "ApplicationStatusHistory",
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
    "Conversation",
    "ConversationStatus",
    "Course",
    "CourseAlignment",
    "CourseSkill",
    "EmergingSkillTrend",
    "Following",
    "Message",
    "GovernmentDataAccessAuthorization",
    "GovernmentUnit",
    "InstitutionProfile",
    "Job",
    "JobApplication",
    "JobScreeningQuestion",
    "JobSkillRequirement",
    "LabourMarketSnapshot",
    "LabourMarketSource",
    "Notification",
    "OrgDocumentStatus",
    "OrgDocumentType",
    "Organization",
    "OrganizationDocument",
    "OrganizationDocumentHistory",
    "OrganizationMember",
    "PlacementOutcome",
    "PlatformConfig",
    "PrivateDocument",
    "Role",
    "SignupVerificationSession",
    "Skill",
    "User",
    "UserNotificationPreference",
    "UserRole",
    "UserWarning",
    "VerificationApplication",
    "VerificationChallenge",
    "VerifierAuthorization",
]

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.assessment_question import (
    AssessmentQuestion,
    AssessmentQuestionType,
)
from app.models.organization import (
    Organization,
    OrganizationVerificationStatus,
)
from app.models.organization_member import (
    OrganizationMember,
    OrganizationMemberRole,
)
from app.models.skill import Skill
from app.models.user import User


class AssessmentQuestionServiceError(Exception):
    """Base assessment question service error."""


class AssessmentQuestionNotFoundError(
    AssessmentQuestionServiceError
):
    """Question or assessment was not found."""


class AssessmentQuestionAccessDeniedError(
    AssessmentQuestionServiceError
):
    """User does not have permission."""


class AssessmentQuestionValidationError(
    AssessmentQuestionServiceError
):
    """Question data is invalid."""


class AssessmentQuestionService:
    """Business logic for assessment questions."""

    MANAGER_ROLES = {
        OrganizationMemberRole.ORG_ADMIN.value,
        OrganizationMemberRole.HR.value,
        OrganizationMemberRole.ASSESSMENT_MANAGER.value,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_assessment(
        self,
        assessment_id: uuid.UUID,
    ) -> Assessment:
        result = await self.db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id
            )
        )

        assessment = result.scalar_one_or_none()

        if assessment is None:
            raise AssessmentQuestionNotFoundError(
                "Assessment not found."
            )

        return assessment

    async def get_question(
        self,
        question_id: uuid.UUID,
    ) -> AssessmentQuestion:
        result = await self.db.execute(
            select(AssessmentQuestion).where(
                AssessmentQuestion.id == question_id
            )
        )

        question = result.scalar_one_or_none()

        if question is None:
            raise AssessmentQuestionNotFoundError(
                "Assessment question not found."
            )

        return question

    async def get_organization(
        self,
        organization_id: uuid.UUID,
    ) -> Organization:
        result = await self.db.execute(
            select(Organization).where(
                Organization.id == organization_id
            )
        )

        organization = result.scalar_one_or_none()

        if organization is None:
            raise AssessmentQuestionValidationError(
                "Assessment organization not found."
            )

        return organization

    async def ensure_manager_access(
        self,
        user: User,
        assessment: Assessment,
    ) -> Organization:
        organization = await self.get_organization(
            assessment.organization_id
        )

        if organization.organization_type.value != "EMPLOYER":
            raise AssessmentQuestionAccessDeniedError(
                "Only employer organizations can manage "
                "job assessments."
            )

        if (
            organization.verification_status
            != OrganizationVerificationStatus.APPROVED.value
        ):
            raise AssessmentQuestionAccessDeniedError(
                "Employer organization is not approved."
            )

        result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id
                == organization.id,
                OrganizationMember.user_id == user.id,
                OrganizationMember.is_active.is_(True),
                OrganizationMember.role_code.in_(
                    self.MANAGER_ROLES
                ),
            )
        )

        membership = result.scalar_one_or_none()

        if membership is None:
            raise AssessmentQuestionAccessDeniedError(
                "You do not have permission to manage "
                "this assessment."
            )

        return organization

    @staticmethod
    def validate_question_data(
        question_text: str,
        question_type: AssessmentQuestionType,
        options: list[str] | None,
        correct_answer: str | None,
        marks: int,
        negative_marks: float,
    ) -> None:
        if not question_text.strip():
            raise AssessmentQuestionValidationError(
                "Question text cannot be empty."
            )

        if marks < 1:
            raise AssessmentQuestionValidationError(
                "Marks must be at least 1."
            )

        if negative_marks < 0:
            raise AssessmentQuestionValidationError(
                "Negative marks cannot be negative."
            )

        if question_type in {
            AssessmentQuestionType.MCQ,
            AssessmentQuestionType.MULTIPLE_SELECT,
        }:
            if not options or len(options) < 2:
                raise AssessmentQuestionValidationError(
                    "MCQ questions require at least two options."
                )

            cleaned_options = [
                option.strip()
                for option in options
                if option.strip()
            ]

            if len(cleaned_options) != len(set(cleaned_options)):
                raise AssessmentQuestionValidationError(
                    "Question options must be unique."
                )

        if question_type == AssessmentQuestionType.TRUE_FALSE:
            if options is not None and set(options) != {
                "True",
                "False",
            }:
                raise AssessmentQuestionValidationError(
                    "True/False questions must use True and False."
                )

        if not correct_answer or not correct_answer.strip():
            raise AssessmentQuestionValidationError(
                "Correct answer is required."
            )

    async def validate_skill(
        self,
        skill_id: uuid.UUID | None,
    ) -> Skill | None:
        if skill_id is None:
            return None

        result = await self.db.execute(
            select(Skill).where(
                Skill.id == skill_id,
                Skill.is_active.is_(True),
            )
        )

        skill = result.scalar_one_or_none()

        if skill is None:
            raise AssessmentQuestionValidationError(
                "Selected skill does not exist or is inactive."
            )

        return skill

    async def ensure_sequence_available(
        self,
        assessment_id: uuid.UUID,
        sequence_number: int,
        exclude_question_id: uuid.UUID | None = None,
    ) -> None:
        query = select(AssessmentQuestion).where(
            AssessmentQuestion.assessment_id == assessment_id,
            AssessmentQuestion.sequence_number
            == sequence_number,
        )

        if exclude_question_id is not None:
            query = query.where(
                AssessmentQuestion.id != exclude_question_id
            )

        result = await self.db.execute(query)

        if result.scalar_one_or_none() is not None:
            raise AssessmentQuestionValidationError(
                "This question sequence number is already used."
            )

    async def create_question(
        self,
        user: User,
        assessment_id: uuid.UUID,
        question_text: str,
        question_type: AssessmentQuestionType,
        difficulty: str,
        options: list[str] | None,
        correct_answer: str,
        explanation: str | None,
        marks: int,
        negative_marks: float,
        skill_id: uuid.UUID | None,
        sequence_number: int,
    ) -> AssessmentQuestion:
        assessment = await self.get_assessment(
            assessment_id
        )

        await self.ensure_manager_access(
            user,
            assessment,
        )

        if assessment.status in {
            AssessmentStatus.PUBLISHED.value,
            AssessmentStatus.ARCHIVED.value,
        }:
            raise AssessmentQuestionValidationError(
                "Questions cannot be added to a published "
                "or archived assessment."
            )

        self.validate_question_data(
            question_text=question_text,
            question_type=question_type,
            options=options,
            correct_answer=correct_answer,
            marks=marks,
            negative_marks=negative_marks,
        )

        await self.validate_skill(skill_id)

        await self.ensure_sequence_available(
            assessment_id=assessment.id,
            sequence_number=sequence_number,
        )

        if question_type == AssessmentQuestionType.TRUE_FALSE:
            options = ["True", "False"]

        question = AssessmentQuestion(
            assessment_id=assessment.id,
            question_text=question_text.strip(),
            question_type=question_type.value,
            difficulty=difficulty,
            options=options,
            correct_answer=correct_answer.strip(),
            explanation=explanation,
            marks=marks,
            negative_marks=negative_marks,
            skill_id=skill_id,
            sequence_number=sequence_number,
            is_active=True,
        )

        self.db.add(question)

        await self.db.commit()
        await self.db.refresh(question)

        await self.recalculate_assessment_marks(
            assessment.id
        )

        return question

    async def update_question(
        self,
        user: User,
        question_id: uuid.UUID,
        **updates,
    ) -> AssessmentQuestion:
        question = await self.get_question(
            question_id
        )

        assessment = await self.get_assessment(
            question.assessment_id
        )

        await self.ensure_manager_access(
            user,
            assessment,
        )

        if assessment.status in {
            AssessmentStatus.PUBLISHED.value,
            AssessmentStatus.ARCHIVED.value,
        }:
            raise AssessmentQuestionValidationError(
                "Published or archived assessments cannot "
                "have their questions modified."
            )

        question_type = updates.get(
            "question_type",
            question.question_type,
        )

        if isinstance(question_type, AssessmentQuestionType):
            question_type = question_type.value

        options = updates.get(
            "options",
            question.options,
        )

        correct_answer = updates.get(
            "correct_answer",
            question.correct_answer,
        )

        question_text = updates.get(
            "question_text",
            question.question_text,
        )

        marks = updates.get(
            "marks",
            question.marks,
        )

        negative_marks = updates.get(
            "negative_marks",
            question.negative_marks,
        )

        try:
            question_type_enum = AssessmentQuestionType(
                question_type
            )
        except ValueError as exc:
            raise AssessmentQuestionValidationError(
                "Invalid question type."
            ) from exc

        self.validate_question_data(
            question_text=question_text,
            question_type=question_type_enum,
            options=options,
            correct_answer=correct_answer,
            marks=marks,
            negative_marks=negative_marks,
        )

        if "skill_id" in updates:
            await self.validate_skill(
                updates["skill_id"]
            )

        if "sequence_number" in updates:
            await self.ensure_sequence_available(
                assessment_id=assessment.id,
                sequence_number=updates["sequence_number"],
                exclude_question_id=question.id,
            )

        for field, value in updates.items():
            if field == "question_type":
                value = (
                    value.value
                    if isinstance(
                        value,
                        AssessmentQuestionType,
                    )
                    else value
                )

            if field == "question_text" and value:
                value = value.strip()

            if field == "correct_answer" and value:
                value = value.strip()

            setattr(question, field, value)

        if question.question_type == (
            AssessmentQuestionType.TRUE_FALSE.value
        ):
            question.options = ["True", "False"]

        await self.db.commit()
        await self.db.refresh(question)

        await self.recalculate_assessment_marks(
            assessment.id
        )

        return question

    async def delete_question(
        self,
        user: User,
        question_id: uuid.UUID,
    ) -> None:
        question = await self.get_question(
            question_id
        )

        assessment = await self.get_assessment(
            question.assessment_id
        )

        await self.ensure_manager_access(
            user,
            assessment,
        )

        if assessment.status in {
            AssessmentStatus.PUBLISHED.value,
            AssessmentStatus.ARCHIVED.value,
        }:
            raise AssessmentQuestionValidationError(
                "Published or archived assessments cannot "
                "have questions deleted."
            )

        question.is_active = False

        await self.db.commit()

        await self.recalculate_assessment_marks(
            assessment.id
        )

    async def list_questions(
        self,
        assessment_id: uuid.UUID,
        include_inactive: bool = False,
    ) -> tuple[list[AssessmentQuestion], int]:
        await self.get_assessment(assessment_id)

        conditions = [
            AssessmentQuestion.assessment_id
            == assessment_id
        ]

        if not include_inactive:
            conditions.append(
                AssessmentQuestion.is_active.is_(True)
            )

        count_result = await self.db.execute(
            select(func.count(AssessmentQuestion.id))
            .where(*conditions)
        )

        total = count_result.scalar_one()

        result = await self.db.execute(
            select(AssessmentQuestion)
            .where(*conditions)
            .order_by(
                AssessmentQuestion.sequence_number.asc()
            )
        )

        return list(result.scalars().all()), total

    async def list_candidate_questions(
        self,
        assessment_id: uuid.UUID,
    ) -> tuple[list[AssessmentQuestion], int]:
        """
        Candidate-safe question retrieval.

        The API layer must serialize these using the
        candidate-safe schema and never expose correct_answer.
        """

        assessment = await self.get_assessment(
            assessment_id
        )

        if assessment.status != AssessmentStatus.PUBLISHED.value:
            raise AssessmentQuestionValidationError(
                "Assessment is not available."
            )

        return await self.list_questions(
            assessment_id=assessment_id,
            include_inactive=False,
        )

    async def recalculate_assessment_marks(
        self,
        assessment_id: uuid.UUID,
    ) -> None:
        result = await self.db.execute(
            select(
                func.coalesce(
                    func.sum(AssessmentQuestion.marks),
                    0,
                )
            ).where(
                AssessmentQuestion.assessment_id
                == assessment_id,
                AssessmentQuestion.is_active.is_(True),
            )
        )

        total_marks = result.scalar_one()

        assessment = await self.get_assessment(
            assessment_id
        )

        assessment.total_marks = int(
            total_marks or 0
        )

        await self.db.commit()
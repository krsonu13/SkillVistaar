from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssessmentQuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=1, max_length=10000)
    question_type: str = Field(default="MCQ", max_length=40)
    difficulty: str = Field(default="MEDIUM", max_length=20)

    options: list[str] | None = None
    correct_answer: str | None = None
    explanation: str | None = None

    marks: int = Field(default=1, ge=1)
    negative_marks: float = Field(default=0, ge=0)

    skill_id: str | None = None
    sequence_number: int = Field(..., ge=1)

    is_active: bool = True

    @model_validator(mode="after")
    def validate_question(self):
        question_type = self.question_type.upper()

        if question_type in {"MCQ", "MULTIPLE_SELECT"}:
            if not self.options or len(self.options) < 2:
                raise ValueError(
                    "MCQ and multiple-select questions require at least 2 options."
                )

        if question_type == "TRUE_FALSE":
            self.options = ["True", "False"]

        if question_type == "SHORT_ANSWER":
            if not self.correct_answer:
                raise ValueError(
                    "Short-answer questions require a correct answer."
                )

        if not self.correct_answer:
            raise ValueError("Correct answer is required.")

        return self


class AssessmentQuestionUpdate(BaseModel):
    question_text: str | None = Field(
        default=None,
        min_length=1,
        max_length=10000,
    )
    question_type: str | None = Field(
        default=None,
        max_length=40,
    )
    difficulty: str | None = Field(
        default=None,
        max_length=20,
    )

    options: list[str] | None = None
    correct_answer: str | None = None
    explanation: str | None = None

    marks: int | None = Field(
        default=None,
        ge=1,
    )
    negative_marks: float | None = Field(
        default=None,
        ge=0,
    )

    skill_id: str | None = None
    sequence_number: int | None = Field(
        default=None,
        ge=1,
    )

    is_active: bool | None = None


class AssessmentQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assessment_id: str

    question_text: str
    question_type: str
    difficulty: str

    options: list[str] | None = None
    correct_answer: str | None = None
    explanation: str | None = None

    marks: int
    negative_marks: float

    skill_id: str | None = None
    sequence_number: int
    is_active: bool


class AssessmentQuestionCandidateResponse(BaseModel):
    """
    Candidate-safe question response.

    IMPORTANT:
    correct_answer and explanation are deliberately excluded.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    assessment_id: str

    question_text: str
    question_type: str
    difficulty: str

    options: list[str] | None = None

    marks: int
    negative_marks: float

    skill_id: str | None = None
    sequence_number: int


class AssessmentQuestionListResponse(BaseModel):
    items: list[AssessmentQuestionResponse]
    total: int


class AssessmentQuestionCandidateListResponse(BaseModel):
    items: list[AssessmentQuestionCandidateResponse]
    total: int
"""link job skill requirements to skills

Revision ID: replace_this_revision
Revises: a0d566c52e05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "58e59c2e2eaa"
down_revision: str | None = "a0d566c52e05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add the new skill_id column as nullable temporarily.
    op.add_column(
        "job_skill_requirements",
        sa.Column(
            "skill_id",
            sa.UUID(),
            nullable=True,
        ),
    )

    # 2. Create Skill records from existing skill names.
    op.execute(
        """
        INSERT INTO skills (
            id,
            name,
            normalized_name,
            skill_type,
            status,
            is_verified,
            is_active
        )
        SELECT
            gen_random_uuid(),
            skill_name,
            lower(trim(skill_name)),
            'OTHER',
            'ACTIVE',
            false,
            true
        FROM job_skill_requirements
        WHERE skill_name IS NOT NULL
          AND trim(skill_name) <> ''
          AND lower(trim(skill_name)) NOT IN (
              SELECT normalized_name
              FROM skills
          )
        """
    )

    # 3. Connect existing job requirements to the new Skill records.
    op.execute(
        """
        UPDATE job_skill_requirements AS jsr
        SET skill_id = s.id
        FROM skills AS s
        WHERE lower(trim(jsr.skill_name)) = s.normalized_name
        """
    )

    # 4. Existing rows must now have a valid skill.
    op.alter_column(
        "job_skill_requirements",
        "skill_id",
        nullable=False,
    )

    # 5. Replace the old uniqueness rule.
    op.drop_constraint(
        "uq_job_skill_requirement",
        "job_skill_requirements",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_job_skill_requirement",
        "job_skill_requirements",
        ["job_id", "skill_id"],
    )

    # 6. Add the new skill index and foreign key.
    op.create_index(
        "ix_job_skill_requirements_skill",
        "job_skill_requirements",
        ["skill_id"],
    )

    op.create_foreign_key(
        "fk_job_skill_requirements_skill_id",
        "job_skill_requirements",
        "skills",
        ["skill_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # 7. Remove the old free-text column.
    op.drop_column(
        "job_skill_requirements",
        "skill_name",
    )


def downgrade() -> None:
    # Recreate skill_name.
    op.add_column(
        "job_skill_requirements",
        sa.Column(
            "skill_name",
            sa.String(length=255),
            nullable=True,
        ),
    )

    # Restore names from Skill.
    op.execute(
        """
        UPDATE job_skill_requirements AS jsr
        SET skill_name = s.name
        FROM skills AS s
        WHERE jsr.skill_id = s.id
        """
    )

    op.alter_column(
        "job_skill_requirements",
        "skill_name",
        nullable=False,
    )

    op.drop_constraint(
        "fk_job_skill_requirements_skill_id",
        "job_skill_requirements",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_job_skill_requirements_skill",
        table_name="job_skill_requirements",
    )

    op.drop_constraint(
        "uq_job_skill_requirement",
        "job_skill_requirements",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_job_skill_requirement",
        "job_skill_requirements",
        ["job_id", "skill_name"],
    )

    op.drop_column(
        "job_skill_requirements",
        "skill_id",
    )
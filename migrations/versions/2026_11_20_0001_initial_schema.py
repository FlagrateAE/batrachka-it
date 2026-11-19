"""initial schema: users, candidates, recruiters, vacancies, applications

Revision ID: 0001
Revises:
Create Date: 2026-11-20 10:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = postgresql.ENUM("CANDIDATE", "RECRUITER", name="user_role", create_type=False)
tech_domain = postgresql.ENUM(
    "PYTHON",
    "DOTNET",
    "JAVA",
    "GAMEDEV",
    "PROJECT_MANAGEMENT",
    "QA",
    "EMBEDDED",
    name="tech_domain",
    create_type=False,
)
company_type = postgresql.ENUM(
    "PRODUCT", "OUTSOURCE", "OUTSTAFF", "STARTUP", name="company_type", create_type=False
)
work_format = postgresql.ENUM("REMOTE", "OFFICE", "HYBRID", name="work_format", create_type=False)
english_level = postgresql.ENUM(
    "NO_ENGLISH",
    "BEGINNER",
    "PRE_INTERMEDIATE",
    "INTERMEDIATE",
    "UPPER_INTERMEDIATE",
    "ADVANCED",
    "PROFICIENT",
    name="english_level",
    create_type=False,
)
vacancy_status = postgresql.ENUM("OPEN", "CLOSED", name="vacancy_status", create_type=False)
application_status = postgresql.ENUM(
    "PENDING", "ACCEPTED", "REJECTED", "HIRED", name="application_status", create_type=False
)

ENUM_TYPES = (
    user_role,
    tech_domain,
    company_type,
    work_format,
    english_level,
    vacancy_status,
    application_status,
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in ENUM_TYPES:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.String(length=2048), nullable=True),
        sa.Column("contact_info", sa.String(length=255), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("user_id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "candidates",
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("domain", tech_domain, nullable=False),
        sa.Column("experience_years", sa.Integer(), nullable=False),
        sa.Column("english_level", english_level, nullable=False),
        sa.Column("expected_salary", sa.Integer(), nullable=False),
        sa.Column("resume_text", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "experience_years >= 0", name=op.f("ck_candidates_experience_years_non_negative")
        ),
        sa.CheckConstraint(
            "expected_salary >= 0", name=op.f("ck_candidates_expected_salary_non_negative")
        ),
        sa.CheckConstraint("age BETWEEN 14 AND 100", name=op.f("ck_candidates_age_range")),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["users.user_id"],
            name="fk_candidates_candidate_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("candidate_id", name="pk_candidates"),
    )

    op.create_table(
        "recruiters",
        sa.Column("recruiter_id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(length=150), nullable=False),
        sa.ForeignKeyConstraint(
            ["recruiter_id"],
            ["users.user_id"],
            name="fk_recruiters_recruiter_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("recruiter_id", name="pk_recruiters"),
    )

    op.create_table(
        "vacancies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recruiter_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("domain", tech_domain, nullable=False),
        sa.Column("company_type", company_type, nullable=False),
        sa.Column("work_format", work_format, nullable=False),
        sa.Column("experience_years_required", sa.Integer(), nullable=False),
        sa.Column("english_level_required", english_level, nullable=False),
        sa.Column("salary_min", sa.Integer(), nullable=False),
        sa.Column("salary_max", sa.Integer(), nullable=False),
        sa.Column("status", vacancy_status, server_default="OPEN", nullable=False),
        *_timestamps(),
        sa.CheckConstraint("salary_min >= 0", name=op.f("ck_vacancies_salary_min_non_negative")),
        sa.CheckConstraint(
            "salary_max >= salary_min", name=op.f("ck_vacancies_salary_range_valid")
        ),
        sa.CheckConstraint(
            "experience_years_required >= 0", name=op.f("ck_vacancies_experience_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["recruiter_id"],
            ["recruiters.recruiter_id"],
            name="fk_vacancies_recruiter_id_recruiters",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_vacancies"),
    )
    op.create_index("ix_vacancies_recruiter_id", "vacancies", ["recruiter_id"])
    op.create_index("ix_vacancies_status_domain", "vacancies", ["status", "domain"])
    op.create_index("ix_vacancies_status_created_at", "vacancies", ["status", "created_at"])
    op.create_index("ix_vacancies_status_salary_max", "vacancies", ["status", "salary_max"])
    op.create_index("ix_vacancies_salary_min", "vacancies", ["salary_min"])
    op.create_index(
        "ix_vacancies_experience_years_required", "vacancies", ["experience_years_required"]
    )

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vacancy_id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("cover_letter", sa.Text(), nullable=True),
        sa.Column("status", application_status, server_default="PENDING", nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["vacancy_id"],
            ["vacancies.id"],
            name="fk_applications_vacancy_id_vacancies",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.candidate_id"],
            name="fk_applications_candidate_id_candidates",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_applications"),
        sa.UniqueConstraint(
            "vacancy_id", "candidate_id", name="uq_applications_vacancy_id_candidate_id"
        ),
    )
    op.create_index("ix_applications_candidate_id", "applications", ["candidate_id"])
    op.create_index("ix_applications_vacancy_id_status", "applications", ["vacancy_id", "status"])


def downgrade() -> None:
    op.drop_table("applications")
    op.drop_table("vacancies")
    op.drop_table("recruiters")
    op.drop_table("candidates")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_type in reversed(ENUM_TYPES):
        enum_type.drop(bind, checkfirst=True)

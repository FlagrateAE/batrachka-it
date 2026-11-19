from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.db import (
    Base,
    TimestampMixin,
    company_type_type,
    english_level_type,
    tech_domain_type,
    vacancy_status_type,
    work_format_type,
)
from app.common.enums import CompanyType, EnglishLevel, TechDomain, VacancyStatus, WorkFormat

if TYPE_CHECKING:
    from app.users.models import Recruiter


class Vacancy(TimestampMixin, Base):
    __tablename__ = "vacancies"
    __table_args__ = (
        CheckConstraint("salary_min >= 0", name="salary_min_non_negative"),
        CheckConstraint("salary_max >= salary_min", name="salary_range_valid"),
        CheckConstraint("experience_years_required >= 0", name="experience_non_negative"),
        Index("ix_vacancies_status_domain", "status", "domain"),
        Index("ix_vacancies_status_created_at", "status", "created_at"),
        Index("ix_vacancies_status_salary_max", "status", "salary_max"),
        Index("ix_vacancies_salary_min", "salary_min"),
        Index("ix_vacancies_experience_years_required", "experience_years_required"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    recruiter_id: Mapped[int] = mapped_column(
        ForeignKey("recruiters.recruiter_id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    domain: Mapped[TechDomain] = mapped_column(tech_domain_type)
    company_type: Mapped[CompanyType] = mapped_column(company_type_type)
    work_format: Mapped[WorkFormat] = mapped_column(work_format_type)
    experience_years_required: Mapped[int]
    english_level_required: Mapped[EnglishLevel] = mapped_column(english_level_type)
    salary_min: Mapped[int]
    salary_max: Mapped[int]
    status: Mapped[VacancyStatus] = mapped_column(
        vacancy_status_type, default=VacancyStatus.OPEN, server_default=VacancyStatus.OPEN.value
    )

    recruiter: Mapped[Recruiter] = relationship(lazy="raise")

    @property
    def company_name(self) -> str:
        return self.recruiter.company_name

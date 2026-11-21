from datetime import datetime
from typing import ClassVar, Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.common.enums import CompanyType, EnglishLevel, TechDomain, VacancyStatus, WorkFormat
from app.common.schemas import ORMModel, PageParams, PatchModel

SALARY_LIMIT = 1_000_000


class VacancyCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=20_000)
    domain: TechDomain
    company_type: CompanyType
    work_format: WorkFormat
    experience_years_required: int = Field(ge=0, le=60)
    english_level_required: EnglishLevel
    salary_min: int = Field(ge=0, le=SALARY_LIMIT, description="Lower bound of the fork, USD")
    salary_max: int = Field(ge=0, le=SALARY_LIMIT, description="Upper bound of the fork, USD")

    @model_validator(mode="after")
    def _check_salary_range(self) -> Self:
        if self.salary_min > self.salary_max:
            raise ValueError("salary_min must not exceed salary_max")
        return self


class VacancyUpdate(PatchModel):
    non_nullable_fields: ClassVar[frozenset[str]] = frozenset(
        {
            "title",
            "description",
            "domain",
            "company_type",
            "work_format",
            "experience_years_required",
            "english_level_required",
            "salary_min",
            "salary_max",
        }
    )

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=20_000)
    domain: TechDomain | None = None
    company_type: CompanyType | None = None
    work_format: WorkFormat | None = None
    experience_years_required: int | None = Field(default=None, ge=0, le=60)
    english_level_required: EnglishLevel | None = None
    salary_min: int | None = Field(default=None, ge=0, le=SALARY_LIMIT)
    salary_max: int | None = Field(default=None, ge=0, le=SALARY_LIMIT)


class VacancyRead(ORMModel):
    id: int
    recruiter_id: int
    company_name: str
    title: str
    description: str
    domain: TechDomain
    company_type: CompanyType
    work_format: WorkFormat
    experience_years_required: int
    english_level_required: EnglishLevel
    salary_min: int
    salary_max: int
    status: VacancyStatus
    created_at: datetime
    updated_at: datetime


class VacancyWithStats(VacancyRead):
    applications_count: int


class VacancyQuery(PageParams):
    domain: TechDomain | None = None
    company_type: CompanyType | None = None
    work_format: WorkFormat | None = None
    english_level: EnglishLevel | None = Field(
        default=None,
        description="Your English level: vacancies requiring this level or lower are returned",
    )
    experience_years: int | None = Field(
        default=None,
        ge=0,
        description="Your experience: vacancies requiring this many years or fewer are returned",
    )
    salary_from: int | None = Field(
        default=None, ge=0, description="Vacancies whose upper salary bound is at least this value"
    )
    salary_to: int | None = Field(
        default=None, ge=0, description="Vacancies whose lower salary bound is at most this value"
    )
    sort_by: Literal["created_at", "salary_max"] = "created_at"
    order: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def _check_salary_range(self) -> Self:
        if (
            self.salary_from is not None
            and self.salary_to is not None
            and self.salary_from > self.salary_to
        ):
            raise ValueError("salary_from must not exceed salary_to")
        return self

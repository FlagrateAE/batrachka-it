from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.applications.models import Application
from app.common.enums import ApplicationStatus, EnglishLevel, TechDomain, VacancyStatus
from app.common.schemas import ORMModel, PageParams

CONTACT_REVEALING_STATUSES = frozenset({ApplicationStatus.ACCEPTED, ApplicationStatus.HIRED})


class ApplicationCreate(BaseModel):
    cover_letter: str | None = Field(default=None, max_length=5_000)


class ApplicationStatusUpdate(BaseModel):
    status: Literal["ACCEPTED", "REJECTED", "HIRED"]


class ApplicationQuery(PageParams):
    status: ApplicationStatus | None = None


class ApplicationRead(ORMModel):
    id: int
    vacancy_id: int
    candidate_id: int
    cover_letter: str | None
    status: ApplicationStatus
    created_at: datetime
    updated_at: datetime


class CandidateCard(BaseModel):
    user_id: int
    full_name: str
    bio: str | None
    avatar_url: str | None
    age: int | None
    domain: TechDomain
    experience_years: int
    english_level: EnglishLevel
    expected_salary: int
    resume_text: str | None
    contact_info: str | None = Field(
        description="Revealed only when the application is ACCEPTED or HIRED"
    )


class RecruiterCard(BaseModel):
    user_id: int
    full_name: str
    company_name: str
    contact_info: str | None = Field(
        description="Revealed only when the application is ACCEPTED or HIRED"
    )


class VacancySummary(ORMModel):
    id: int
    title: str
    company_name: str
    status: VacancyStatus


class ApplicationForRecruiter(ApplicationRead):
    candidate: CandidateCard


class ApplicationForCandidate(ApplicationRead):
    vacancy: VacancySummary
    recruiter: RecruiterCard


def contacts_revealed(status: ApplicationStatus) -> bool:
    return status in CONTACT_REVEALING_STATUSES


def to_recruiter_view(application: Application) -> ApplicationForRecruiter:
    candidate = application.candidate
    user = candidate.user
    return ApplicationForRecruiter(
        **ApplicationRead.model_validate(application).model_dump(),
        candidate=CandidateCard(
            user_id=user.user_id,
            full_name=user.full_name,
            bio=user.bio,
            avatar_url=user.avatar_url,
            age=candidate.age,
            domain=candidate.domain,
            experience_years=candidate.experience_years,
            english_level=candidate.english_level,
            expected_salary=candidate.expected_salary,
            resume_text=candidate.resume_text,
            contact_info=user.contact_info if contacts_revealed(application.status) else None,
        ),
    )


def to_candidate_view(application: Application) -> ApplicationForCandidate:
    vacancy = application.vacancy
    recruiter = vacancy.recruiter
    return ApplicationForCandidate(
        **ApplicationRead.model_validate(application).model_dump(),
        vacancy=VacancySummary.model_validate(vacancy),
        recruiter=RecruiterCard(
            user_id=recruiter.user.user_id,
            full_name=recruiter.user.full_name,
            company_name=recruiter.company_name,
            contact_info=(
                recruiter.user.contact_info if contacts_revealed(application.status) else None
            ),
        ),
    )

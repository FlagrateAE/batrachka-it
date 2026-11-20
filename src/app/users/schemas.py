from datetime import datetime
from typing import ClassVar

from pydantic import AnyHttpUrl, EmailStr, Field

from app.common.enums import EnglishLevel, TechDomain, UserRole
from app.common.schemas import ORMModel, PatchModel


class CandidateProfileRead(ORMModel):
    age: int | None
    domain: TechDomain
    experience_years: int
    english_level: EnglishLevel
    expected_salary: int
    resume_text: str | None


class RecruiterProfileRead(ORMModel):
    company_name: str


class UserRead(ORMModel):
    user_id: int
    email: EmailStr
    role: UserRole
    full_name: str
    bio: str | None
    avatar_url: str | None
    contact_info: str
    created_at: datetime
    updated_at: datetime
    candidate: CandidateProfileRead | None
    recruiter: RecruiterProfileRead | None


class CandidateProfileUpdate(PatchModel):
    non_nullable_fields: ClassVar[frozenset[str]] = frozenset(
        {"domain", "experience_years", "english_level", "expected_salary"}
    )

    age: int | None = Field(default=None, ge=14, le=100)
    domain: TechDomain | None = None
    experience_years: int | None = Field(default=None, ge=0, le=60)
    english_level: EnglishLevel | None = None
    expected_salary: int | None = Field(default=None, ge=0, le=1_000_000)
    resume_text: str | None = Field(default=None, max_length=20_000)


class RecruiterProfileUpdate(PatchModel):
    non_nullable_fields: ClassVar[frozenset[str]] = frozenset({"company_name"})

    company_name: str | None = Field(default=None, min_length=2, max_length=150)


class UserUpdate(PatchModel):
    non_nullable_fields: ClassVar[frozenset[str]] = frozenset(
        {"full_name", "contact_info", "candidate", "recruiter"}
    )

    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    bio: str | None = Field(default=None, max_length=5_000)
    avatar_url: AnyHttpUrl | None = None
    contact_info: str | None = Field(default=None, min_length=3, max_length=255)
    candidate: CandidateProfileUpdate | None = None
    recruiter: RecruiterProfileUpdate | None = None

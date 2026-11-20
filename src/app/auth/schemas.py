from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.common.enums import EnglishLevel, TechDomain
from app.core.security import TokenPair


class _RegisterBase(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)
    contact_info: str = Field(min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return value.lower()


class CandidateRegister(_RegisterBase):
    role: Literal["CANDIDATE"]
    domain: TechDomain
    experience_years: int = Field(ge=0, le=60)
    english_level: EnglishLevel
    expected_salary: int = Field(ge=0, le=1_000_000)
    age: int | None = Field(default=None, ge=14, le=100)
    resume_text: str | None = Field(default=None, max_length=20_000)


class RecruiterRegister(_RegisterBase):
    role: Literal["RECRUITER"]
    company_name: str = Field(min_length=2, max_length=150)


RegisterRequest = Annotated[CandidateRegister | RecruiterRegister, Field(discriminator="role")]


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int

    @classmethod
    def from_pair(cls, pair: TokenPair) -> "TokenResponse":
        return cls(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            expires_in=pair.expires_in,
        )

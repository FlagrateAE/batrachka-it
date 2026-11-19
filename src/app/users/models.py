from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.db import (
    Base,
    TimestampMixin,
    english_level_type,
    tech_domain_type,
    user_role_type,
)
from app.common.enums import EnglishLevel, TechDomain, UserRole


class User(TimestampMixin, Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(user_role_type)
    full_name: Mapped[str] = mapped_column(String(150))
    bio: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(String(2048))
    contact_info: Mapped[str] = mapped_column(String(255))

    candidate: Mapped[Candidate | None] = relationship(
        back_populates="user", lazy="raise", passive_deletes=True
    )
    recruiter: Mapped[Recruiter | None] = relationship(
        back_populates="user", lazy="raise", passive_deletes=True
    )


class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = (
        CheckConstraint("experience_years >= 0", name="experience_years_non_negative"),
        CheckConstraint("expected_salary >= 0", name="expected_salary_non_negative"),
        CheckConstraint("age BETWEEN 14 AND 100", name="age_range"),
    )

    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    age: Mapped[int | None]
    domain: Mapped[TechDomain] = mapped_column(tech_domain_type)
    experience_years: Mapped[int]
    english_level: Mapped[EnglishLevel] = mapped_column(english_level_type)
    expected_salary: Mapped[int]
    resume_text: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="candidate", lazy="raise")


class Recruiter(Base):
    __tablename__ = "recruiters"

    recruiter_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    company_name: Mapped[str] = mapped_column(String(150))

    user: Mapped[User] = relationship(back_populates="recruiter", lazy="raise")

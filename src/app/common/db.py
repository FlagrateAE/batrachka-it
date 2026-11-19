from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.common.enums import (
    ApplicationStatus,
    CompanyType,
    EnglishLevel,
    TechDomain,
    UserRole,
    VacancyStatus,
    WorkFormat,
)

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=utcnow
    )


# Bound to metadata so that a type shared by several tables is created and dropped once.
user_role_type = Enum(UserRole, name="user_role", metadata=Base.metadata)
tech_domain_type = Enum(TechDomain, name="tech_domain", metadata=Base.metadata)
company_type_type = Enum(CompanyType, name="company_type", metadata=Base.metadata)
work_format_type = Enum(WorkFormat, name="work_format", metadata=Base.metadata)
english_level_type = Enum(EnglishLevel, name="english_level", metadata=Base.metadata)
vacancy_status_type = Enum(VacancyStatus, name="vacancy_status", metadata=Base.metadata)
application_status_type = Enum(ApplicationStatus, name="application_status", metadata=Base.metadata)

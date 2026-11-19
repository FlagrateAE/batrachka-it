from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.db import Base, TimestampMixin, application_status_type
from app.common.enums import ApplicationStatus

if TYPE_CHECKING:
    from app.users.models import Candidate
    from app.vacancies.models import Vacancy


class Application(TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("vacancy_id", "candidate_id"),
        Index("ix_applications_vacancy_id_status", "vacancy_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"))
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.candidate_id", ondelete="CASCADE"), index=True
    )
    cover_letter: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ApplicationStatus] = mapped_column(
        application_status_type,
        default=ApplicationStatus.PENDING,
        server_default=ApplicationStatus.PENDING.value,
    )

    vacancy: Mapped[Vacancy] = relationship(lazy="raise")
    candidate: Mapped[Candidate] = relationship(lazy="raise")

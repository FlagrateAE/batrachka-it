from typing import Protocol

from sqlalchemy import ColumnElement, exists, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.interfaces import LoaderOption

from app.applications.models import Application
from app.common.enums import ApplicationStatus
from app.common.schemas import PageParams
from app.core.exceptions import ConflictError
from app.users.models import Candidate, Recruiter
from app.vacancies.models import Vacancy

ACTIVE_STATUSES = (ApplicationStatus.PENDING, ApplicationStatus.ACCEPTED)


class ApplicationRepository(Protocol):
    async def add(self, application: Application) -> None: ...

    async def exists(self, vacancy_id: int, candidate_id: int) -> bool: ...

    async def get_by_id(
        self, application_id: int, *, for_update: bool = False
    ) -> Application | None: ...

    async def get_detailed(self, application_id: int) -> Application | None: ...

    async def list_by_vacancy(
        self, vacancy_id: int, status: ApplicationStatus | None, page: PageParams
    ) -> tuple[list[Application], int]: ...

    async def list_by_candidate(
        self, candidate_id: int, status: ApplicationStatus | None, page: PageParams
    ) -> tuple[list[Application], int]: ...

    async def reject_active(
        self, vacancy_id: int, *, exclude_application_id: int | None = None
    ) -> int: ...


class SqlAlchemyApplicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, application: Application) -> None:
        try:
            async with self._session.begin_nested():
                self._session.add(application)
        except IntegrityError as exc:
            raise ConflictError("You have already applied to this vacancy") from exc

    async def exists(self, vacancy_id: int, candidate_id: int) -> bool:
        stmt = select(
            exists().where(
                Application.vacancy_id == vacancy_id, Application.candidate_id == candidate_id
            )
        )
        return bool(await self._session.scalar(stmt))

    async def get_by_id(
        self, application_id: int, *, for_update: bool = False
    ) -> Application | None:
        stmt = select(Application).where(Application.id == application_id)
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        return await self._session.scalar(stmt)

    async def get_detailed(self, application_id: int) -> Application | None:
        stmt = (
            select(Application)
            .options(*self._detailed_options())
            .where(Application.id == application_id)
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(stmt)

    async def list_by_vacancy(
        self, vacancy_id: int, status: ApplicationStatus | None, page: PageParams
    ) -> tuple[list[Application], int]:
        return await self._list([Application.vacancy_id == vacancy_id], status, page)

    async def list_by_candidate(
        self, candidate_id: int, status: ApplicationStatus | None, page: PageParams
    ) -> tuple[list[Application], int]:
        return await self._list([Application.candidate_id == candidate_id], status, page)

    async def reject_active(
        self, vacancy_id: int, *, exclude_application_id: int | None = None
    ) -> int:
        stmt = (
            update(Application)
            .where(Application.vacancy_id == vacancy_id, Application.status.in_(ACTIVE_STATUSES))
            .values(status=ApplicationStatus.REJECTED)
            .execution_options(synchronize_session=False)
        )
        if exclude_application_id is not None:
            stmt = stmt.where(Application.id != exclude_application_id)
        result = await self._session.execute(stmt)
        return result.rowcount

    async def _list(
        self,
        conditions: list[ColumnElement[bool]],
        status: ApplicationStatus | None,
        page: PageParams,
    ) -> tuple[list[Application], int]:
        if status is not None:
            conditions = [*conditions, Application.status == status]
        total = await self._session.scalar(
            select(func.count()).select_from(Application).where(*conditions)
        )
        stmt = (
            select(Application)
            .options(*self._detailed_options())
            .where(*conditions)
            .order_by(Application.created_at.desc(), Application.id.desc())
            .limit(page.limit)
            .offset(page.offset)
        )
        items = list((await self._session.scalars(stmt)).all())
        return items, total or 0

    @staticmethod
    def _detailed_options() -> tuple[LoaderOption, ...]:
        return (
            joinedload(Application.candidate, innerjoin=True).joinedload(
                Candidate.user, innerjoin=True
            ),
            joinedload(Application.vacancy, innerjoin=True)
            .joinedload(Vacancy.recruiter, innerjoin=True)
            .joinedload(Recruiter.user, innerjoin=True),
        )

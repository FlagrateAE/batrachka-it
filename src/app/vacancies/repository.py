from typing import Protocol

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.applications.models import Application
from app.common.enums import VacancyStatus
from app.common.schemas import PageParams
from app.vacancies.models import Vacancy
from app.vacancies.schemas import VacancyQuery


class VacancyRepository(Protocol):
    async def add(self, vacancy: Vacancy) -> None: ...

    async def get_by_id(self, vacancy_id: int) -> Vacancy | None: ...

    async def get_locked(self, vacancy_id: int, *, exclusive: bool) -> Vacancy | None: ...

    async def search(self, query: VacancyQuery) -> tuple[list[Vacancy], int]: ...

    async def list_by_recruiter(
        self, recruiter_id: int, page: PageParams
    ) -> tuple[list[tuple[Vacancy, int]], int]: ...

    async def delete(self, vacancy: Vacancy) -> None: ...


class SqlAlchemyVacancyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, vacancy: Vacancy) -> None:
        self._session.add(vacancy)
        await self._session.flush()

    async def get_by_id(self, vacancy_id: int) -> Vacancy | None:
        stmt = (
            select(Vacancy)
            .options(joinedload(Vacancy.recruiter, innerjoin=True))
            .where(Vacancy.id == vacancy_id)
        )
        return await self._session.scalar(stmt)

    async def get_locked(self, vacancy_id: int, *, exclusive: bool) -> Vacancy | None:
        stmt = (
            select(Vacancy)
            .options(joinedload(Vacancy.recruiter, innerjoin=True))
            .where(Vacancy.id == vacancy_id)
            .with_for_update(read=not exclusive, of=Vacancy)
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(stmt)

    async def search(self, query: VacancyQuery) -> tuple[list[Vacancy], int]:
        conditions = self._build_conditions(query)
        sort_column = Vacancy.salary_max if query.sort_by == "salary_max" else Vacancy.created_at
        ordering = (
            (sort_column.desc(), Vacancy.id.desc())
            if query.order == "desc"
            else (sort_column.asc(), Vacancy.id.asc())
        )
        # The window count returns the page and the total in one round trip to the database.
        stmt = (
            select(Vacancy, func.count().over())
            .options(joinedload(Vacancy.recruiter, innerjoin=True))
            .where(*conditions)
            .order_by(*ordering)
            .limit(query.limit)
            .offset(query.offset)
        )
        rows = (await self._session.execute(stmt)).tuples().all()
        if rows:
            return [vacancy for vacancy, _ in rows], rows[0][1]
        if query.offset == 0:
            return [], 0
        total = await self._session.scalar(
            select(func.count()).select_from(Vacancy).where(*conditions)
        )
        return [], total or 0

    async def list_by_recruiter(
        self, recruiter_id: int, page: PageParams
    ) -> tuple[list[tuple[Vacancy, int]], int]:
        applications_count = (
            select(func.count(Application.id))
            .where(Application.vacancy_id == Vacancy.id)
            .correlate(Vacancy)
            .scalar_subquery()
        )
        stmt = (
            select(Vacancy, applications_count)
            .options(joinedload(Vacancy.recruiter, innerjoin=True))
            .where(Vacancy.recruiter_id == recruiter_id)
            .order_by(Vacancy.created_at.desc(), Vacancy.id.desc())
            .limit(page.limit)
            .offset(page.offset)
        )
        rows = (await self._session.execute(stmt)).tuples().all()
        total = await self._session.scalar(
            select(func.count()).select_from(Vacancy).where(Vacancy.recruiter_id == recruiter_id)
        )
        return [(vacancy, count) for vacancy, count in rows], total or 0

    async def delete(self, vacancy: Vacancy) -> None:
        await self._session.delete(vacancy)
        await self._session.flush()

    @staticmethod
    def _build_conditions(query: VacancyQuery) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = [Vacancy.status == VacancyStatus.OPEN]
        if query.domain is not None:
            conditions.append(Vacancy.domain == query.domain)
        if query.company_type is not None:
            conditions.append(Vacancy.company_type == query.company_type)
        if query.work_format is not None:
            conditions.append(Vacancy.work_format == query.work_format)
        if query.english_level is not None:
            # PostgreSQL compares ENUM values by declaration order, NO_ENGLISH < ... < PROFICIENT.
            conditions.append(Vacancy.english_level_required <= query.english_level)
        if query.experience_years is not None:
            conditions.append(Vacancy.experience_years_required <= query.experience_years)
        if query.salary_from is not None:
            conditions.append(Vacancy.salary_max >= query.salary_from)
        if query.salary_to is not None:
            conditions.append(Vacancy.salary_min <= query.salary_to)
        return conditions

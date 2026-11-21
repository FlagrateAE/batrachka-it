from typing import Protocol

from app.common.enums import VacancyStatus
from app.common.schemas import PageParams
from app.core.database import UnitOfWork
from app.core.exceptions import (
    ConflictError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
)
from app.users.models import User
from app.vacancies.models import Vacancy
from app.vacancies.repository import VacancyRepository
from app.vacancies.schemas import VacancyCreate, VacancyQuery, VacancyUpdate


class ActiveApplicationsRejecter(Protocol):
    async def reject_active(
        self, vacancy_id: int, *, exclude_application_id: int | None = None
    ) -> int: ...


class VacancyService:
    def __init__(
        self,
        vacancies: VacancyRepository,
        applications: ActiveApplicationsRejecter,
        uow: UnitOfWork,
    ) -> None:
        self._vacancies = vacancies
        self._applications = applications
        self._uow = uow

    async def create(self, recruiter: User, data: VacancyCreate) -> Vacancy:
        if recruiter.recruiter is None:
            raise PermissionDeniedError("Only recruiters can publish vacancies")
        vacancy = Vacancy(
            **data.model_dump(), recruiter_id=recruiter.user_id, status=VacancyStatus.OPEN
        )
        vacancy.recruiter = recruiter.recruiter
        await self._vacancies.add(vacancy)
        await self._uow.commit()
        return vacancy

    async def get(self, vacancy_id: int) -> Vacancy:
        vacancy = await self._vacancies.get_by_id(vacancy_id)
        if vacancy is None:
            raise NotFoundError("Vacancy not found")
        return vacancy

    async def search(self, query: VacancyQuery) -> tuple[list[Vacancy], int]:
        return await self._vacancies.search(query)

    async def list_own(
        self, recruiter: User, page: PageParams
    ) -> tuple[list[tuple[Vacancy, int]], int]:
        return await self._vacancies.list_by_recruiter(recruiter.user_id, page)

    async def update(self, recruiter: User, vacancy_id: int, data: VacancyUpdate) -> Vacancy:
        vacancy = await self.get_locked(vacancy_id, exclusive=True)
        self.ensure_owner(vacancy, recruiter)
        self.ensure_open(vacancy)

        changes = data.model_dump(exclude_unset=True)
        salary_min = changes.get("salary_min", vacancy.salary_min)
        salary_max = changes.get("salary_max", vacancy.salary_max)
        if salary_min > salary_max:
            raise InvalidInputError("salary_min must not exceed salary_max")

        for field, value in changes.items():
            setattr(vacancy, field, value)
        await self._uow.commit()
        return vacancy

    async def close(self, recruiter: User, vacancy_id: int) -> Vacancy:
        vacancy = await self.get_locked(vacancy_id, exclusive=True)
        self.ensure_owner(vacancy, recruiter)
        self.ensure_open(vacancy)
        vacancy.status = VacancyStatus.CLOSED
        await self._applications.reject_active(vacancy.id)
        await self._uow.commit()
        return vacancy

    async def delete(self, recruiter: User, vacancy_id: int) -> None:
        vacancy = await self.get_locked(vacancy_id, exclusive=True)
        self.ensure_owner(vacancy, recruiter)
        await self._vacancies.delete(vacancy)
        await self._uow.commit()

    async def get_locked(self, vacancy_id: int, *, exclusive: bool) -> Vacancy:
        vacancy = await self._vacancies.get_locked(vacancy_id, exclusive=exclusive)
        if vacancy is None:
            raise NotFoundError("Vacancy not found")
        return vacancy

    @staticmethod
    def close_after_hire(vacancy: Vacancy) -> None:
        vacancy.status = VacancyStatus.CLOSED

    @staticmethod
    def ensure_open(vacancy: Vacancy) -> None:
        if vacancy.status is not VacancyStatus.OPEN:
            raise ConflictError("Vacancy is closed")

    @staticmethod
    def ensure_owner(vacancy: Vacancy, recruiter: User) -> None:
        if vacancy.recruiter_id != recruiter.user_id:
            raise PermissionDeniedError("Only the author of the vacancy can do this")

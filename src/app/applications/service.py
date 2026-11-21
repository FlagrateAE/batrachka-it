from app.applications.models import Application
from app.applications.repository import ApplicationRepository
from app.applications.schemas import ApplicationCreate
from app.common.enums import ApplicationStatus
from app.common.schemas import PageParams
from app.core.database import UnitOfWork
from app.core.exceptions import ConflictError, NotFoundError
from app.users.models import User
from app.vacancies.service import VacancyService

ALLOWED_TRANSITIONS: dict[ApplicationStatus, frozenset[ApplicationStatus]] = {
    ApplicationStatus.PENDING: frozenset(
        {ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED, ApplicationStatus.HIRED}
    ),
    ApplicationStatus.ACCEPTED: frozenset({ApplicationStatus.REJECTED, ApplicationStatus.HIRED}),
}


class ApplicationService:
    def __init__(
        self,
        applications: ApplicationRepository,
        vacancies: VacancyService,
        uow: UnitOfWork,
    ) -> None:
        self._applications = applications
        self._vacancies = vacancies
        self._uow = uow

    async def apply(self, candidate: User, vacancy_id: int, data: ApplicationCreate) -> Application:
        # A shared lock conflicts with the exclusive lock taken on hiring, so nobody can apply
        # to a vacancy while it is being closed.
        vacancy = await self._vacancies.get_locked(vacancy_id, exclusive=False)
        self._vacancies.ensure_open(vacancy)
        if await self._applications.exists(vacancy.id, candidate.user_id):
            raise ConflictError("You have already applied to this vacancy")

        application = Application(
            vacancy_id=vacancy.id,
            candidate_id=candidate.user_id,
            cover_letter=data.cover_letter,
            status=ApplicationStatus.PENDING,
        )
        await self._applications.add(application)
        await self._uow.commit()
        return application

    async def list_for_vacancy(
        self,
        recruiter: User,
        vacancy_id: int,
        status: ApplicationStatus | None,
        page: PageParams,
    ) -> tuple[list[Application], int]:
        vacancy = await self._vacancies.get(vacancy_id)
        self._vacancies.ensure_owner(vacancy, recruiter)
        return await self._applications.list_by_vacancy(vacancy_id, status, page)

    async def list_for_candidate(
        self, candidate: User, status: ApplicationStatus | None, page: PageParams
    ) -> tuple[list[Application], int]:
        return await self._applications.list_by_candidate(candidate.user_id, status, page)

    async def get_for_participant(self, user: User, application_id: int) -> Application:
        application = await self._applications.get_detailed(application_id)
        if application is None or user.user_id not in (
            application.candidate_id,
            application.vacancy.recruiter_id,
        ):
            raise NotFoundError("Application not found")
        return application

    async def change_status(
        self, recruiter: User, application_id: int, new_status: ApplicationStatus
    ) -> Application:
        application = await self._applications.get_by_id(application_id)
        if application is None:
            raise NotFoundError("Application not found")

        # Every status change locks the vacancy row first, so concurrent changes of one vacancy
        # run one after another and two candidates can never be hired for it (NFR-3.1).
        vacancy = await self._vacancies.get_locked(application.vacancy_id, exclusive=True)
        if vacancy.recruiter_id != recruiter.user_id:
            raise NotFoundError("Application not found")
        self._vacancies.ensure_open(vacancy)

        application = await self._applications.get_by_id(application_id, for_update=True)
        if application is None:
            raise NotFoundError("Application not found")
        if new_status not in ALLOWED_TRANSITIONS.get(application.status, frozenset()):
            raise ConflictError(
                f"Cannot change application status from {application.status} to {new_status}"
            )

        application.status = new_status
        if new_status is ApplicationStatus.HIRED:
            self._vacancies.close_after_hire(vacancy)
            await self._applications.reject_active(
                vacancy.id, exclude_application_id=application.id
            )
        await self._uow.commit()

        detailed = await self._applications.get_detailed(application.id)
        if detailed is None:
            raise NotFoundError("Application not found")
        return detailed

from typing import Annotated

from fastapi import Depends

from app.applications.repository import SqlAlchemyApplicationRepository
from app.applications.service import ApplicationService
from app.core.dependencies import SessionDep
from app.vacancies.dependencies import VacancyServiceDep


def get_application_service(
    session: SessionDep, vacancies: VacancyServiceDep
) -> ApplicationService:
    return ApplicationService(
        applications=SqlAlchemyApplicationRepository(session),
        vacancies=vacancies,
        uow=session,
    )


ApplicationServiceDep = Annotated[ApplicationService, Depends(get_application_service)]

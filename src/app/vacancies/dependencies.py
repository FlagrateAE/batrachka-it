from typing import Annotated

from fastapi import Depends

from app.applications.repository import SqlAlchemyApplicationRepository
from app.core.dependencies import SessionDep
from app.vacancies.repository import SqlAlchemyVacancyRepository
from app.vacancies.service import VacancyService


def get_vacancy_service(session: SessionDep) -> VacancyService:
    return VacancyService(
        vacancies=SqlAlchemyVacancyRepository(session),
        applications=SqlAlchemyApplicationRepository(session),
        uow=session,
    )


VacancyServiceDep = Annotated[VacancyService, Depends(get_vacancy_service)]

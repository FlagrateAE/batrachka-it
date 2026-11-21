from typing import Annotated

from fastapi import APIRouter, Query, status

from app.auth.dependencies import CurrentRecruiter
from app.common.schemas import Page, PageParams
from app.vacancies.dependencies import VacancyServiceDep
from app.vacancies.schemas import (
    VacancyCreate,
    VacancyQuery,
    VacancyRead,
    VacancyUpdate,
    VacancyWithStats,
)

router = APIRouter(prefix="/vacancies", tags=["vacancies"])


@router.get("", summary="Search open vacancies by exact filters")
async def search_vacancies(
    query: Annotated[VacancyQuery, Query()], service: VacancyServiceDep
) -> Page[VacancyRead]:
    items, total = await service.search(query)
    return Page(
        items=[VacancyRead.model_validate(vacancy) for vacancy in items],
        total=total,
        limit=query.limit,
        offset=query.offset,
    )


@router.get("/my", summary="List own vacancies with the number of applications")
async def list_own_vacancies(
    page: Annotated[PageParams, Query()],
    recruiter: CurrentRecruiter,
    service: VacancyServiceDep,
) -> Page[VacancyWithStats]:
    rows, total = await service.list_own(recruiter, page)
    items = [
        VacancyWithStats.model_validate(
            {**VacancyRead.model_validate(vacancy).model_dump(), "applications_count": count}
        )
        for vacancy, count in rows
    ]
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get("/{vacancy_id}", summary="Get vacancy details")
async def get_vacancy(vacancy_id: int, service: VacancyServiceDep) -> VacancyRead:
    return VacancyRead.model_validate(await service.get(vacancy_id))


@router.post("", status_code=status.HTTP_201_CREATED, summary="Publish a vacancy")
async def create_vacancy(
    payload: VacancyCreate, recruiter: CurrentRecruiter, service: VacancyServiceDep
) -> VacancyRead:
    return VacancyRead.model_validate(await service.create(recruiter, payload))


@router.patch("/{vacancy_id}", summary="Edit an open vacancy")
async def update_vacancy(
    vacancy_id: int,
    payload: VacancyUpdate,
    recruiter: CurrentRecruiter,
    service: VacancyServiceDep,
) -> VacancyRead:
    return VacancyRead.model_validate(await service.update(recruiter, vacancy_id, payload))


@router.post(
    "/{vacancy_id}/close",
    summary="Close a vacancy manually; active applications become REJECTED",
)
async def close_vacancy(
    vacancy_id: int, recruiter: CurrentRecruiter, service: VacancyServiceDep
) -> VacancyRead:
    return VacancyRead.model_validate(await service.close(recruiter, vacancy_id))


@router.delete(
    "/{vacancy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a vacancy together with its applications",
)
async def delete_vacancy(
    vacancy_id: int, recruiter: CurrentRecruiter, service: VacancyServiceDep
) -> None:
    await service.delete(recruiter, vacancy_id)

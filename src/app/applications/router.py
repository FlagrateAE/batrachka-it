from typing import Annotated

from fastapi import APIRouter, Query, status

from app.applications.dependencies import ApplicationServiceDep
from app.applications.schemas import (
    ApplicationCreate,
    ApplicationForCandidate,
    ApplicationForRecruiter,
    ApplicationQuery,
    ApplicationRead,
    ApplicationStatusUpdate,
    to_candidate_view,
    to_recruiter_view,
)
from app.auth.dependencies import CurrentCandidate, CurrentRecruiter, CurrentUser
from app.common.enums import ApplicationStatus, UserRole
from app.common.schemas import Page

router = APIRouter(tags=["applications"])


@router.post(
    "/vacancies/{vacancy_id}/apply",
    status_code=status.HTTP_201_CREATED,
    summary="Apply to an open vacancy",
)
async def apply_to_vacancy(
    vacancy_id: int,
    payload: ApplicationCreate,
    candidate: CurrentCandidate,
    service: ApplicationServiceDep,
) -> ApplicationRead:
    application = await service.apply(candidate, vacancy_id, payload)
    return ApplicationRead.model_validate(application)


@router.get(
    "/vacancies/{vacancy_id}/applications",
    summary="List applications to own vacancy",
)
async def list_vacancy_applications(
    vacancy_id: int,
    query: Annotated[ApplicationQuery, Query()],
    recruiter: CurrentRecruiter,
    service: ApplicationServiceDep,
) -> Page[ApplicationForRecruiter]:
    items, total = await service.list_for_vacancy(recruiter, vacancy_id, query.status, query)
    return Page(
        items=[to_recruiter_view(item) for item in items],
        total=total,
        limit=query.limit,
        offset=query.offset,
    )


@router.get("/applications/my", summary="List own applications")
async def list_own_applications(
    query: Annotated[ApplicationQuery, Query()],
    candidate: CurrentCandidate,
    service: ApplicationServiceDep,
) -> Page[ApplicationForCandidate]:
    items, total = await service.list_for_candidate(candidate, query.status, query)
    return Page(
        items=[to_candidate_view(item) for item in items],
        total=total,
        limit=query.limit,
        offset=query.offset,
    )


@router.get(
    "/applications/{application_id}",
    summary="Get an application; visible only to its candidate and the vacancy author",
)
async def get_application(
    application_id: int, user: CurrentUser, service: ApplicationServiceDep
) -> ApplicationForRecruiter | ApplicationForCandidate:
    application = await service.get_for_participant(user, application_id)
    if user.role is UserRole.RECRUITER:
        return to_recruiter_view(application)
    return to_candidate_view(application)


@router.patch(
    "/applications/{application_id}/status",
    summary="Accept, reject or hire; hiring closes the vacancy and rejects the rest",
)
async def change_application_status(
    application_id: int,
    payload: ApplicationStatusUpdate,
    recruiter: CurrentRecruiter,
    service: ApplicationServiceDep,
) -> ApplicationForRecruiter:
    application = await service.change_status(
        recruiter, application_id, ApplicationStatus(payload.status)
    )
    return to_recruiter_view(application)

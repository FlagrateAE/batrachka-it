from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.dependencies import SessionDep

router = APIRouter(tags=["system"])


class HealthRead(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]


@router.get(
    "/health",
    summary="Liveness and database connectivity check",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthRead}},
)
async def health(session: SessionDep, response: Response) -> HealthRead:
    try:
        await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthRead(status="degraded", database="unavailable")
    return HealthRead(status="ok", database="ok")

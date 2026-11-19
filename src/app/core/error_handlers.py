from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    DomainError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
)

_STATUS_CODES: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    InvalidInputError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


async def handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, DomainError):
        raise exc
    status_code = next(
        (code for error_type, code in _STATUS_CODES.items() if isinstance(exc, error_type)),
        status.HTTP_400_BAD_REQUEST,
    )
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, AuthenticationError) else None
    return JSONResponse(status_code=status_code, content={"detail": exc.detail}, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_domain_error)

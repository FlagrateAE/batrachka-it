from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

import app.models  # noqa: F401  # registers every ORM model before mappers are configured
from app.api import api_router
from app.core.config import Settings, get_settings
from app.core.database import build_engine, build_session_factory
from app.core.error_handlers import register_exception_handlers
from app.core.security import PasswordHasher, TokenService
from app.health import router as health_router

DESCRIPTION = """
REST API for searching IT vacancies by exact relational filters
(domain, salary fork, experience, work format, company type, English level)
and for managing the hiring flow: PENDING -> ACCEPTED / REJECTED / HIRED.

Use **Authorize** with your email as the username to call protected endpoints.
"""

OPENAPI_TAGS = [
    {"name": "auth", "description": "Registration, login and token refresh (OAuth2 + JWT)."},
    {"name": "users", "description": "Own profile of the authenticated user."},
    {"name": "vacancies", "description": "Publishing, editing and searching vacancies."},
    {"name": "applications", "description": "Applying, reviewing and hiring."},
    {"name": "system", "description": "Service health."},
]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = build_engine(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await engine.dispose()

    application = FastAPI(
        title=settings.app_name,
        version="0.5.0",
        description=DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.engine = engine
    application.state.session_factory = build_session_factory(engine)
    application.state.password_hasher = PasswordHasher()
    application.state.token_service = TokenService.from_settings(settings)

    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(api_router)

    @application.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    return application

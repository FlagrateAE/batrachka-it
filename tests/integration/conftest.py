from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import text

from app.core.config import Settings
from app.main import create_app
from app.models import Base
from tests.helpers import auth_headers, candidate_payload, create_vacancy, recruiter_payload


class TestDatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    test_database_url: str = (
        "postgresql+asyncpg://batrachka:batrachka@localhost:5432/batrachkait_test"
    )


@pytest.fixture(scope="session")
async def app() -> AsyncIterator[FastAPI]:
    settings = Settings(
        database_url=TestDatabaseSettings().test_database_url,
        environment="test",
        jwt_secret_key="test-secret-key-that-is-long-enough-for-hs256",  # type: ignore[arg-type]
    )
    application = create_app(settings)
    engine = application.state.engine
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield application
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_database(app: FastAPI) -> AsyncIterator[None]:
    yield
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    async with app.state.engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.fixture
async def recruiter_headers(client: AsyncClient) -> dict[str, str]:
    return await auth_headers(client, recruiter_payload())


@pytest.fixture
async def other_recruiter_headers(client: AsyncClient) -> dict[str, str]:
    return await auth_headers(client, recruiter_payload(company_name="Another Corp"))


@pytest.fixture
async def candidate_headers(client: AsyncClient) -> dict[str, str]:
    return await auth_headers(client, candidate_payload())


@pytest.fixture
async def vacancy(client: AsyncClient, recruiter_headers: dict[str, str]) -> dict:
    return await create_vacancy(client, recruiter_headers)

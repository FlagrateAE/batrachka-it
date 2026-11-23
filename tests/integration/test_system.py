from httpx import AsyncClient


async def test_health_reports_database_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_openapi_documents_every_endpoint(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    paths = response.json()["paths"]
    assert response.status_code == 200
    assert {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/users/me",
        "/api/v1/vacancies",
        "/api/v1/vacancies/my",
        "/api/v1/vacancies/{vacancy_id}",
        "/api/v1/vacancies/{vacancy_id}/close",
        "/api/v1/vacancies/{vacancy_id}/apply",
        "/api/v1/vacancies/{vacancy_id}/applications",
        "/api/v1/applications/my",
        "/api/v1/applications/{application_id}",
        "/api/v1/applications/{application_id}/status",
    } <= paths.keys()


async def test_swagger_ui_is_served(client: AsyncClient) -> None:
    response = await client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


async def test_root_redirects_to_docs(client: AsyncClient) -> None:
    response = await client.get("/")

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"

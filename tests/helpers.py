from typing import Any
from uuid import uuid4

from httpx import AsyncClient

PASSWORD = "Str0ngPassw0rd!"


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}@example.com"


def candidate_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "role": "CANDIDATE",
        "email": unique_email("candidate"),
        "password": PASSWORD,
        "full_name": "Ivan Petrenko",
        "contact_info": "@ivan_dev",
        "domain": "PYTHON",
        "experience_years": 3,
        "english_level": "UPPER_INTERMEDIATE",
        "expected_salary": 2500,
        "age": 25,
        "resume_text": "Backend developer: FastAPI, PostgreSQL, Docker.",
    } | overrides


def recruiter_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "role": "RECRUITER",
        "email": unique_email("recruiter"),
        "password": PASSWORD,
        "full_name": "Olena Kovalenko",
        "contact_info": "@olena_hr",
        "company_name": "Frog Software",
    } | overrides


def vacancy_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "title": "Middle Python Developer",
        "description": "FastAPI, SQLAlchemy 2.0, PostgreSQL. Product team, async services.",
        "domain": "PYTHON",
        "company_type": "PRODUCT",
        "work_format": "REMOTE",
        "experience_years_required": 2,
        "english_level_required": "INTERMEDIATE",
        "salary_min": 2000,
        "salary_max": 3500,
    } | overrides


async def register(client: AsyncClient, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def login(client: AsyncClient, email: str, password: str = PASSWORD) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()


async def auth_headers(client: AsyncClient, payload: dict[str, Any]) -> dict[str, str]:
    await register(client, payload)
    tokens = await login(client, payload["email"], payload["password"])
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def create_vacancy(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/vacancies", json=vacancy_payload(**overrides), headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


async def apply(
    client: AsyncClient, headers: dict[str, str], vacancy_id: int, cover_letter: str | None = None
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/vacancies/{vacancy_id}/apply",
        json={"cover_letter": cover_letter},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def set_status(
    client: AsyncClient, headers: dict[str, str], application_id: int, status: str
) -> Any:
    return await client.patch(
        f"/api/v1/applications/{application_id}/status", json={"status": status}, headers=headers
    )

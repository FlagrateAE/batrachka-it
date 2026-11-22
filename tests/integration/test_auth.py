from httpx import AsyncClient
from sqlalchemy import text

from tests.helpers import PASSWORD, candidate_payload, login, recruiter_payload, register


async def test_candidate_registration_returns_profile_without_password(client: AsyncClient) -> None:
    payload = candidate_payload()

    body = await register(client, payload)

    assert body["role"] == "CANDIDATE"
    assert body["email"] == payload["email"]
    assert body["candidate"]["domain"] == "PYTHON"
    assert body["recruiter"] is None
    assert "password" not in body
    assert "hashed_password" not in body


async def test_recruiter_registration_creates_recruiter_profile(client: AsyncClient) -> None:
    body = await register(client, recruiter_payload(company_name="Frog Software"))

    assert body["role"] == "RECRUITER"
    assert body["recruiter"] == {"company_name": "Frog Software"}
    assert body["candidate"] is None


async def test_password_is_stored_as_argon2_hash(client: AsyncClient, app) -> None:
    payload = candidate_payload()
    await register(client, payload)

    async with app.state.engine.connect() as connection:
        stored = await connection.scalar(
            text("SELECT hashed_password FROM users WHERE email = :email"),
            {"email": payload["email"]},
        )

    assert stored.startswith("$argon2id$")
    assert PASSWORD not in stored


async def test_duplicate_email_is_rejected_case_insensitively(client: AsyncClient) -> None:
    payload = candidate_payload()
    await register(client, payload)

    response = await client.post(
        "/api/v1/auth/register", json=payload | {"email": payload["email"].upper()}
    )

    assert response.status_code == 409


async def test_candidate_without_profile_fields_gets_422(client: AsyncClient) -> None:
    payload = candidate_payload()
    del payload["domain"]

    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422


async def test_login_returns_token_pair(client: AsyncClient) -> None:
    payload = candidate_payload()
    await register(client, payload)

    tokens = await login(client, payload["email"])

    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] and tokens["refresh_token"]
    assert tokens["expires_in"] == 30 * 60


async def test_login_with_wrong_password_returns_401(client: AsyncClient) -> None:
    payload = candidate_payload()
    await register(client, payload)

    response = await client.post(
        "/api/v1/auth/login", data={"username": payload["email"], "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_login_with_unknown_email_returns_same_error(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login", data={"username": "nobody@example.com", "password": PASSWORD}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


async def test_refresh_issues_new_working_pair(client: AsyncClient) -> None:
    payload = candidate_payload()
    await register(client, payload)
    tokens = await login(client, payload["email"])

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 200
    new_access = response.json()["access_token"]
    me = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200


async def test_access_token_is_not_accepted_for_refresh(client: AsyncClient) -> None:
    payload = candidate_payload()
    await register(client, payload)
    tokens = await login(client, payload["email"])

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )

    assert response.status_code == 401


async def test_refresh_token_is_not_accepted_as_bearer(client: AsyncClient) -> None:
    payload = candidate_payload()
    await register(client, payload)
    tokens = await login(client, payload["email"])

    response = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
    )

    assert response.status_code == 401

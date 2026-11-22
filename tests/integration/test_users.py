from httpx import AsyncClient

from tests.helpers import auth_headers, candidate_payload


async def test_profile_requires_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 401


async def test_malformed_token_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401


async def test_own_profile_includes_private_contacts(
    client: AsyncClient, candidate_headers: dict[str, str]
) -> None:
    response = await client.get("/api/v1/users/me", headers=candidate_headers)

    assert response.status_code == 200
    assert response.json()["contact_info"] == "@ivan_dev"


async def test_candidate_updates_common_and_profile_fields(
    client: AsyncClient, candidate_headers: dict[str, str]
) -> None:
    response = await client.patch(
        "/api/v1/users/me",
        json={
            "bio": "Async Python enthusiast",
            "avatar_url": "https://example.com/avatar.png",
            "candidate": {"experience_years": 5, "english_level": "ADVANCED"},
        },
        headers=candidate_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["bio"] == "Async Python enthusiast"
    assert body["avatar_url"] == "https://example.com/avatar.png"
    assert body["candidate"]["experience_years"] == 5
    assert body["candidate"]["english_level"] == "ADVANCED"
    assert body["candidate"]["domain"] == "PYTHON"


async def test_update_is_persisted(client: AsyncClient) -> None:
    headers = await auth_headers(client, candidate_payload())
    await client.patch("/api/v1/users/me", json={"full_name": "Ivan Ivanenko"}, headers=headers)

    response = await client.get("/api/v1/users/me", headers=headers)

    assert response.json()["full_name"] == "Ivan Ivanenko"


async def test_recruiter_updates_company_name(
    client: AsyncClient, recruiter_headers: dict[str, str]
) -> None:
    response = await client.patch(
        "/api/v1/users/me",
        json={"recruiter": {"company_name": "Toad Tech"}},
        headers=recruiter_headers,
    )

    assert response.status_code == 200
    assert response.json()["recruiter"]["company_name"] == "Toad Tech"


async def test_recruiter_cannot_set_candidate_fields(
    client: AsyncClient, recruiter_headers: dict[str, str]
) -> None:
    response = await client.patch(
        "/api/v1/users/me", json={"candidate": {"experience_years": 3}}, headers=recruiter_headers
    )

    assert response.status_code == 422


async def test_candidate_cannot_set_recruiter_fields(
    client: AsyncClient, candidate_headers: dict[str, str]
) -> None:
    response = await client.patch(
        "/api/v1/users/me", json={"recruiter": {"company_name": "Nope"}}, headers=candidate_headers
    )

    assert response.status_code == 422


async def test_null_for_required_field_is_rejected(
    client: AsyncClient, candidate_headers: dict[str, str]
) -> None:
    response = await client.patch(
        "/api/v1/users/me", json={"contact_info": None}, headers=candidate_headers
    )

    assert response.status_code == 422

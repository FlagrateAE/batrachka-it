import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import text

from tests.helpers import apply, auth_headers, candidate_payload, set_status

LOCK_WAIT_SECONDS = 0.5


@asynccontextmanager
async def competing_hire(app: FastAPI, vacancy_id: int) -> AsyncIterator[None]:
    async with app.state.engine.connect() as connection:
        transaction = await connection.begin()
        await connection.execute(
            text("SELECT id FROM vacancies WHERE id = :id FOR UPDATE"), {"id": vacancy_id}
        )
        yield
        await connection.execute(
            text("UPDATE vacancies SET status = 'CLOSED' WHERE id = :id"), {"id": vacancy_id}
        )
        await transaction.commit()


async def test_hiring_waits_for_vacancy_lock_and_sees_fresh_status(
    app: FastAPI,
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    candidate_headers: dict[str, str],
    vacancy: dict,
) -> None:
    application = await apply(client, candidate_headers, vacancy["id"])

    async with competing_hire(app, vacancy["id"]):
        request = asyncio.create_task(
            set_status(client, recruiter_headers, application["id"], "HIRED")
        )
        await asyncio.sleep(LOCK_WAIT_SECONDS)
        assert not request.done()
    response = await request

    assert response.status_code == 409
    assert response.json()["detail"] == "Vacancy is closed"


async def test_applying_waits_for_vacancy_lock_and_sees_fresh_status(
    app: FastAPI, client: AsyncClient, candidate_headers: dict[str, str], vacancy: dict
) -> None:
    async with competing_hire(app, vacancy["id"]):
        request = asyncio.create_task(
            client.post(
                f"/api/v1/vacancies/{vacancy['id']}/apply", json={}, headers=candidate_headers
            )
        )
        await asyncio.sleep(LOCK_WAIT_SECONDS)
        assert not request.done()
    response = await request

    assert response.status_code == 409
    assert response.json()["detail"] == "Vacancy is closed"


async def test_concurrent_hiring_hires_exactly_one_candidate(
    client: AsyncClient, recruiter_headers: dict[str, str], vacancy: dict
) -> None:
    applicants = [await auth_headers(client, candidate_payload()) for _ in range(5)]
    applications = [await apply(client, headers, vacancy["id"]) for headers in applicants]

    responses = await asyncio.gather(
        *(set_status(client, recruiter_headers, item["id"], "HIRED") for item in applications)
    )

    codes = sorted(response.status_code for response in responses)
    assert codes == [200, 409, 409, 409, 409]
    listing = await client.get(
        f"/api/v1/vacancies/{vacancy['id']}/applications", headers=recruiter_headers
    )
    statuses = sorted(item["status"] for item in listing.json()["items"])
    assert statuses == ["HIRED", "REJECTED", "REJECTED", "REJECTED", "REJECTED"]


async def test_concurrent_duplicate_applications_create_one_record(
    client: AsyncClient,
    candidate_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    vacancy: dict,
) -> None:
    url = f"/api/v1/vacancies/{vacancy['id']}/apply"

    responses = await asyncio.gather(
        *(client.post(url, json={}, headers=candidate_headers) for _ in range(5))
    )

    assert sorted(response.status_code for response in responses) == [201, 409, 409, 409, 409]
    listing = await client.get(
        f"/api/v1/vacancies/{vacancy['id']}/applications", headers=recruiter_headers
    )
    assert listing.json()["total"] == 1


async def test_hiring_and_applying_at_once_never_leaves_pending_on_closed_vacancy(
    client: AsyncClient, recruiter_headers: dict[str, str], vacancy: dict
) -> None:
    hired = await apply(client, await auth_headers(client, candidate_payload()), vacancy["id"])
    latecomers = [await auth_headers(client, candidate_payload()) for _ in range(4)]

    await asyncio.gather(
        set_status(client, recruiter_headers, hired["id"], "HIRED"),
        *(
            client.post(f"/api/v1/vacancies/{vacancy['id']}/apply", json={}, headers=headers)
            for headers in latecomers
        ),
    )

    listing = await client.get(
        f"/api/v1/vacancies/{vacancy['id']}/applications", headers=recruiter_headers
    )
    assert "PENDING" not in {item["status"] for item in listing.json()["items"]}

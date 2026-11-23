from httpx import AsyncClient

from tests.helpers import apply, auth_headers, candidate_payload, create_vacancy, set_status


async def test_candidate_applies_with_cover_letter(
    client: AsyncClient, candidate_headers: dict[str, str], vacancy: dict
) -> None:
    body = await apply(client, candidate_headers, vacancy["id"], cover_letter="I love FastAPI")

    assert body["status"] == "PENDING"
    assert body["cover_letter"] == "I love FastAPI"
    assert body["vacancy_id"] == vacancy["id"]


async def test_cover_letter_is_optional(
    client: AsyncClient, candidate_headers: dict[str, str], vacancy: dict
) -> None:
    body = await apply(client, candidate_headers, vacancy["id"])

    assert body["cover_letter"] is None


async def test_second_application_to_same_vacancy_is_rejected(
    client: AsyncClient, candidate_headers: dict[str, str], vacancy: dict
) -> None:
    await apply(client, candidate_headers, vacancy["id"])

    response = await client.post(
        f"/api/v1/vacancies/{vacancy['id']}/apply", json={}, headers=candidate_headers
    )

    assert response.status_code == 409


async def test_recruiter_cannot_apply(
    client: AsyncClient, recruiter_headers: dict[str, str], vacancy: dict
) -> None:
    response = await client.post(
        f"/api/v1/vacancies/{vacancy['id']}/apply", json={}, headers=recruiter_headers
    )

    assert response.status_code == 403


async def test_guest_cannot_apply(client: AsyncClient, vacancy: dict) -> None:
    response = await client.post(f"/api/v1/vacancies/{vacancy['id']}/apply", json={})

    assert response.status_code == 401


async def test_cannot_apply_to_missing_vacancy(
    client: AsyncClient, candidate_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/vacancies/999999/apply", json={}, headers=candidate_headers
    )

    assert response.status_code == 404


async def test_contacts_are_hidden_while_pending(
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    candidate_headers: dict[str, str],
    vacancy: dict,
) -> None:
    application = await apply(client, candidate_headers, vacancy["id"])

    for_recruiter = await client.get(
        f"/api/v1/vacancies/{vacancy['id']}/applications", headers=recruiter_headers
    )
    for_candidate = await client.get(
        f"/api/v1/applications/{application['id']}", headers=candidate_headers
    )

    assert for_recruiter.json()["items"][0]["candidate"]["contact_info"] is None
    assert for_recruiter.json()["items"][0]["candidate"]["experience_years"] == 3
    assert for_candidate.json()["recruiter"]["contact_info"] is None


async def test_accepting_reveals_contacts_to_both_sides(
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    candidate_headers: dict[str, str],
    vacancy: dict,
) -> None:
    application = await apply(client, candidate_headers, vacancy["id"])

    accepted = await set_status(client, recruiter_headers, application["id"], "ACCEPTED")
    for_candidate = await client.get("/api/v1/applications/my", headers=candidate_headers)
    vacancy_state = await client.get(f"/api/v1/vacancies/{vacancy['id']}")

    assert accepted.status_code == 200
    assert accepted.json()["candidate"]["contact_info"] == "@ivan_dev"
    assert for_candidate.json()["items"][0]["recruiter"]["contact_info"] == "@olena_hr"
    assert vacancy_state.json()["status"] == "OPEN"


async def test_rejecting_keeps_contacts_hidden(
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    candidate_headers: dict[str, str],
    vacancy: dict,
) -> None:
    application = await apply(client, candidate_headers, vacancy["id"])

    response = await set_status(client, recruiter_headers, application["id"], "REJECTED")

    assert response.json()["status"] == "REJECTED"
    assert response.json()["candidate"]["contact_info"] is None


async def test_hiring_closes_vacancy_and_rejects_others(
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    vacancy: dict,
) -> None:
    applicants = [await auth_headers(client, candidate_payload()) for _ in range(3)]
    applications = [await apply(client, headers, vacancy["id"]) for headers in applicants]
    await set_status(client, recruiter_headers, applications[1]["id"], "ACCEPTED")

    hired = await set_status(client, recruiter_headers, applications[0]["id"], "HIRED")
    vacancy_state = await client.get(f"/api/v1/vacancies/{vacancy['id']}")
    statuses = await client.get(
        f"/api/v1/vacancies/{vacancy['id']}/applications", headers=recruiter_headers
    )

    assert hired.status_code == 200
    assert hired.json()["candidate"]["contact_info"] == "@ivan_dev"
    assert vacancy_state.json()["status"] == "CLOSED"
    by_id = {item["id"]: item["status"] for item in statuses.json()["items"]}
    assert by_id == {
        applications[0]["id"]: "HIRED",
        applications[1]["id"]: "REJECTED",
        applications[2]["id"]: "REJECTED",
    }


async def test_accepted_candidate_can_be_hired(
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    candidate_headers: dict[str, str],
    vacancy: dict,
) -> None:
    application = await apply(client, candidate_headers, vacancy["id"])
    await set_status(client, recruiter_headers, application["id"], "ACCEPTED")

    response = await set_status(client, recruiter_headers, application["id"], "HIRED")

    assert response.json()["status"] == "HIRED"


async def test_no_applications_after_hiring(
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    candidate_headers: dict[str, str],
    vacancy: dict,
) -> None:
    application = await apply(client, candidate_headers, vacancy["id"])
    await set_status(client, recruiter_headers, application["id"], "HIRED")
    latecomer = await auth_headers(client, candidate_payload())

    response = await client.post(
        f"/api/v1/vacancies/{vacancy['id']}/apply", json={}, headers=latecomer
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Vacancy is closed"


async def test_status_change_on_closed_vacancy_is_refused(
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    vacancy: dict,
) -> None:
    first = await apply(client, await auth_headers(client, candidate_payload()), vacancy["id"])
    second = await apply(client, await auth_headers(client, candidate_payload()), vacancy["id"])
    await set_status(client, recruiter_headers, first["id"], "HIRED")

    response = await set_status(client, recruiter_headers, second["id"], "HIRED")

    assert response.status_code == 409
    assert response.json()["detail"] == "Vacancy is closed"


async def test_rejected_application_cannot_be_reopened(
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    candidate_headers: dict[str, str],
    vacancy: dict,
) -> None:
    application = await apply(client, candidate_headers, vacancy["id"])
    await set_status(client, recruiter_headers, application["id"], "REJECTED")

    response = await set_status(client, recruiter_headers, application["id"], "ACCEPTED")

    assert response.status_code == 409


async def test_only_vacancy_author_can_change_status(
    client: AsyncClient,
    other_recruiter_headers: dict[str, str],
    candidate_headers: dict[str, str],
    vacancy: dict,
) -> None:
    application = await apply(client, candidate_headers, vacancy["id"])

    response = await set_status(client, other_recruiter_headers, application["id"], "ACCEPTED")

    assert response.status_code == 404


async def test_candidate_cannot_change_status(
    client: AsyncClient, candidate_headers: dict[str, str], vacancy: dict
) -> None:
    application = await apply(client, candidate_headers, vacancy["id"])

    response = await set_status(client, candidate_headers, application["id"], "HIRED")

    assert response.status_code == 403


async def test_other_recruiter_cannot_list_applications(
    client: AsyncClient,
    other_recruiter_headers: dict[str, str],
    vacancy: dict,
) -> None:
    response = await client.get(
        f"/api/v1/vacancies/{vacancy['id']}/applications", headers=other_recruiter_headers
    )

    assert response.status_code == 403


async def test_application_is_hidden_from_outsiders(
    client: AsyncClient,
    other_recruiter_headers: dict[str, str],
    candidate_headers: dict[str, str],
    vacancy: dict,
) -> None:
    application = await apply(client, candidate_headers, vacancy["id"])
    outsider = await auth_headers(client, candidate_payload())

    by_candidate = await client.get(f"/api/v1/applications/{application['id']}", headers=outsider)
    by_recruiter = await client.get(
        f"/api/v1/applications/{application['id']}", headers=other_recruiter_headers
    )

    assert (by_candidate.status_code, by_recruiter.status_code) == (404, 404)


async def test_recruiter_sees_application_with_candidate_card(
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    candidate_headers: dict[str, str],
    vacancy: dict,
) -> None:
    application = await apply(client, candidate_headers, vacancy["id"], cover_letter="Hi!")

    response = await client.get(
        f"/api/v1/applications/{application['id']}", headers=recruiter_headers
    )

    body = response.json()
    assert body["candidate"]["full_name"] == "Ivan Petrenko"
    assert body["cover_letter"] == "Hi!"
    assert "recruiter" not in body


async def test_my_applications_filtered_by_status(
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    candidate_headers: dict[str, str],
) -> None:
    first = await create_vacancy(client, recruiter_headers, title="First vacancy")
    second = await create_vacancy(client, recruiter_headers, title="Second vacancy")
    accepted = await apply(client, candidate_headers, first["id"])
    await apply(client, candidate_headers, second["id"])
    await set_status(client, recruiter_headers, accepted["id"], "ACCEPTED")

    everything = await client.get("/api/v1/applications/my", headers=candidate_headers)
    only_accepted = await client.get(
        "/api/v1/applications/my", params={"status": "ACCEPTED"}, headers=candidate_headers
    )

    assert everything.json()["total"] == 2
    assert [item["id"] for item in only_accepted.json()["items"]] == [accepted["id"]]
    assert only_accepted.json()["items"][0]["vacancy"]["title"] == "First vacancy"


async def test_vacancy_applications_filtered_by_status(
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    vacancy: dict,
) -> None:
    pending = await apply(client, await auth_headers(client, candidate_payload()), vacancy["id"])
    rejected = await apply(client, await auth_headers(client, candidate_payload()), vacancy["id"])
    await set_status(client, recruiter_headers, rejected["id"], "REJECTED")

    response = await client.get(
        f"/api/v1/vacancies/{vacancy['id']}/applications",
        params={"status": "PENDING"},
        headers=recruiter_headers,
    )

    assert [item["id"] for item in response.json()["items"]] == [pending["id"]]


async def test_recruiter_cannot_use_candidate_listing(
    client: AsyncClient, recruiter_headers: dict[str, str]
) -> None:
    response = await client.get("/api/v1/applications/my", headers=recruiter_headers)

    assert response.status_code == 403

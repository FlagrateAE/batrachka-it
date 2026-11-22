import pytest
from httpx import AsyncClient

from tests.helpers import apply, create_vacancy, vacancy_payload


async def test_recruiter_publishes_open_vacancy(
    client: AsyncClient, recruiter_headers: dict[str, str]
) -> None:
    body = await create_vacancy(client, recruiter_headers)

    assert body["status"] == "OPEN"
    assert body["company_name"] == "Frog Software"
    assert body["salary_min"] == 2000 and body["salary_max"] == 3500


async def test_guest_cannot_publish_vacancy(client: AsyncClient) -> None:
    response = await client.post("/api/v1/vacancies", json=vacancy_payload())

    assert response.status_code == 401


async def test_candidate_cannot_publish_vacancy(
    client: AsyncClient, candidate_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/vacancies", json=vacancy_payload(), headers=candidate_headers
    )

    assert response.status_code == 403


async def test_inverted_salary_fork_is_rejected(
    client: AsyncClient, recruiter_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/vacancies",
        json=vacancy_payload(salary_min=4000, salary_max=1000),
        headers=recruiter_headers,
    )

    assert response.status_code == 422


async def test_guest_reads_vacancy_without_recruiter_contacts(
    client: AsyncClient, vacancy: dict
) -> None:
    response = await client.get(f"/api/v1/vacancies/{vacancy['id']}")

    assert response.status_code == 200
    assert "contact_info" not in response.json()
    assert "@olena_hr" not in response.text


async def test_missing_vacancy_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/vacancies/999999")

    assert response.status_code == 404


@pytest.fixture
async def catalog(client: AsyncClient, recruiter_headers: dict[str, str]) -> dict[str, int]:
    specs = {
        "python_remote": {
            "domain": "PYTHON",
            "work_format": "REMOTE",
            "salary_min": 2000,
            "salary_max": 3000,
            "experience_years_required": 2,
            "english_level_required": "INTERMEDIATE",
            "company_type": "PRODUCT",
        },
        "python_senior": {
            "domain": "PYTHON",
            "work_format": "OFFICE",
            "salary_min": 5000,
            "salary_max": 7000,
            "experience_years_required": 5,
            "english_level_required": "ADVANCED",
            "company_type": "OUTSOURCE",
        },
        "java_hybrid": {
            "domain": "JAVA",
            "work_format": "HYBRID",
            "salary_min": 3000,
            "salary_max": 4500,
            "experience_years_required": 3,
            "english_level_required": "UPPER_INTERMEDIATE",
            "company_type": "STARTUP",
        },
        "qa_junior": {
            "domain": "QA",
            "work_format": "REMOTE",
            "salary_min": 800,
            "salary_max": 1200,
            "experience_years_required": 0,
            "english_level_required": "PRE_INTERMEDIATE",
            "company_type": "OUTSTAFF",
        },
    }
    ids = {}
    for name, spec in specs.items():
        ids[name] = (await create_vacancy(client, recruiter_headers, **spec))["id"]
    return ids


async def search(client: AsyncClient, **params) -> list[int]:
    response = await client.get("/api/v1/vacancies", params=params)
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


async def test_filter_by_domain(client: AsyncClient, catalog: dict[str, int]) -> None:
    found = await search(client, domain="PYTHON")

    assert set(found) == {catalog["python_remote"], catalog["python_senior"]}


async def test_filter_by_work_format_and_company_type(
    client: AsyncClient, catalog: dict[str, int]
) -> None:
    assert await search(client, work_format="REMOTE", company_type="OUTSTAFF") == [
        catalog["qa_junior"]
    ]


async def test_filter_by_salary_overlap(client: AsyncClient, catalog: dict[str, int]) -> None:
    found = await search(client, salary_from=4000)

    assert set(found) == {catalog["python_senior"], catalog["java_hybrid"]}


async def test_filter_by_salary_window(client: AsyncClient, catalog: dict[str, int]) -> None:
    found = await search(client, salary_from=1000, salary_to=2500)

    assert set(found) == {catalog["python_remote"], catalog["qa_junior"]}


async def test_filter_by_candidate_experience(client: AsyncClient, catalog: dict[str, int]) -> None:
    found = await search(client, experience_years=2)

    assert set(found) == {catalog["python_remote"], catalog["qa_junior"]}


async def test_english_filter_uses_level_order(
    client: AsyncClient, catalog: dict[str, int]
) -> None:
    found = await search(client, english_level="UPPER_INTERMEDIATE")

    assert set(found) == {catalog["python_remote"], catalog["java_hybrid"], catalog["qa_junior"]}


async def test_combined_filters(client: AsyncClient, catalog: dict[str, int]) -> None:
    found = await search(
        client, domain="PYTHON", experience_years=6, english_level="PROFICIENT", salary_from=6000
    )

    assert found == [catalog["python_senior"]]


async def test_sort_by_salary_desc(client: AsyncClient, catalog: dict[str, int]) -> None:
    found = await search(client, sort_by="salary_max", order="desc")

    assert found == [
        catalog["python_senior"],
        catalog["java_hybrid"],
        catalog["python_remote"],
        catalog["qa_junior"],
    ]


async def test_default_sort_is_newest_first(client: AsyncClient, catalog: dict[str, int]) -> None:
    found = await search(client)

    assert found == sorted(catalog.values(), reverse=True)


async def test_invalid_filter_value_returns_422(client: AsyncClient) -> None:
    response = await client.get("/api/v1/vacancies", params={"domain": "COBOL"})

    assert response.status_code == 422


async def test_default_page_size_is_20(
    client: AsyncClient, recruiter_headers: dict[str, str]
) -> None:
    for index in range(23):
        await create_vacancy(client, recruiter_headers, title=f"Vacancy number {index}")

    first = (await client.get("/api/v1/vacancies")).json()
    second = (await client.get("/api/v1/vacancies", params={"offset": 20})).json()

    assert (first["total"], first["limit"], len(first["items"])) == (23, 20, 20)
    assert len(second["items"]) == 3
    assert not {i["id"] for i in first["items"]} & {i["id"] for i in second["items"]}


async def test_closed_vacancy_is_excluded_from_search(
    client: AsyncClient, recruiter_headers: dict[str, str], vacancy: dict
) -> None:
    await client.post(f"/api/v1/vacancies/{vacancy['id']}/close", headers=recruiter_headers)

    assert await search(client) == []


async def test_author_edits_vacancy(
    client: AsyncClient, recruiter_headers: dict[str, str], vacancy: dict
) -> None:
    response = await client.patch(
        f"/api/v1/vacancies/{vacancy['id']}",
        json={"title": "Senior Python Developer", "salary_max": 6000},
        headers=recruiter_headers,
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Senior Python Developer"
    assert response.json()["salary_max"] == 6000


async def test_partial_edit_cannot_invert_salary_fork(
    client: AsyncClient, recruiter_headers: dict[str, str], vacancy: dict
) -> None:
    response = await client.patch(
        f"/api/v1/vacancies/{vacancy['id']}", json={"salary_min": 9000}, headers=recruiter_headers
    )

    assert response.status_code == 422


async def test_other_recruiter_cannot_edit_close_or_delete(
    client: AsyncClient, other_recruiter_headers: dict[str, str], vacancy: dict
) -> None:
    url = f"/api/v1/vacancies/{vacancy['id']}"

    edit = await client.patch(url, json={"title": "Hijacked"}, headers=other_recruiter_headers)
    close = await client.post(f"{url}/close", headers=other_recruiter_headers)
    delete = await client.delete(url, headers=other_recruiter_headers)

    assert (edit.status_code, close.status_code, delete.status_code) == (403, 403, 403)


async def test_closed_vacancy_cannot_be_edited_or_closed_again(
    client: AsyncClient, recruiter_headers: dict[str, str], vacancy: dict
) -> None:
    url = f"/api/v1/vacancies/{vacancy['id']}"
    await client.post(f"{url}/close", headers=recruiter_headers)

    edit = await client.patch(url, json={"title": "Too late"}, headers=recruiter_headers)
    close = await client.post(f"{url}/close", headers=recruiter_headers)

    assert (edit.status_code, close.status_code) == (409, 409)


async def test_manual_close_rejects_active_applications(
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    candidate_headers: dict[str, str],
    vacancy: dict,
) -> None:
    application = await apply(client, candidate_headers, vacancy["id"])

    response = await client.post(
        f"/api/v1/vacancies/{vacancy['id']}/close", headers=recruiter_headers
    )
    mine = await client.get(f"/api/v1/applications/{application['id']}", headers=candidate_headers)

    assert response.json()["status"] == "CLOSED"
    assert mine.json()["status"] == "REJECTED"


async def test_delete_cascades_to_applications(
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    candidate_headers: dict[str, str],
    vacancy: dict,
) -> None:
    application = await apply(client, candidate_headers, vacancy["id"])

    response = await client.delete(f"/api/v1/vacancies/{vacancy['id']}", headers=recruiter_headers)
    after = await client.get(f"/api/v1/applications/{application['id']}", headers=candidate_headers)

    assert response.status_code == 204
    assert after.status_code == 404


async def test_own_vacancies_include_application_count(
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    other_recruiter_headers: dict[str, str],
    candidate_headers: dict[str, str],
    vacancy: dict,
) -> None:
    await create_vacancy(client, other_recruiter_headers, title="Foreign vacancy")
    await apply(client, candidate_headers, vacancy["id"])

    response = await client.get("/api/v1/vacancies/my", headers=recruiter_headers)

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == vacancy["id"]
    assert body["items"][0]["applications_count"] == 1


async def test_candidate_cannot_list_recruiter_vacancies(
    client: AsyncClient, candidate_headers: dict[str, str]
) -> None:
    response = await client.get("/api/v1/vacancies/my", headers=candidate_headers)

    assert response.status_code == 403

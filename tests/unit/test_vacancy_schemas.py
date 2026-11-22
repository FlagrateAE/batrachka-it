import pytest
from pydantic import ValidationError

from app.applications.schemas import ApplicationStatusUpdate, contacts_revealed
from app.common.enums import ApplicationStatus
from app.common.schemas import DEFAULT_PAGE_SIZE
from app.vacancies.schemas import VacancyCreate, VacancyQuery, VacancyUpdate
from tests.helpers import vacancy_payload


def test_valid_vacancy_is_accepted() -> None:
    vacancy = VacancyCreate.model_validate(vacancy_payload())

    assert vacancy.salary_min <= vacancy.salary_max


def test_inverted_salary_fork_is_rejected() -> None:
    with pytest.raises(ValidationError, match="salary_min must not exceed salary_max"):
        VacancyCreate.model_validate(vacancy_payload(salary_min=5000, salary_max=1000))


@pytest.mark.parametrize("field", ["salary_min", "experience_years_required"])
def test_negative_numbers_are_rejected(field: str) -> None:
    with pytest.raises(ValidationError):
        VacancyCreate.model_validate(vacancy_payload(**{field: -1}))


def test_unknown_domain_is_rejected() -> None:
    with pytest.raises(ValidationError):
        VacancyCreate.model_validate(vacancy_payload(domain="COBOL"))


def test_vacancy_update_rejects_null_title() -> None:
    with pytest.raises(ValidationError, match="title"):
        VacancyUpdate.model_validate({"title": None})


def test_query_defaults_match_specification() -> None:
    query = VacancyQuery()

    assert (query.limit, query.offset) == (DEFAULT_PAGE_SIZE, 0)
    assert (query.sort_by, query.order) == ("created_at", "desc")


def test_query_rejects_inverted_salary_range() -> None:
    with pytest.raises(ValidationError):
        VacancyQuery(salary_from=5000, salary_to=1000)


def test_query_rejects_page_size_over_limit() -> None:
    with pytest.raises(ValidationError):
        VacancyQuery(limit=101)


def test_pending_cannot_be_set_by_recruiter() -> None:
    with pytest.raises(ValidationError):
        ApplicationStatusUpdate.model_validate({"status": "PENDING"})


@pytest.mark.parametrize(
    ("status", "revealed"),
    [
        (ApplicationStatus.PENDING, False),
        (ApplicationStatus.REJECTED, False),
        (ApplicationStatus.ACCEPTED, True),
        (ApplicationStatus.HIRED, True),
    ],
)
def test_contacts_are_revealed_only_after_approval(
    status: ApplicationStatus, revealed: bool
) -> None:
    assert contacts_revealed(status) is revealed

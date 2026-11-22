import pytest
from pydantic import TypeAdapter, ValidationError

from app.auth.schemas import CandidateRegister, RecruiterRegister, RegisterRequest
from app.users.schemas import UserUpdate
from tests.helpers import candidate_payload, recruiter_payload

register_adapter: TypeAdapter[CandidateRegister | RecruiterRegister] = TypeAdapter(RegisterRequest)


def test_role_selects_registration_schema() -> None:
    assert isinstance(register_adapter.validate_python(candidate_payload()), CandidateRegister)
    assert isinstance(register_adapter.validate_python(recruiter_payload()), RecruiterRegister)


def test_email_is_normalized_to_lowercase() -> None:
    data = register_adapter.validate_python(candidate_payload(email="Ivan.Dev@Example.COM"))

    assert data.email == "ivan.dev@example.com"


@pytest.mark.parametrize(
    "missing", ["domain", "experience_years", "english_level", "expected_salary"]
)
def test_candidate_registration_requires_profile_fields(missing: str) -> None:
    payload = candidate_payload()
    payload.pop(missing)

    with pytest.raises(ValidationError):
        register_adapter.validate_python(payload)


def test_recruiter_registration_requires_company_name() -> None:
    payload = recruiter_payload()
    payload.pop("company_name")

    with pytest.raises(ValidationError):
        register_adapter.validate_python(payload)


def test_unknown_role_is_rejected() -> None:
    with pytest.raises(ValidationError):
        register_adapter.validate_python(candidate_payload(role="ADMIN"))


def test_short_password_is_rejected() -> None:
    with pytest.raises(ValidationError):
        register_adapter.validate_python(candidate_payload(password="short"))


def test_user_update_rejects_null_for_required_fields() -> None:
    with pytest.raises(ValidationError, match="full_name"):
        UserUpdate.model_validate({"full_name": None})


def test_user_update_allows_null_for_optional_fields() -> None:
    update = UserUpdate.model_validate({"bio": None})

    assert update.model_fields_set == {"bio"}


def test_user_update_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        UserUpdate.model_validate({"email": "new@example.com"})

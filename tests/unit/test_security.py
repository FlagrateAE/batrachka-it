from datetime import timedelta

import jwt
import pytest

from app.common.enums import UserRole
from app.core.exceptions import AuthenticationError
from app.core.security import PasswordHasher, TokenService, TokenType

SECRET = "unit-test-secret-key-that-is-long-enough"


@pytest.fixture(scope="module")
def hasher() -> PasswordHasher:
    return PasswordHasher()


@pytest.fixture
def tokens() -> TokenService:
    return TokenService(SECRET, "HS256", timedelta(minutes=5), timedelta(days=1))


def test_password_is_hashed_with_argon2(hasher: PasswordHasher) -> None:
    hashed = hasher.hash("Str0ngPassw0rd!")

    assert hashed.startswith("$argon2id$")
    assert "Str0ngPassw0rd!" not in hashed


def test_password_hash_is_salted(hasher: PasswordHasher) -> None:
    assert hasher.hash("same-password") != hasher.hash("same-password")


def test_verify_accepts_correct_and_rejects_wrong_password(hasher: PasswordHasher) -> None:
    hashed = hasher.hash("Str0ngPassw0rd!")

    assert hasher.verify("Str0ngPassw0rd!", hashed)
    assert not hasher.verify("wrong-password", hashed)


def test_issued_pair_decodes_to_original_claims(tokens: TokenService) -> None:
    pair = tokens.issue_pair(42, UserRole.RECRUITER)

    access = tokens.decode(pair.access_token, TokenType.ACCESS)
    refresh = tokens.decode(pair.refresh_token, TokenType.REFRESH)

    assert (access.user_id, access.role) == (42, UserRole.RECRUITER)
    assert refresh.token_type is TokenType.REFRESH
    assert pair.expires_in == 300


def test_access_token_cannot_be_used_as_refresh(tokens: TokenService) -> None:
    pair = tokens.issue_pair(1, UserRole.CANDIDATE)

    with pytest.raises(AuthenticationError, match="Invalid token type"):
        tokens.decode(pair.access_token, TokenType.REFRESH)


def test_expired_token_is_rejected() -> None:
    expired = TokenService(SECRET, "HS256", timedelta(seconds=-1), timedelta(seconds=-1))
    pair = expired.issue_pair(1, UserRole.CANDIDATE)

    with pytest.raises(AuthenticationError, match="expired"):
        expired.decode(pair.access_token, TokenType.ACCESS)


def test_token_signed_with_another_key_is_rejected(tokens: TokenService) -> None:
    forged = TokenService(
        "another-secret-key-that-is-long-enough", "HS256", timedelta(1), timedelta(1)
    )
    pair = forged.issue_pair(1, UserRole.RECRUITER)

    with pytest.raises(AuthenticationError):
        tokens.decode(pair.access_token, TokenType.ACCESS)


def test_token_without_required_claims_is_rejected(tokens: TokenService) -> None:
    token = jwt.encode({"sub": "1"}, SECRET, algorithm="HS256")

    with pytest.raises(AuthenticationError):
        tokens.decode(token, TokenType.ACCESS)


def test_token_with_unknown_role_is_rejected(tokens: TokenService) -> None:
    token = jwt.encode(
        {"sub": "1", "role": "ADMIN", "type": "access", "iat": 0, "exp": 9_999_999_999},
        SECRET,
        algorithm="HS256",
    )

    with pytest.raises(AuthenticationError):
        tokens.decode(token, TokenType.ACCESS)

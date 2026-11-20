import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Self

import jwt
from pwdlib import PasswordHash

from app.common.enums import UserRole
from app.core.config import Settings
from app.core.exceptions import AuthenticationError


class PasswordHasher:
    def __init__(self) -> None:
        self._context = PasswordHash.recommended()
        self._dummy_hash = self._context.hash(uuid.uuid4().hex)

    def hash(self, password: str) -> str:
        return self._context.hash(password)

    def verify(self, password: str, hashed_password: str) -> bool:
        return self._context.verify(password, hashed_password)

    def verify_dummy(self, password: str) -> None:
        # Spends the same time as a real check so that unknown emails cannot be detected by timing.
        self._context.verify(password, self._dummy_hash)


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True, slots=True)
class TokenPayload:
    user_id: int
    role: UserRole
    token_type: TokenType


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


class TokenService:
    def __init__(
        self,
        secret_key: str,
        algorithm: str,
        access_ttl: timedelta,
        refresh_ttl: timedelta,
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        return cls(
            secret_key=settings.jwt_secret_key.get_secret_value(),
            algorithm=settings.jwt_algorithm,
            access_ttl=timedelta(minutes=settings.access_token_expire_minutes),
            refresh_ttl=timedelta(days=settings.refresh_token_expire_days),
        )

    def issue_pair(self, user_id: int, role: UserRole) -> TokenPair:
        return TokenPair(
            access_token=self._encode(user_id, role, TokenType.ACCESS, self._access_ttl),
            refresh_token=self._encode(user_id, role, TokenType.REFRESH, self._refresh_ttl),
            expires_in=int(self._access_ttl.total_seconds()),
        )

    def decode(self, token: str, expected_type: TokenType) -> TokenPayload:
        try:
            claims = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                options={"require": ["exp", "iat", "sub", "type", "role"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Token has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("Could not validate credentials") from exc

        if claims["type"] != expected_type:
            raise AuthenticationError("Invalid token type")
        try:
            return TokenPayload(
                user_id=int(claims["sub"]),
                role=UserRole(claims["role"]),
                token_type=expected_type,
            )
        except ValueError as exc:
            raise AuthenticationError("Could not validate credentials") from exc

    def _encode(self, user_id: int, role: UserRole, token_type: TokenType, ttl: timedelta) -> str:
        now = datetime.now(UTC)
        claims = {
            "sub": str(user_id),
            "role": role.value,
            "type": token_type.value,
            "iat": now,
            "exp": now + ttl,
            "jti": uuid.uuid4().hex,
        }
        return jwt.encode(claims, self._secret_key, algorithm=self._algorithm)

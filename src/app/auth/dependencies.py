from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.auth.service import AuthService
from app.common.enums import UserRole
from app.core.dependencies import PasswordHasherDep, SessionDep, TokenServiceDep
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import TokenType
from app.users.dependencies import UserRepositoryDep
from app.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_auth_service(
    session: SessionDep,
    users: UserRepositoryDep,
    hasher: PasswordHasherDep,
    tokens: TokenServiceDep,
) -> AuthService:
    return AuthService(users=users, hasher=hasher, tokens=tokens, uow=session)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    tokens: TokenServiceDep,
    users: UserRepositoryDep,
) -> User:
    payload = tokens.decode(token, TokenType.ACCESS)
    user = await users.get_by_id(payload.user_id)
    if user is None:
        raise AuthenticationError("User no longer exists")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(role: UserRole) -> Callable[[User], Awaitable[User]]:
    async def dependency(user: CurrentUser) -> User:
        if user.role is not role:
            raise PermissionDeniedError(f"This action is available only for {role.lower()}s")
        return user

    return dependency


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CurrentCandidate = Annotated[User, Depends(require_role(UserRole.CANDIDATE))]
CurrentRecruiter = Annotated[User, Depends(require_role(UserRole.RECRUITER))]

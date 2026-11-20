from typing import Protocol

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import ConflictError
from app.users.models import User


class UserRepository(Protocol):
    async def get_by_id(self, user_id: int) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def add(self, user: User) -> None: ...


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self._session.scalar(self._select().where(User.user_id == user_id))

    async def get_by_email(self, email: str) -> User | None:
        return await self._session.scalar(self._select().where(User.email == email))

    async def add(self, user: User) -> None:
        try:
            async with self._session.begin_nested():
                self._session.add(user)
        except IntegrityError as exc:
            raise ConflictError("User with this email already exists") from exc

    @staticmethod
    def _select() -> Select[tuple[User]]:
        return select(User).options(joinedload(User.candidate), joinedload(User.recruiter))

from typing import Annotated

from fastapi import Depends

from app.core.dependencies import SessionDep
from app.users.repository import SqlAlchemyUserRepository, UserRepository
from app.users.service import UserService


def get_user_repository(session: SessionDep) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_user_service(session: SessionDep) -> UserService:
    return UserService(uow=session)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]

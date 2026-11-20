from fastapi import APIRouter

from app.auth.dependencies import CurrentUser
from app.users.dependencies import UserServiceDep
from app.users.schemas import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", summary="Get own profile, including private contacts")
async def read_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/me", summary="Partially update own profile")
async def update_me(payload: UserUpdate, user: CurrentUser, service: UserServiceDep) -> UserRead:
    updated = await service.update_profile(user, payload)
    return UserRead.model_validate(updated)

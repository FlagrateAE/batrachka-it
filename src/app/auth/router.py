from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.dependencies import AuthServiceDep
from app.auth.schemas import RefreshRequest, RegisterRequest, TokenResponse
from app.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a candidate or a recruiter",
)
async def register(payload: RegisterRequest, service: AuthServiceDep) -> UserRead:
    user = await service.register(payload)
    return UserRead.model_validate(user)


@router.post("/login", summary="Exchange email (as username) and password for a token pair")
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], service: AuthServiceDep
) -> TokenResponse:
    pair = await service.login(form.username, form.password)
    return TokenResponse.from_pair(pair)


@router.post("/refresh", summary="Exchange a refresh token for a new token pair")
async def refresh(payload: RefreshRequest, service: AuthServiceDep) -> TokenResponse:
    pair = await service.refresh(payload.refresh_token)
    return TokenResponse.from_pair(pair)

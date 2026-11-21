from fastapi import APIRouter

from app.applications.router import router as applications_router
from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.vacancies.router import router as vacancies_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(vacancies_router)
api_router.include_router(applications_router)

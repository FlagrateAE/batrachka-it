from app.applications.models import Application
from app.common.db import Base
from app.users.models import Candidate, Recruiter, User
from app.vacancies.models import Vacancy

__all__ = ["Application", "Base", "Candidate", "Recruiter", "User", "Vacancy"]

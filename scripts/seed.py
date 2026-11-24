"""Fill the database with demo accounts and random vacancies for manual and load testing."""

import argparse
import asyncio
import random

from sqlalchemy import insert, select

import app.models  # noqa: F401
from app.common.enums import (
    CompanyType,
    EnglishLevel,
    TechDomain,
    UserRole,
    VacancyStatus,
    WorkFormat,
)
from app.core.config import DatabaseSettings
from app.core.database import build_engine, build_session_factory
from app.core.security import PasswordHasher
from app.users.models import Candidate, Recruiter, User
from app.vacancies.models import Vacancy

DEMO_PASSWORD = "DemoPass123!"
RECRUITER_EMAIL = "seed.recruiter@batrachka.it"
CANDIDATE_EMAIL = "seed.candidate@batrachka.it"
CHUNK_SIZE = 1_000

TITLES = {
    TechDomain.PYTHON: ["Python Developer", "Django Engineer", "FastAPI Backend Engineer"],
    TechDomain.DOTNET: [".NET Developer", "C# Backend Engineer", "ASP.NET Core Developer"],
    TechDomain.JAVA: ["Java Developer", "Spring Boot Engineer", "Kotlin/Java Backend Engineer"],
    TechDomain.GAMEDEV: ["Unity Developer", "Unreal Engine Programmer", "Gameplay Engineer"],
    TechDomain.PROJECT_MANAGEMENT: ["Project Manager", "Delivery Manager", "Scrum Master"],
    TechDomain.QA: ["Manual QA Engineer", "QA Automation Engineer", "SDET"],
    TechDomain.EMBEDDED: ["Embedded C Developer", "Firmware Engineer", "Embedded Linux Engineer"],
}
SENIORITY = ["Junior", "Middle", "Senior", "Lead"]


async def ensure_user(session, hasher: PasswordHasher, email: str, role: UserRole) -> User:
    user = await session.scalar(select(User).where(User.email == email))
    if user is not None:
        return user
    user = User(
        email=email,
        hashed_password=hasher.hash(DEMO_PASSWORD),
        role=role,
        full_name="Seed Recruiter" if role is UserRole.RECRUITER else "Seed Candidate",
        contact_info="@seed_recruiter" if role is UserRole.RECRUITER else "@seed_candidate",
    )
    if role is UserRole.RECRUITER:
        user.recruiter = Recruiter(company_name="Seed Company")
    else:
        user.candidate = Candidate(
            domain=TechDomain.PYTHON,
            experience_years=3,
            english_level=EnglishLevel.UPPER_INTERMEDIATE,
            expected_salary=3000,
            age=27,
        )
    session.add(user)
    await session.flush()
    return user


def random_vacancy(recruiter_id: int, rng: random.Random) -> dict:
    domain = rng.choice(list(TechDomain))
    seniority = rng.randrange(len(SENIORITY))
    salary_min = rng.randrange(500, 3_000, 100) * (seniority + 1)
    return {
        "recruiter_id": recruiter_id,
        "title": f"{SENIORITY[seniority]} {rng.choice(TITLES[domain])}",
        "description": "Generated vacancy for load testing. " * 5,
        "domain": domain,
        "company_type": rng.choice(list(CompanyType)),
        "work_format": rng.choice(list(WorkFormat)),
        "experience_years_required": rng.randint(seniority * 2, seniority * 2 + 2),
        "english_level_required": rng.choice(list(EnglishLevel)),
        "salary_min": salary_min,
        "salary_max": salary_min + rng.randrange(500, 3_000, 100),
        "status": VacancyStatus.OPEN if rng.random() < 0.9 else VacancyStatus.CLOSED,
    }


async def seed(vacancies: int, random_seed: int) -> None:
    engine = build_engine(DatabaseSettings())
    session_factory = build_session_factory(engine)
    hasher = PasswordHasher()
    rng = random.Random(random_seed)

    async with session_factory() as session:
        recruiter = await ensure_user(session, hasher, RECRUITER_EMAIL, UserRole.RECRUITER)
        await ensure_user(session, hasher, CANDIDATE_EMAIL, UserRole.CANDIDATE)
        for start in range(0, vacancies, CHUNK_SIZE):
            rows = [
                random_vacancy(recruiter.user_id, rng)
                for _ in range(min(CHUNK_SIZE, vacancies - start))
            ]
            await session.execute(insert(Vacancy), rows)
        await session.commit()
    await engine.dispose()

    print(f"Inserted {vacancies} vacancies.")
    print(f"Recruiter: {RECRUITER_EMAIL} / {DEMO_PASSWORD}")
    print(f"Candidate: {CANDIDATE_EMAIL} / {DEMO_PASSWORD}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vacancies", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42, help="random seed for reproducible data")
    args = parser.parse_args()
    asyncio.run(seed(args.vacancies, args.seed))


if __name__ == "__main__":
    main()

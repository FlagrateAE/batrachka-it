from app.core.database import UnitOfWork
from app.core.exceptions import InvalidInputError
from app.users.models import User
from app.users.schemas import UserUpdate


class UserService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        changes = data.model_dump(exclude_unset=True, exclude={"candidate", "recruiter"})
        if changes.get("avatar_url") is not None:
            changes["avatar_url"] = str(changes["avatar_url"])
        for field, value in changes.items():
            setattr(user, field, value)

        if data.candidate is not None:
            if user.candidate is None:
                raise InvalidInputError(
                    "Candidate profile fields can be updated only by candidates"
                )
            for field, value in data.candidate.model_dump(exclude_unset=True).items():
                setattr(user.candidate, field, value)

        if data.recruiter is not None:
            if user.recruiter is None:
                raise InvalidInputError(
                    "Recruiter profile fields can be updated only by recruiters"
                )
            for field, value in data.recruiter.model_dump(exclude_unset=True).items():
                setattr(user.recruiter, field, value)

        await self._uow.commit()
        return user

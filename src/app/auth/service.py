from app.auth.schemas import CandidateRegister, RecruiterRegister
from app.common.enums import UserRole
from app.core.database import UnitOfWork
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import PasswordHasher, TokenPair, TokenService, TokenType
from app.users.models import Candidate, Recruiter, User
from app.users.repository import UserRepository


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenService,
        uow: UnitOfWork,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens
        self._uow = uow

    async def register(self, data: CandidateRegister | RecruiterRegister) -> User:
        if await self._users.get_by_email(data.email) is not None:
            raise ConflictError("User with this email already exists")

        user = User(
            email=data.email,
            hashed_password=self._hasher.hash(data.password),
            role=UserRole(data.role),
            full_name=data.full_name,
            contact_info=data.contact_info,
            candidate=None,
            recruiter=None,
        )
        match data:
            case CandidateRegister():
                user.candidate = Candidate(
                    age=data.age,
                    domain=data.domain,
                    experience_years=data.experience_years,
                    english_level=data.english_level,
                    expected_salary=data.expected_salary,
                    resume_text=data.resume_text,
                )
            case RecruiterRegister():
                user.recruiter = Recruiter(company_name=data.company_name)

        await self._users.add(user)
        await self._uow.commit()
        return user

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self._users.get_by_email(email.lower())
        if user is None:
            self._hasher.verify_dummy(password)
            raise AuthenticationError("Incorrect email or password")
        if not self._hasher.verify(password, user.hashed_password):
            raise AuthenticationError("Incorrect email or password")
        return self._tokens.issue_pair(user.user_id, user.role)

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = self._tokens.decode(refresh_token, TokenType.REFRESH)
        user = await self._users.get_by_id(payload.user_id)
        if user is None:
            raise AuthenticationError("User no longer exists")
        return self._tokens.issue_pair(user.user_id, user.role)

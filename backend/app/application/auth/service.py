import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.domain.models.user import User
from app.ports.repositories import UserRepository


class DuplicateUserError(Exception):
    """Raised when a user with the given email already exists."""


def hash_password(password: str) -> str:
    # passlib's bcrypt backend has a known incompatibility with bcrypt>=4.1
    # (relies on a `__about__.__version__` attribute bcrypt removed) - using
    # the bcrypt package directly instead of routing through passlib.
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


class AuthService:
    def __init__(
        self, user_repository: UserRepository, secret_key: str, algorithm: str, access_token_expire_minutes: int
    ) -> None:
        self.user_repository = user_repository
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes

    async def register(self, email: str, password: str) -> User:
        existing = await self.user_repository.get_by_email(email)
        if existing is not None:
            raise DuplicateUserError(email)

        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hash_password(password),
            created_at=datetime.now(timezone.utc),
        )
        return await self.user_repository.create(user)

    async def authenticate(self, email: str, password: str) -> str | None:
        """Returns a signed access token on success, None on bad credentials."""
        user = await self.user_repository.get_by_email(email)
        if user is None or not user.is_active or not verify_password(password, user.hashed_password):
            return None

        expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        return jwt.encode({"sub": str(user.id), "exp": expire}, self.secret_key, algorithm=self.algorithm)

    async def get_user_from_token(self, token: str) -> User | None:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("sub")
            if user_id is None:
                return None
        except JWTError:
            return None

        return await self.user_repository.get_by_id(uuid.UUID(user_id))

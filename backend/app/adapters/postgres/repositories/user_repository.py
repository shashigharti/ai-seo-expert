from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.models.user import UserModel
from app.domain.models.user import User


class PostgresUserRepository:
    """Adapter implementing the UserRepository port via SQLAlchemy."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, user: User) -> User:
        row = UserModel(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            is_active=user.is_active,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return User.model_validate(row)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(UserModel).where(UserModel.email == email))
        row = result.scalar_one_or_none()
        return User.model_validate(row) if row else None

    async def get_by_id(self, user_id: UUID) -> User | None:
        row = await self.db.get(UserModel, user_id)
        return User.model_validate(row) if row else None

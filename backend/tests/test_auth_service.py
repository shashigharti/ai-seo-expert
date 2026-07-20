import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.repositories.user_repository import PostgresUserRepository
from app.application.auth.service import AuthService, DuplicateUserError, hash_password, verify_password


def test_hash_password_produces_a_verifiable_but_different_string():
    hashed = hash_password("correct-horse-battery-staple")
    assert hashed != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", hashed) is True
    assert verify_password("wrong-password", hashed) is False


@pytest.fixture
def service(db_session: AsyncSession) -> AuthService:
    return AuthService(
        PostgresUserRepository(db_session),
        secret_key="test-secret",
        algorithm="HS256",
        access_token_expire_minutes=30,
    )


async def test_register_creates_a_user_with_a_hashed_password(service: AuthService):
    user = await service.register("test@example.com", "testpass123")

    assert user.email == "test@example.com"
    assert user.hashed_password != "testpass123"
    assert user.is_active is True


async def test_register_rejects_duplicate_email(service: AuthService):
    await service.register("test@example.com", "testpass123")
    with pytest.raises(DuplicateUserError):
        await service.register("test@example.com", "anotherpass456")


async def test_authenticate_returns_token_for_correct_credentials(service: AuthService):
    await service.register("test@example.com", "testpass123")
    token = await service.authenticate("test@example.com", "testpass123")
    assert token is not None
    assert isinstance(token, str)


async def test_authenticate_returns_none_for_wrong_password(service: AuthService):
    await service.register("test@example.com", "testpass123")
    assert await service.authenticate("test@example.com", "wrongpass") is None


async def test_authenticate_returns_none_for_unknown_email(service: AuthService):
    assert await service.authenticate("nobody@example.com", "anything") is None


async def test_get_user_from_token_round_trips(service: AuthService):
    registered = await service.register("test@example.com", "testpass123")
    token = await service.authenticate("test@example.com", "testpass123")

    user = await service.get_user_from_token(token)

    assert user is not None
    assert user.id == registered.id
    assert user.email == "test@example.com"


async def test_get_user_from_token_returns_none_for_garbage_token(service: AuthService):
    assert await service.get_user_from_token("not-a-real-token") is None

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.adapters.postgres.database import Base
# Import all ORM models so Alembic's autogenerate can see them.
from app.adapters.postgres.models.approval import ApprovalModel  # noqa: F401
from app.adapters.postgres.models.finding import FindingModel  # noqa: F401
from app.adapters.postgres.models.memory_entry import MemoryEntryModel  # noqa: F401
from app.adapters.postgres.models.pull_request import PullRequestModel  # noqa: F401
from app.adapters.postgres.models.task import TaskModel  # noqa: F401
from app.adapters.postgres.models.user import UserModel  # noqa: F401
from app.adapters.postgres.models.workflow import WorkflowModel  # noqa: F401
from app.config.settings import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable: AsyncEngine = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.events.sse_publisher import sse_event_publisher
from app.adapters.github.provider import GitHubProvider
from app.adapters.postgres.database import get_db
from app.adapters.postgres.repositories.approval_repository import PostgresApprovalRepository
from app.adapters.postgres.repositories.memory_repository import PostgresMemoryRepository
from app.adapters.postgres.repositories.pull_request_repository import PostgresPullRequestRepository
from app.adapters.postgres.repositories.result_repository import PostgresResultRepository
from app.adapters.postgres.repositories.task_repository import PostgresTaskRepository
from app.adapters.postgres.repositories.user_repository import PostgresUserRepository
from app.adapters.postgres.repositories.workflow_repository import PostgresWorkflowRepository
from app.adapters.qwen.model_client import QwenCloudModelClient
from app.adapters.storage.local_store import LocalFilesystemArtifactStore
from app.adapters.storage.oss_store import AlibabaOSSArtifactStore
from app.agents.bootstrap import build_agent_factory
from app.agents.factory import AgentFactory
from app.application.approvals.service import ApprovalService
from app.application.auth.service import AuthService
from app.application.memory.service import MemoryService
from app.application.orchestrator.orchestrator import Orchestrator
from app.application.pull_requests.service import PullRequestService
from app.application.workflows.service import WorkflowService
from app.config.settings import settings
from app.domain.models.user import User
from app.ports.artifact_store import ArtifactStore
from app.ports.event_publisher import EventPublisher
from app.ports.git_provider import GitProvider
from app.ports.repositories import (
    ApprovalRepository,
    MemoryRepository,
    PullRequestRepository,
    ResultRepository,
    TaskRepository,
    UserRepository,
    WorkflowRepository,
)

DbDep = Annotated[AsyncSession, Depends(get_db)]


def get_workflow_repository(db: DbDep) -> WorkflowRepository:
    return PostgresWorkflowRepository(db)


WorkflowRepositoryDep = Annotated[WorkflowRepository, Depends(get_workflow_repository)]


def get_workflow_service(repository: WorkflowRepositoryDep) -> WorkflowService:
    return WorkflowService(repository)


WorkflowServiceDep = Annotated[WorkflowService, Depends(get_workflow_service)]


def get_task_repository(db: DbDep) -> TaskRepository:
    return PostgresTaskRepository(db)


TaskRepositoryDep = Annotated[TaskRepository, Depends(get_task_repository)]


def get_event_publisher() -> EventPublisher:
    return sse_event_publisher


EventPublisherDep = Annotated[EventPublisher, Depends(get_event_publisher)]


def get_orchestrator(task_repository: TaskRepositoryDep, event_publisher: EventPublisherDep) -> Orchestrator:
    return Orchestrator(task_repository, event_publisher)


OrchestratorDep = Annotated[Orchestrator, Depends(get_orchestrator)]


def get_result_repository(db: DbDep) -> ResultRepository:
    return PostgresResultRepository(db)


ResultRepositoryDep = Annotated[ResultRepository, Depends(get_result_repository)]


def get_approval_repository(db: DbDep) -> ApprovalRepository:
    return PostgresApprovalRepository(db)


ApprovalRepositoryDep = Annotated[ApprovalRepository, Depends(get_approval_repository)]


def get_memory_repository(db: DbDep) -> MemoryRepository:
    return PostgresMemoryRepository(db)


MemoryRepositoryDep = Annotated[MemoryRepository, Depends(get_memory_repository)]


def get_memory_service(memory_repository: MemoryRepositoryDep) -> MemoryService:
    return MemoryService(memory_repository)


MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]


def get_approval_service(
    result_repository: ResultRepositoryDep,
    approval_repository: ApprovalRepositoryDep,
    workflow_repository: WorkflowRepositoryDep,
    memory_service: MemoryServiceDep,
) -> ApprovalService:
    return ApprovalService(result_repository, approval_repository, workflow_repository, memory_service)


ApprovalServiceDep = Annotated[ApprovalService, Depends(get_approval_service)]


def get_pull_request_repository(db: DbDep) -> PullRequestRepository:
    return PostgresPullRequestRepository(db)


PullRequestRepositoryDep = Annotated[PullRequestRepository, Depends(get_pull_request_repository)]


def get_git_provider() -> GitProvider:
    return GitHubProvider(token=settings.github_token)


GitProviderDep = Annotated[GitProvider, Depends(get_git_provider)]


def get_artifact_store() -> ArtifactStore:
    if settings.artifact_store_backend == "oss":
        return AlibabaOSSArtifactStore(
            access_key_id=settings.oss_access_key_id,
            access_key_secret=settings.oss_access_key_secret,
            endpoint=settings.oss_endpoint,
            bucket_name=settings.oss_bucket,
        )
    return LocalFilesystemArtifactStore(base_path=Path(settings.artifact_store_local_path))


ArtifactStoreDep = Annotated[ArtifactStore, Depends(get_artifact_store)]


def get_agent_factory() -> AgentFactory:
    model_client = QwenCloudModelClient(api_key=settings.qwen_api_key, base_url=settings.qwen_base_url)
    return build_agent_factory(model_client)


AgentFactoryDep = Annotated[AgentFactory, Depends(get_agent_factory)]


def get_pull_request_service(
    workflow_repository: WorkflowRepositoryDep,
    task_repository: TaskRepositoryDep,
    result_repository: ResultRepositoryDep,
    agent_factory: AgentFactoryDep,
    event_publisher: EventPublisherDep,
) -> PullRequestService:
    return PullRequestService(
        workflow_repository,
        task_repository,
        result_repository,
        agent_factory,
        event_publisher,
    )


PullRequestServiceDep = Annotated[PullRequestService, Depends(get_pull_request_service)]


def get_user_repository(db: DbDep) -> UserRepository:
    return PostgresUserRepository(db)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]


def get_auth_service(user_repository: UserRepositoryDep) -> AuthService:
    return AuthService(
        user_repository,
        secret_key=settings.secret_key,
        algorithm=settings.algorithm,
        access_token_expire_minutes=settings.access_token_expire_minutes,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


async def get_current_user(
    token: Annotated[str, Depends(_oauth2_scheme)], auth_service: AuthServiceDep
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "INVALID_CREDENTIALS", "message": "Could not validate credentials"},
        headers={"WWW-Authenticate": "Bearer"},
    )
    user = await auth_service.get_user_from_token(token)
    if user is None:
        raise credentials_exception
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_current_active_user(current_user: CurrentUserDep) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "INACTIVE_USER", "message": "Inactive user"},
        )
    return current_user


ActiveUserDep = Annotated[User, Depends(get_current_active_user)]

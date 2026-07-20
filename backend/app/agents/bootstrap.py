from pathlib import Path

from app.agents.factory import AgentFactory
from app.agents.managers.fix_manager import FixManagerAgent
from app.agents.managers.seo_manager import SEOManagerAgent
from app.agents.registry import AgentRegistry
from app.agents.reviewers.reviewer_agent import ReviewerAgent
from app.agents.workers.accessibility import AccessibilityAgent
from app.agents.workers.content_seo import ContentSEOAgent
from app.agents.workers.fix_worker import FixWorkerAgent
from app.agents.workers.metadata import MetadataAgent
from app.agents.workers.performance import PerformanceAgent
from app.agents.workers.technical_seo import TechnicalSEOAgent
from app.config.settings import settings
from app.ports.model_client import ModelClient
from app.tools.github_file_reader import read_repository_file

_AGENT_CLASSES = {
    "SEOManagerAgent": SEOManagerAgent,
    "TechnicalSEOAgent": TechnicalSEOAgent,
    "MetadataAgent": MetadataAgent,
    "ContentSEOAgent": ContentSEOAgent,
    "AccessibilityAgent": AccessibilityAgent,
    "PerformanceAgent": PerformanceAgent,
    "ReviewerAgent": ReviewerAgent,
    "FixManagerAgent": FixManagerAgent,
    "FixWorkerAgent": FixWorkerAgent,
}

_TOOLS_REGISTRY = {
    "github_file_reader": read_repository_file,
}

_APP_DIR = Path(__file__).resolve().parent.parent
_AGENTS_CONFIG_PATH = _APP_DIR / "config" / "agents.yaml"


def build_agent_factory(model_client: ModelClient) -> AgentFactory:
    """Single place that knows about every concrete agent class and tool -
    used both by the live analysis runner and available for reuse anywhere
    else a fully-wired AgentFactory is needed.

    Applies `settings.qwen_model_basic`/`qwen_model_reasoning` (from
    `.env`) over whatever agents.yaml's model_policies say - so which real
    Qwen model backs each tier is configurable per-deployment without
    editing the checked-in YAML.
    """
    registry = AgentRegistry.from_yaml(
        _AGENTS_CONFIG_PATH,
        basic_model=settings.qwen_model_basic,
        reasoning_model=settings.qwen_model_reasoning,
    )
    return AgentFactory(
        registry=registry,
        model_client=model_client,
        agent_classes=_AGENT_CLASSES,
        skills_dir=_APP_DIR,
        tools_registry=_TOOLS_REGISTRY,
    )

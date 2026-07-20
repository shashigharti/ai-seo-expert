from typing import Any

from pydantic import ValidationError

from app.config.logging import get_logger
from app.domain.models.agent_result import AgentResult

logger = get_logger(__name__)


def validate_agent_result(raw: dict[str, Any]) -> AgentResult | None:
    """docs/agent-architecture.md §10 Review Flow, step 1: Schema Validator.

    Task.output is untyped JSON once it round-trips through the database -
    re-validate it before treating it as trustworthy input to review/
    synthesis (Agents.md Security & Quality: "Validate inputs"), rather than
    assuming it's still shaped like an AgentResult. Returns None (logged,
    not raised) on failure - one malformed result shouldn't crash the whole
    review pipeline for a workflow with other valid results.
    """
    try:
        return AgentResult.model_validate(raw)
    except ValidationError:
        logger.exception("Task output failed AgentResult schema validation")
        return None

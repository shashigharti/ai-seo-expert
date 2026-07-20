import re
from pathlib import Path
from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.domain.policies.prompt_injection_guard import harden_system_prompt
from app.ports.model_client import ModelClient

_FRONTMATTER_PATTERN = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)

# Not a per-capability skill (no agents.yaml entry points at it) - a shared
# addendum applied to every agent's system prompt, same mechanism as
# harden_system_prompt's trust-boundary clause below. Read once per
# AgentFactory (not per create() call) since it's identical for every agent.
_TOKEN_EFFICIENCY_SKILL_PATH = Path("skills/token_efficient_prompting/SKILL.md")


def _strip_frontmatter(text: str) -> str:
    """Skill files use the same YAML-frontmatter-then-body shape as this
    project's own .agents/skills/<name>/SKILL.md (name + description, then
    instructions) - the frontmatter is metadata for humans/tooling, not
    instructions for the model, so it's stripped before use as a system
    prompt. A no-op on content with no frontmatter.
    """
    return _FRONTMATTER_PATTERN.sub("", text, count=1).strip()


class AgentClassNotFoundError(Exception):
    pass


class AgentFactory:
    """Task -> Agent Registry -> Model Policy -> Agent Factory -> PydanticAI
    Agent (docs/agent-architecture.md §6). Resolves a capability string to a
    constructed, ready-to-run agent instance.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        model_client: ModelClient,
        agent_classes: dict[str, type[BaseAgent]],
        skills_dir: Path,
        tools_registry: dict[str, Any] | None = None,
    ) -> None:
        self._registry = registry
        self._model_client = model_client
        self._agent_classes = agent_classes
        self._skills_dir = skills_dir
        self._tools_registry = tools_registry or {}
        self._token_efficiency_clause = _strip_frontmatter(
            (skills_dir / _TOKEN_EFFICIENCY_SKILL_PATH).read_text()
        )

    def create(self, capability: str) -> BaseAgent:
        registration = self._registry.get_registration(capability)

        agent_cls = self._agent_classes.get(registration.class_name)
        if agent_cls is None:
            raise AgentClassNotFoundError(
                f"No agent class registered for '{registration.class_name}' "
                f"(capability '{capability}')"
            )

        policy = self._registry.get_model_policy(registration.model_policy)
        skill_text = _strip_frontmatter((self._skills_dir / registration.skill).read_text())
        skill_text = harden_system_prompt(skill_text)
        skill_text = f"{skill_text}\n\n---\n{self._token_efficiency_clause}"
        tools = {name: self._tools_registry[name] for name in registration.tools if name in self._tools_registry}

        return agent_cls(
            name=registration.class_name,
            capability=registration.capability,
            model_client=self._model_client,
            tools=tools,
            skill=skill_text,
            model=policy.model,
            thinking=policy.thinking,
        )

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class AgentRegistration(BaseModel):
    """One entry under `agents:` in config/agents.yaml (docs/agent-architecture.md §5)."""

    class_name: str = Field(alias="class")
    capability: str
    model_policy: str
    skill: str
    tools: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class ModelPolicy(BaseModel):
    """One entry under `model_policies:` (docs/agent-architecture.md §6)."""

    model: str
    thinking: bool = False


class AgentRegistryConfig(BaseModel):
    agents: dict[str, AgentRegistration] = Field(default_factory=dict)
    model_policies: dict[str, ModelPolicy] = Field(default_factory=dict)


class UnknownCapabilityError(Exception):
    pass


class UnknownModelPolicyError(Exception):
    pass


class AgentRegistry:
    """Central agent + model-policy configuration. Workers are registered
    here, keyed by capability - docs/agent-architecture.md §5.
    """

    def __init__(self, config: AgentRegistryConfig) -> None:
        self._config = config

    @classmethod
    def from_yaml(
        cls,
        path: Path,
        *,
        basic_model: str | None = None,
        reasoning_model: str | None = None,
    ) -> "AgentRegistry":
        """`basic_model`/`reasoning_model` override every policy's `model`
        field by its `thinking` flag (not by policy name - "economical" vs
        "balanced" vs "advanced" is a YAML-authoring convenience, `thinking`
        is the real distinction) - how `settings.qwen_model_basic`/
        `qwen_model_reasoning` reach the registry without editing
        agents.yaml per deployment. Omit either (or both) to use exactly
        what the YAML says, unchanged - the default, so loading the file
        standalone (e.g. in a test) isn't silently affected by whatever a
        real deployment's `.env` happens to have.
        """
        data = yaml.safe_load(path.read_text()) or {}
        config = AgentRegistryConfig.model_validate(data)
        if basic_model is not None or reasoning_model is not None:
            for name, policy in config.model_policies.items():
                override = reasoning_model if policy.thinking else basic_model
                if override is not None:
                    config.model_policies[name] = policy.model_copy(update={"model": override})
        return cls(config)

    def get_registration(self, capability: str) -> AgentRegistration:
        try:
            return self._config.agents[capability]
        except KeyError as exc:
            raise UnknownCapabilityError(f"No agent registered for capability '{capability}'") from exc

    def get_model_policy(self, policy_name: str) -> ModelPolicy:
        try:
            return self._config.model_policies[policy_name]
        except KeyError as exc:
            raise UnknownModelPolicyError(f"Unknown model policy '{policy_name}'") from exc

    def capabilities(self) -> list[str]:
        return list(self._config.agents.keys())

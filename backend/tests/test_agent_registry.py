import pytest

from app.agents.registry import (
    AgentRegistry,
    AgentRegistryConfig,
    UnknownCapabilityError,
    UnknownModelPolicyError,
)


@pytest.fixture
def registry() -> AgentRegistry:
    config = AgentRegistryConfig.model_validate(
        {
            "model_policies": {
                "economical": {"model": "qwen-plus", "thinking": False},
                "advanced": {"model": "qwen-max", "thinking": True},
            },
            "agents": {
                "technical_seo": {
                    "class": "TechnicalSEOAgent",
                    "capability": "technical_seo",
                    "model_policy": "economical",
                    "skill": "skills/technical_seo/SKILL.md",
                    "tools": ["robots_parser", "sitemap_parser"],
                }
            },
        }
    )
    return AgentRegistry(config)


def test_get_registration_returns_config_for_known_capability(registry: AgentRegistry):
    registration = registry.get_registration("technical_seo")
    assert registration.class_name == "TechnicalSEOAgent"
    assert registration.tools == ["robots_parser", "sitemap_parser"]


def test_get_registration_raises_for_unknown_capability(registry: AgentRegistry):
    with pytest.raises(UnknownCapabilityError):
        registry.get_registration("nonexistent")


def test_get_model_policy_returns_policy(registry: AgentRegistry):
    policy = registry.get_model_policy("advanced")
    assert policy.model == "qwen-max"
    assert policy.thinking is True


def test_get_model_policy_raises_for_unknown_policy(registry: AgentRegistry):
    with pytest.raises(UnknownModelPolicyError):
        registry.get_model_policy("nonexistent")


def test_capabilities_lists_registered_agents(registry: AgentRegistry):
    assert registry.capabilities() == ["technical_seo"]


def test_from_yaml_loads_the_real_config_file():
    from pathlib import Path

    config_path = Path(__file__).parent.parent / "app" / "config" / "agents.yaml"
    loaded = AgentRegistry.from_yaml(config_path)

    assert loaded.get_model_policy("economical").model == "qwen-plus"
    assert loaded.get_model_policy("balanced").thinking is True
    assert loaded.get_model_policy("advanced").model == "qwen-max"


def test_from_yaml_without_overrides_uses_exactly_what_the_file_says(tmp_path):
    """No basic_model/reasoning_model passed - e.g. a test loading the file
    standalone - must not be affected by whatever a real deployment's .env
    happens to have."""
    config_path = tmp_path / "agents.yaml"
    config_path.write_text(
        "model_policies:\n"
        "  economical:\n"
        "    model: qwen-plus\n"
        "    thinking: false\n"
        "  advanced:\n"
        "    model: qwen-max\n"
        "    thinking: true\n"
        "agents: {}\n"
    )

    loaded = AgentRegistry.from_yaml(config_path)

    assert loaded.get_model_policy("economical").model == "qwen-plus"
    assert loaded.get_model_policy("advanced").model == "qwen-max"


def test_from_yaml_overrides_model_by_thinking_flag_not_by_policy_name(tmp_path):
    """basic_model/reasoning_model (from settings.qwen_model_basic/
    qwen_model_reasoning in real use) replace every policy's model by
    `thinking`, regardless of the YAML's own model or the policy's name -
    proves the override doesn't just apply to one hardcoded policy name."""
    config_path = tmp_path / "agents.yaml"
    config_path.write_text(
        "model_policies:\n"
        "  economical:\n"
        "    model: some-old-model\n"
        "    thinking: false\n"
        "  balanced:\n"
        "    model: some-old-model\n"
        "    thinking: true\n"
        "  advanced:\n"
        "    model: yet-another-model\n"
        "    thinking: true\n"
        "agents: {}\n"
    )

    loaded = AgentRegistry.from_yaml(config_path, basic_model="qwen-plus", reasoning_model="qwen-max")

    assert loaded.get_model_policy("economical").model == "qwen-plus"
    assert loaded.get_model_policy("balanced").model == "qwen-max"
    assert loaded.get_model_policy("advanced").model == "qwen-max"


def test_from_yaml_partial_override_leaves_the_other_tier_untouched(tmp_path):
    config_path = tmp_path / "agents.yaml"
    config_path.write_text(
        "model_policies:\n"
        "  economical:\n"
        "    model: qwen-plus\n"
        "    thinking: false\n"
        "  advanced:\n"
        "    model: qwen-max\n"
        "    thinking: true\n"
        "agents: {}\n"
    )

    loaded = AgentRegistry.from_yaml(config_path, reasoning_model="qwen-max-2025-01-01")

    assert loaded.get_model_policy("economical").model == "qwen-plus"  # untouched - no basic_model given
    assert loaded.get_model_policy("advanced").model == "qwen-max-2025-01-01"

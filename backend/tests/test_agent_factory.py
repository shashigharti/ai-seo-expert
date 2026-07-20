from pathlib import Path

import pytest
from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.agents.factory import AgentClassNotFoundError, AgentFactory
from app.agents.registry import AgentRegistry, AgentRegistryConfig
from app.domain.models.agent_result import AgentResult
from app.domain.models.task import Task


class _StubOutput(BaseModel):
    ok: bool = True


class _StubWorkerAgent(BaseAgent):
    def __init__(self, name, capability, model_client, tools, skill, model, thinking=False):
        super().__init__(
            name=name,
            capability=capability,
            model_client=model_client,
            tools=tools,
            skill=skill,
            output_model=_StubOutput,
            model=model,
            thinking=thinking,
        )

    async def execute(self, task: Task) -> AgentResult:
        raise NotImplementedError("not exercised by these tests")


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    skill = tmp_path / "skills" / "technical_seo"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("You are a technical SEO auditor.")
    # Not a per-capability skill - AgentFactory reads this same shared file
    # for every agent it constructs (see factory.py's _TOKEN_EFFICIENCY_SKILL_PATH).
    token_efficiency_skill = tmp_path / "skills" / "token_efficient_prompting"
    token_efficiency_skill.mkdir(parents=True)
    (token_efficiency_skill / "SKILL.md").write_text(
        "---\nname: token_efficient_prompting\ndescription: test\n---\nBe token-efficient."
    )
    return tmp_path


@pytest.fixture
def registry() -> AgentRegistry:
    config = AgentRegistryConfig.model_validate(
        {
            "model_policies": {"economical": {"model": "qwen-plus", "thinking": False}},
            "agents": {
                "technical_seo": {
                    "class": "StubWorkerAgent",
                    "capability": "technical_seo",
                    "model_policy": "economical",
                    "skill": "skills/technical_seo/SKILL.md",
                    "tools": ["robots_parser"],
                }
            },
        }
    )
    return AgentRegistry(config)


def test_create_builds_a_configured_agent_instance(registry: AgentRegistry, skills_dir: Path):
    factory = AgentFactory(
        registry=registry,
        model_client=object(),  # not called in this test
        agent_classes={"StubWorkerAgent": _StubWorkerAgent},
        skills_dir=skills_dir,
        tools_registry={"robots_parser": "robots-parser-tool"},
    )

    agent = factory.create("technical_seo")

    assert isinstance(agent, _StubWorkerAgent)
    assert agent.name == "StubWorkerAgent"
    assert agent.capability == "technical_seo"
    assert agent.model == "qwen-plus"
    assert agent.thinking is False
    assert agent.skill.startswith("You are a technical SEO auditor.")
    assert "Trust boundary" in agent.skill
    assert agent.tools == {"robots_parser": "robots-parser-tool"}
    assert agent.output_model is _StubOutput


def test_create_appends_the_shared_token_efficiency_clause_to_every_agent(
    registry: AgentRegistry, skills_dir: Path
):
    """token_efficient_prompting isn't a per-capability skill (no agents.yaml
    entry points at it) - AgentFactory applies it to every agent
    automatically, the same mechanism harden_system_prompt already uses for
    the trust-boundary clause."""
    factory = AgentFactory(
        registry=registry,
        model_client=object(),
        agent_classes={"StubWorkerAgent": _StubWorkerAgent},
        skills_dir=skills_dir,
    )

    agent = factory.create("technical_seo")

    assert "Be token-efficient." in agent.skill
    # Frontmatter is metadata for humans/tooling, stripped before use as a
    # system prompt - same rule this file already applies to every SKILL.md.
    assert "description: test" not in agent.skill


def test_create_raises_for_unregistered_agent_class(registry: AgentRegistry, skills_dir: Path):
    factory = AgentFactory(
        registry=registry,
        model_client=object(),
        agent_classes={},  # StubWorkerAgent intentionally not registered
        skills_dir=skills_dir,
    )

    with pytest.raises(AgentClassNotFoundError):
        factory.create("technical_seo")

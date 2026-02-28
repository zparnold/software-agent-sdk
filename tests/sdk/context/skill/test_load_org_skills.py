"""Tests for load_org_skills functionality with git-based caching and auth."""

from unittest.mock import patch

import pytest

from openhands.sdk.context.agent_context import AgentContext
from openhands.sdk.context.skills import (
    KeywordTrigger,
    Skill,
    load_org_skills,
)


@pytest.fixture
def mock_org_repo_dir(tmp_path):
    """Create a mock org skills repository with skill files."""
    repo_dir = tmp_path / "mock_org_repo"
    repo_dir.mkdir()

    # Create skills directory
    skills_dir = repo_dir / "skills"
    skills_dir.mkdir()

    # Create legacy .md skill files
    deploy_skill = skills_dir / "deploy.md"
    deploy_skill.write_text(
        "---\n"
        "name: deploy\n"
        "triggers:\n"
        "  - deploy\n"
        "  - deployment\n"
        "---\n"
        "Org-specific deployment procedures."
    )

    compliance_skill = skills_dir / "compliance.md"
    compliance_skill.write_text(
        "---\nname: compliance\n---\nOrg compliance guidelines."
    )

    # Create AgentSkills-format skill
    sre_dir = skills_dir / "sre-runbook"
    sre_dir.mkdir()
    sre_skill_md = sre_dir / "SKILL.md"
    sre_skill_md.write_text(
        "---\n"
        "name: sre-runbook\n"
        "description: SRE runbook for incident response.\n"
        "---\n"
        "# SRE Runbook\n\nIncident response procedures.\n"
    )

    # Create .git directory to simulate a git repo
    (repo_dir / ".git").mkdir()

    return repo_dir


def test_load_org_skills_success(mock_org_repo_dir, tmp_path):
    """Test successfully loading skills from an org repository."""

    def mock_update_repo(repo_url, branch, cache_dir, auth_header=None):
        return mock_org_repo_dir

    with (
        patch(
            "openhands.sdk.context.skills.skill.update_org_skills_repository",
            side_effect=mock_update_repo,
        ),
        patch(
            "openhands.sdk.context.skills.skill.get_skills_cache_dir",
            return_value=tmp_path,
        ),
    ):
        skills = load_org_skills(
            repo_url="https://dev.azure.com/org/project/_git/skills"
        )
        assert len(skills) == 3
        skill_names = {s.name for s in skills}
        assert skill_names == {"deploy", "compliance", "sre-runbook"}

        # Check deploy skill details
        deploy_skill = next(s for s in skills if s.name == "deploy")
        assert isinstance(deploy_skill.trigger, KeywordTrigger)
        assert "deploy" in deploy_skill.trigger.keywords

        # Check compliance skill (no trigger - always active)
        compliance_skill = next(s for s in skills if s.name == "compliance")
        assert compliance_skill.trigger is None

        # Check AgentSkills-format skill
        sre_skill = next(s for s in skills if s.name == "sre-runbook")
        assert sre_skill.is_agentskills_format


def test_load_org_skills_auth_header_passthrough(mock_org_repo_dir, tmp_path):
    """Test that auth_header is passed through to update_org_skills_repository."""
    captured_args = {}

    def mock_update_repo(repo_url, branch, cache_dir, auth_header=None):
        captured_args["repo_url"] = repo_url
        captured_args["branch"] = branch
        captured_args["auth_header"] = auth_header
        return mock_org_repo_dir

    with (
        patch(
            "openhands.sdk.context.skills.skill.update_org_skills_repository",
            side_effect=mock_update_repo,
        ),
        patch(
            "openhands.sdk.context.skills.skill.get_skills_cache_dir",
            return_value=tmp_path,
        ),
    ):
        load_org_skills(
            repo_url="https://dev.azure.com/org/project/_git/skills",
            branch="develop",
            auth_header="Authorization: Bearer my-secret-token",
        )
        assert captured_args["repo_url"] == (
            "https://dev.azure.com/org/project/_git/skills"
        )
        assert captured_args["branch"] == "develop"
        assert captured_args["auth_header"] == ("Authorization: Bearer my-secret-token")


def test_load_org_skills_repo_update_fails(tmp_path):
    """Test handling when repository update fails."""

    def mock_update_repo(repo_url, branch, cache_dir, auth_header=None):
        return None

    with (
        patch(
            "openhands.sdk.context.skills.skill.update_org_skills_repository",
            side_effect=mock_update_repo,
        ),
        patch(
            "openhands.sdk.context.skills.skill.get_skills_cache_dir",
            return_value=tmp_path,
        ),
    ):
        skills = load_org_skills(
            repo_url="https://dev.azure.com/org/project/_git/skills"
        )
        assert skills == []


def test_load_org_skills_no_skills_directory(tmp_path):
    """Test handling when skills directory doesn't exist in repo."""
    repo_dir = tmp_path / "mock_org_repo"
    repo_dir.mkdir()
    # No skills directory created

    def mock_update_repo(repo_url, branch, cache_dir, auth_header=None):
        return repo_dir

    with (
        patch(
            "openhands.sdk.context.skills.skill.update_org_skills_repository",
            side_effect=mock_update_repo,
        ),
        patch(
            "openhands.sdk.context.skills.skill.get_skills_cache_dir",
            return_value=tmp_path,
        ),
    ):
        skills = load_org_skills(
            repo_url="https://dev.azure.com/org/project/_git/skills"
        )
        assert skills == []


def test_load_org_skills_custom_branch(mock_org_repo_dir, tmp_path):
    """Test loading from a specific branch."""
    captured_branch = {}

    def mock_update_repo(repo_url, branch, cache_dir, auth_header=None):
        captured_branch["branch"] = branch
        return mock_org_repo_dir

    with (
        patch(
            "openhands.sdk.context.skills.skill.update_org_skills_repository",
            side_effect=mock_update_repo,
        ),
        patch(
            "openhands.sdk.context.skills.skill.get_skills_cache_dir",
            return_value=tmp_path,
        ),
    ):
        skills = load_org_skills(
            repo_url="https://dev.azure.com/org/project/_git/skills",
            branch="release/v2",
        )
        assert len(skills) == 3
        assert captured_branch["branch"] == "release/v2"


def test_load_org_skills_invalid_skill_skipped(tmp_path):
    """Test that invalid skill files are skipped gracefully."""
    repo_dir = tmp_path / "mock_org_repo"
    repo_dir.mkdir()
    skills_dir = repo_dir / "skills"
    skills_dir.mkdir()

    # Valid skill
    valid_skill = skills_dir / "valid.md"
    valid_skill.write_text("---\nname: valid\n---\nValid skill content.")

    # Invalid skill (triggers must be a list)
    invalid_skill = skills_dir / "invalid.md"
    invalid_skill.write_text(
        "---\nname: invalid\ntriggers: not_a_list\n---\nInvalid skill."
    )

    def mock_update_repo(repo_url, branch, cache_dir, auth_header=None):
        return repo_dir

    with (
        patch(
            "openhands.sdk.context.skills.skill.update_org_skills_repository",
            side_effect=mock_update_repo,
        ),
        patch(
            "openhands.sdk.context.skills.skill.get_skills_cache_dir",
            return_value=tmp_path,
        ),
    ):
        skills = load_org_skills(
            repo_url="https://dev.azure.com/org/project/_git/skills"
        )
        assert len(skills) == 1
        assert skills[0].name == "valid"


def test_agent_context_loads_org_skills(mock_org_repo_dir, tmp_path):
    """Test that AgentContext loads org skills when enabled."""

    def mock_update_repo(repo_url, branch, cache_dir, auth_header=None):
        return mock_org_repo_dir

    with (
        patch(
            "openhands.sdk.context.skills.skill.update_org_skills_repository",
            side_effect=mock_update_repo,
        ),
        patch(
            "openhands.sdk.context.skills.skill.get_skills_cache_dir",
            return_value=tmp_path,
        ),
    ):
        context = AgentContext(
            enable_org_skills=True,
            org_skills_repo_url="https://dev.azure.com/org/project/_git/skills",
            org_skills_auth_header="Authorization: Bearer token",
        )
        skill_names = {s.name for s in context.skills}
        assert "deploy" in skill_names
        assert "compliance" in skill_names
        assert "sre-runbook" in skill_names


def test_agent_context_org_skills_disabled_by_default():
    """Test that org skills loading is disabled by default."""
    context = AgentContext()
    assert context.enable_org_skills is False
    assert context.skills == []


def test_agent_context_org_skills_no_url_warns():
    """Test that enabling org skills without URL logs a warning."""
    context = AgentContext(enable_org_skills=True)
    # Should not crash, just warn and produce no skills
    assert context.skills == []


def test_agent_context_explicit_skills_override_org(mock_org_repo_dir, tmp_path):
    """Test that explicit skills take precedence over org skills."""

    def mock_update_repo(repo_url, branch, cache_dir, auth_header=None):
        return mock_org_repo_dir

    # Create explicit skill with same name as an org skill
    explicit_deploy = Skill(
        name="deploy",
        content="Explicit deploy skill content.",
        trigger=None,
    )

    with (
        patch(
            "openhands.sdk.context.skills.skill.update_org_skills_repository",
            side_effect=mock_update_repo,
        ),
        patch(
            "openhands.sdk.context.skills.skill.get_skills_cache_dir",
            return_value=tmp_path,
        ),
    ):
        context = AgentContext(
            skills=[explicit_deploy],
            enable_org_skills=True,
            org_skills_repo_url="https://dev.azure.com/org/project/_git/skills",
        )
        # 1 explicit deploy + 2 other org skills (compliance, sre-runbook)
        assert len(context.skills) == 3
        deploy_skill = next(s for s in context.skills if s.name == "deploy")
        assert deploy_skill.content == "Explicit deploy skill content."


def test_agent_context_org_overrides_user_and_public(mock_org_repo_dir, tmp_path):
    """Test precedence: explicit > org > user > public."""

    def mock_org_update(repo_url, branch, cache_dir, auth_header=None):
        return mock_org_repo_dir

    # Create a mock public repo with a skill that has the same name as an org skill
    public_repo_dir = tmp_path / "public_repo"
    public_repo_dir.mkdir()
    public_skills_dir = public_repo_dir / "skills"
    public_skills_dir.mkdir()
    (public_skills_dir / "deploy.md").write_text(
        "---\nname: deploy\n---\nPublic deploy skill."
    )
    (public_skills_dir / "public-only.md").write_text(
        "---\nname: public-only\n---\nPublic-only skill."
    )
    (public_repo_dir / ".git").mkdir()

    def mock_public_update(repo_url, branch, cache_dir):
        return public_repo_dir

    with (
        patch(
            "openhands.sdk.context.skills.skill.update_org_skills_repository",
            side_effect=mock_org_update,
        ),
        patch(
            "openhands.sdk.context.skills.skill.update_skills_repository",
            side_effect=mock_public_update,
        ),
        patch(
            "openhands.sdk.context.skills.skill.get_skills_cache_dir",
            return_value=tmp_path,
        ),
    ):
        context = AgentContext(
            enable_org_skills=True,
            org_skills_repo_url="https://dev.azure.com/org/project/_git/skills",
            load_public_skills=True,
        )
        skill_names = {s.name for s in context.skills}
        # Org skills: deploy, compliance, sre-runbook
        # Public: deploy (duplicate, skipped), public-only (new)
        assert "deploy" in skill_names
        assert "compliance" in skill_names
        assert "sre-runbook" in skill_names
        assert "public-only" in skill_names

        # Org version should win over public
        deploy_skill = next(s for s in context.skills if s.name == "deploy")
        assert deploy_skill.content == "Org-specific deployment procedures."

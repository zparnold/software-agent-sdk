"""Tests for extra_git_config support in GitHelper and try_cached_clone_or_update."""

from unittest.mock import MagicMock, patch

import pytest

from openhands.sdk.git.cached_repo import GitHelper, try_cached_clone_or_update


@pytest.fixture
def mock_subprocess_success():
    """Mock subprocess.run to return success."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""
    return mock_result


class TestGitHelperExtraConfig:
    """Tests for GitHelper.clone() and fetch() with extra_git_config."""

    def test_clone_with_extra_git_config(self, tmp_path, mock_subprocess_success):
        """Test that clone prepends -c flags before the clone subcommand."""
        git = GitHelper()
        dest = tmp_path / "repo"

        with patch(
            "openhands.sdk.git.utils.subprocess.run",
            return_value=mock_subprocess_success,
        ) as mock_run:
            git.clone(
                url="https://example.com/repo.git",
                dest=dest,
                extra_git_config=["http.extraHeader=Authorization: Bearer token123"],
            )

            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]

            # Verify structure: git -c <config> clone ...
            assert cmd[0] == "git"
            assert cmd[1] == "-c"
            assert cmd[2] == "http.extraHeader=Authorization: Bearer token123"
            assert cmd[3] == "clone"

    def test_clone_with_multiple_extra_configs(self, tmp_path, mock_subprocess_success):
        """Test clone with multiple config entries."""
        git = GitHelper()
        dest = tmp_path / "repo"

        with patch(
            "openhands.sdk.git.utils.subprocess.run",
            return_value=mock_subprocess_success,
        ) as mock_run:
            git.clone(
                url="https://example.com/repo.git",
                dest=dest,
                extra_git_config=[
                    "http.extraHeader=Authorization: Bearer token123",
                    "http.sslVerify=false",
                ],
            )

            cmd = mock_run.call_args[0][0]
            assert cmd[0] == "git"
            assert cmd[1] == "-c"
            assert cmd[2] == "http.extraHeader=Authorization: Bearer token123"
            assert cmd[3] == "-c"
            assert cmd[4] == "http.sslVerify=false"
            assert cmd[5] == "clone"

    def test_clone_without_extra_git_config(self, tmp_path, mock_subprocess_success):
        """Test that clone works normally when extra_git_config is None."""
        git = GitHelper()
        dest = tmp_path / "repo"

        with patch(
            "openhands.sdk.git.utils.subprocess.run",
            return_value=mock_subprocess_success,
        ) as mock_run:
            git.clone(
                url="https://example.com/repo.git",
                dest=dest,
            )

            cmd = mock_run.call_args[0][0]
            # No -c flags should be present
            assert cmd[0] == "git"
            assert cmd[1] == "clone"
            assert "-c" not in cmd

    def test_fetch_with_extra_git_config(self, tmp_path, mock_subprocess_success):
        """Test that fetch prepends -c flags before the fetch subcommand."""
        git = GitHelper()

        with patch(
            "openhands.sdk.git.utils.subprocess.run",
            return_value=mock_subprocess_success,
        ) as mock_run:
            git.fetch(
                repo_path=tmp_path,
                extra_git_config=["http.extraHeader=Authorization: Bearer token123"],
            )

            cmd = mock_run.call_args[0][0]
            assert cmd[0] == "git"
            assert cmd[1] == "-c"
            assert cmd[2] == "http.extraHeader=Authorization: Bearer token123"
            assert cmd[3] == "fetch"
            assert cmd[4] == "origin"

    def test_fetch_without_extra_git_config(self, tmp_path, mock_subprocess_success):
        """Test that fetch works normally when extra_git_config is None."""
        git = GitHelper()

        with patch(
            "openhands.sdk.git.utils.subprocess.run",
            return_value=mock_subprocess_success,
        ) as mock_run:
            git.fetch(repo_path=tmp_path)

            cmd = mock_run.call_args[0][0]
            assert cmd[0] == "git"
            assert cmd[1] == "fetch"
            assert "-c" not in cmd


class TestTryCachedCloneOrUpdateAuth:
    """Tests for try_cached_clone_or_update with extra_git_config."""

    def test_clone_threads_extra_config(self, tmp_path, mock_subprocess_success):
        """Test that extra_git_config is threaded through to clone."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        repo_path = cache_dir / "test-repo"

        with patch(
            "openhands.sdk.git.utils.subprocess.run",
            return_value=mock_subprocess_success,
        ) as mock_run:
            result = try_cached_clone_or_update(
                url="https://example.com/repo.git",
                repo_path=repo_path,
                ref="main",
                extra_git_config=["http.extraHeader=Authorization: Bearer token123"],
            )

            assert result is not None
            # Clone should have been called with -c flag
            cmd = mock_run.call_args[0][0]
            assert "-c" in cmd
            assert "http.extraHeader=Authorization: Bearer token123" in cmd

    def test_fetch_threads_extra_config(self, tmp_path):
        """Test that extra_git_config is threaded through to fetch on update."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        repo_path = cache_dir / "test-repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "main"

        with patch(
            "openhands.sdk.git.utils.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            result = try_cached_clone_or_update(
                url="https://example.com/repo.git",
                repo_path=repo_path,
                ref="main",
                update=True,
                extra_git_config=["http.extraHeader=Authorization: Bearer token123"],
            )

            assert result == repo_path
            # First call should be fetch with -c flag
            fetch_cmd = mock_run.call_args_list[0][0][0]
            assert fetch_cmd[0] == "git"
            assert "-c" in fetch_cmd
            assert "http.extraHeader=Authorization: Bearer token123" in fetch_cmd
            assert "fetch" in fetch_cmd

    def test_no_extra_config_backwards_compatible(
        self, tmp_path, mock_subprocess_success
    ):
        """Test that omitting extra_git_config preserves old behavior."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        repo_path = cache_dir / "test-repo"

        with patch(
            "openhands.sdk.git.utils.subprocess.run",
            return_value=mock_subprocess_success,
        ) as mock_run:
            result = try_cached_clone_or_update(
                url="https://example.com/repo.git",
                repo_path=repo_path,
                ref="main",
            )

            assert result is not None
            cmd = mock_run.call_args[0][0]
            assert "-c" not in cmd

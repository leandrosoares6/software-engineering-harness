from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    return tmp_path


@pytest.fixture
def committed_repo(git_repo: Path) -> Path:
    readme = git_repo / "README.md"
    readme.write_text("fixture\n", encoding="utf-8")
    git(git_repo, "add", "README.md")
    git(git_repo, "commit", "-qm", "fixture")
    return git_repo

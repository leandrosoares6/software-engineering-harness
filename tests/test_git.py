from __future__ import annotations

import pytest

from conftest import git
from seh.errors import GitError
from seh.git import head, repository_root, state_fingerprint, tracked_files


def test_discovers_canonical_root_from_subdirectory(committed_repo):
    nested = committed_repo / "src" / "nested"
    nested.mkdir(parents=True)

    assert repository_root(nested) == committed_repo.resolve()
    assert tracked_files(nested) == [committed_repo / "README.md"]


def test_supports_unborn_head_and_fingerprint_changes_only_for_tracked_files(git_repo):
    tracked = git_repo / "tracked.txt"
    tracked.write_text("one\n", encoding="utf-8")
    git(git_repo, "add", "tracked.txt")

    assert head(git_repo) is None
    initial = state_fingerprint(git_repo)
    (git_repo / "untracked.txt").write_text("ignored\n", encoding="utf-8")
    assert state_fingerprint(git_repo) == initial
    tracked.write_text("two\n", encoding="utf-8")
    assert state_fingerprint(git_repo) != initial


def test_rejects_non_repository(tmp_path):
    with pytest.raises(GitError):
        repository_root(tmp_path)


def test_fingerprint_tracks_staged_changes_and_deletions(committed_repo):
    initial = state_fingerprint(committed_repo)
    readme = committed_repo / "README.md"
    readme.write_text("staged\n", encoding="utf-8")
    git(committed_repo, "add", "README.md")
    staged = state_fingerprint(committed_repo)
    readme.unlink()

    assert staged != initial
    assert state_fingerprint(committed_repo) != staged

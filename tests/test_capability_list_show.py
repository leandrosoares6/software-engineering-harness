"""Tests for `seh capability list` and `seh capability show`.

Both close usability gaps that made the product hard to adopt from outside:
without `list` a developer cannot discover the id `run` requires, and without
`show` the `--allow-verification` trust decision demands a review the tool did
not support.

`show` is security-relevant, so the tests pin the two properties that matter:
every declared command is printed in full, and nothing is executed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seh.capability_catalog import CATALOG_DIRECTORY, install_candidate
from seh.capability_list import installed_capabilities
from seh.capability_show import render, resolve
from seh.errors import CapabilityError
from test_capability import candidate_package


@pytest.fixture
def repo_with_capability(git_repo: Path, tmp_path: Path) -> Path:
    install_candidate(
        candidate_package(tmp_path / "cand"), git_repo, allow_verification=True
    )
    return git_repo


# --- list ------------------------------------------------------------------


def test_list_is_empty_before_anything_is_installed(git_repo):
    assert installed_capabilities(git_repo) == []


def test_list_reports_id_version_and_parameters(repo_with_capability):
    entries = installed_capabilities(repo_with_capability)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.version == 1
    assert entry.parameters == ("name",)
    assert entry.problem is None


def test_list_reports_a_broken_entry_instead_of_hiding_it(repo_with_capability):
    """A catalogue that silently omits a broken capability is worse than useless."""
    broken = repo_with_capability / CATALOG_DIRECTORY / "app.broken"
    broken.mkdir()
    (broken / "capability.yaml").write_text("not: a valid manifest\n", encoding="utf-8")

    entries = installed_capabilities(repo_with_capability)
    problems = {entry.capability_id: entry.problem for entry in entries}

    assert "app.broken" in problems
    assert problems["app.broken"] is not None
    assert len(entries) == 2


def test_list_rejects_a_symlinked_catalogue(git_repo, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (git_repo / CATALOG_DIRECTORY).symlink_to(elsewhere, target_is_directory=True)

    with pytest.raises(CapabilityError, match="must not be a symlink"):
        installed_capabilities(git_repo)


# --- show ------------------------------------------------------------------


def test_show_resolves_an_installed_capability_by_id(repo_with_capability):
    entries = installed_capabilities(repo_with_capability)
    installed_id = entries[0].capability_id

    candidate = resolve(repo_with_capability, path=None, capability_id=installed_id)

    assert candidate.capability_id == installed_id


def test_show_refuses_an_uninstalled_id(git_repo):
    with pytest.raises(CapabilityError, match="is not installed"):
        resolve(git_repo, path=None, capability_id="app.missing")


def test_show_requires_exactly_one_selector(git_repo):
    with pytest.raises(CapabilityError, match="either a candidate path or --id"):
        resolve(git_repo, path=None, capability_id=None)
    with pytest.raises(CapabilityError, match="either a candidate path or --id"):
        resolve(git_repo, path="./x", capability_id="app.x")


def test_show_prints_every_declared_command_in_full(tmp_path):
    """The whole point: a reviewer must see exactly what would execute."""
    candidate = resolve(
        tmp_path, path=str(candidate_package(tmp_path / "cand")), capability_id=None
    )
    output = "\n".join(render(candidate))

    assert candidate.verification
    for invocation in candidate.verification:
        config = invocation.config
        argv = " ".join([config["executable"], *config["args"]])
        assert f"$ {argv}" in output
        assert f"timeout {config['timeout_seconds']}s" in output
    assert "WILL execute with your privileges" in output
    assert "not an OS sandbox" in output


def test_show_includes_template_contents(tmp_path):
    candidate = resolve(
        tmp_path, path=str(candidate_package(tmp_path / "cand")), capability_id=None
    )
    output = "\n".join(render(candidate))

    assert candidate.steps
    for invocation in candidate.steps:
        relative = invocation.config["template"]
        assert relative in output
        for line in (candidate.root / relative).read_text().splitlines():
            assert f"    | {line}" in output


def test_show_executes_nothing(tmp_path, monkeypatch):
    """Rendering a candidate must never run a declared command."""
    candidate = resolve(
        tmp_path, path=str(candidate_package(tmp_path / "cand")), capability_id=None
    )

    def forbidden(*args, **kwargs):  # pragma: no cover - must not be reached
        raise AssertionError("show executed a subprocess")

    monkeypatch.setattr("subprocess.run", forbidden)

    assert render(candidate)

"""Tests for `seh capability capture`.

The acceptance test is the last one: a fresh external Python repository, an
accepted change, `capture`, and then the four gates passing without a single
byte of generated patch or fixture being edited by hand. That is the point of
the command — the mechanical half of authoring stops being the developer's
problem, while the judgement half (templates, parameters, steps) stays with the
agent, where the model says it belongs.
"""

from __future__ import annotations

import difflib
import subprocess
from pathlib import Path

import pytest

from seh.capability import validate_candidate
from test_capability import record_scope_digests
from seh.capability_capture import capture
from seh.errors import CapabilityError, CapabilityRefusal

BASE_REGISTRY = """from __future__ import annotations


def handler_seed() -> str:
    return "seed"


def build_registry() -> dict:
    registry: dict = {}
    return registry
"""

ACCEPTED_REGISTRY = """from __future__ import annotations


def handler_seed() -> str:
    return "seed"


def handler_ping() -> str:
    return "ping"


def build_registry() -> dict:
    registry: dict = {}
    registry["ping"] = handler_ping
    return registry
"""

MANIFEST = """schema: seh.capability.phase0/v0.1
id: app.add-registry-handler
version: 1

parameters:
  name:
    type: python_identifier

preconditions:
  - uses: text.absent
    with:
      file: app/registry.py
      value: "def handler_{{ name }}("

steps:
  - uses: splice.after
    with:
      file: app/registry.py
      locator: python.symbol
      selector: last_with_prefix
      prefix: handler_
      template: templates/handler.py.tmpl
  - uses: splice.before
    with:
      file: app/registry.py
      locator: python.statement
      function: build_registry
      statement: return
      template: templates/registration.py.tmpl

verification:
  - uses: verify.command
    with:
      executable: python
      args: ["-m", "compileall", "-q", "app/registry.py"]
      timeout_seconds: 30
      expected_exit: 0
"""


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


@pytest.fixture
def external_repo(tmp_path: Path) -> Path:
    """A Python project that knows nothing about SEH."""
    root = tmp_path / "app-repo"
    (root / "app").mkdir(parents=True)
    (root / "app" / "__init__.py").touch()
    (root / "app" / "registry.py").write_text(BASE_REGISTRY, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    git(root, "config", "user.email", "dev@example.test")
    git(root, "config", "user.name", "Dev")
    git(root, "add", "-A")
    git(root, "commit", "-m", "initial application")
    return root


def accept_change(root: Path) -> str:
    """Make and commit the change a capability is later captured from."""
    baseline = git(root, "rev-parse", "HEAD")
    (root / "app" / "registry.py").write_text(ACCEPTED_REGISTRY, encoding="utf-8")
    (root / "app" / "notes.md").write_text("behavioural work\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-m", "add ping handler")
    return baseline


# --- refusals --------------------------------------------------------------


def test_capture_refuses_a_dirty_working_tree(external_repo, tmp_path):
    baseline = accept_change(external_repo)
    (external_repo / "app" / "scratch.py").write_text("x = 1\n", encoding="utf-8")

    with pytest.raises(CapabilityRefusal, match="working tree is not clean"):
        capture(
            external_repo,
            tmp_path / "out",
            capability_id="app.x",
            baseline=baseline,
            declared=["app/registry.py"],
        )


def test_capture_refuses_when_nothing_was_accepted(external_repo, tmp_path):
    with pytest.raises(CapabilityRefusal, match="nothing was accepted"):
        capture(
            external_repo,
            tmp_path / "out",
            capability_id="app.x",
            baseline="HEAD",
            declared=["app/registry.py"],
        )


def test_capture_refuses_a_file_that_did_not_change(external_repo, tmp_path):
    baseline = accept_change(external_repo)

    with pytest.raises(CapabilityRefusal, match="did not change"):
        capture(
            external_repo,
            tmp_path / "out",
            capability_id="app.x",
            baseline=baseline,
            declared=["app/__init__.py"],
        )


def test_capture_refuses_to_overwrite_an_existing_directory(external_repo, tmp_path):
    baseline = accept_change(external_repo)
    existing = tmp_path / "out"
    existing.mkdir()

    with pytest.raises(CapabilityError, match="already exists"):
        capture(
            external_repo,
            existing,
            capability_id="app.x",
            baseline=baseline,
            declared=["app/registry.py"],
        )


def test_capture_rejects_paths_that_escape_the_repository(external_repo, tmp_path):
    baseline = accept_change(external_repo)

    with pytest.raises(CapabilityError, match="normalized relative path"):
        capture(
            external_repo,
            tmp_path / "out",
            capability_id="app.x",
            baseline=baseline,
            declared=["../outside.py"],
        )


# --- what capture produces -------------------------------------------------


def test_before_bytes_come_from_the_baseline_not_from_subtraction(
    external_repo, tmp_path
):
    baseline = accept_change(external_repo)
    candidate, _, _ = capture(
        external_repo,
        tmp_path / "out",
        capability_id="app.add-registry-handler",
        baseline=baseline,
        declared=["app/registry.py"],
    )

    captured = (candidate / "examples/fidelity/before/app/registry.py").read_text()
    assert captured == BASE_REGISTRY


def test_excluded_files_are_listed_rather_than_silently_dropped(
    external_repo, tmp_path
):
    baseline = accept_change(external_repo)
    candidate, declared, excluded = capture(
        external_repo,
        tmp_path / "out",
        capability_id="app.add-registry-handler",
        baseline=baseline,
        declared=["app/registry.py"],
    )

    assert declared == ["app/registry.py"]
    assert excluded == ["app/notes.md"]
    scope = (candidate / "examples/fidelity/scope.yaml").read_text()
    assert "app/notes.md" in scope
    assert baseline in scope


def test_scope_is_valid_yaml_when_nothing_is_excluded(external_repo, tmp_path):
    """Regression: an empty sequence must be inline, not a bare [] on its own line.

    Found by running the README walkthrough, where the accepted change touched
    only the declared file. Every unit test until then happened to exclude
    something, so the empty branch was never rendered.
    """
    import yaml

    baseline = git(external_repo, "rev-parse", "HEAD")
    (external_repo / "app" / "registry.py").write_text(
        ACCEPTED_REGISTRY, encoding="utf-8"
    )
    git(external_repo, "add", "-A")
    git(external_repo, "commit", "-m", "only the declared file")

    candidate, _, excluded = capture(
        external_repo,
        tmp_path / "out",
        capability_id="app.add-registry-handler",
        baseline=baseline,
        declared=["app/registry.py"],
    )

    assert excluded == []
    scope = yaml.safe_load((candidate / "examples/fidelity/scope.yaml").read_text())
    assert scope["excluded"] == []
    assert scope["included"][0]["path"] == "app/registry.py"


def test_expected_patch_is_contained_in_accepted_patch(external_repo, tmp_path):
    """Containment holds by construction: one renderer, two file sets."""
    baseline = accept_change(external_repo)
    candidate, _, _ = capture(
        external_repo,
        tmp_path / "out",
        capability_id="app.add-registry-handler",
        baseline=baseline,
        declared=["app/registry.py"],
    )

    expected = (candidate / "examples/fidelity/expected.patch").read_text()
    accepted = (candidate / "examples/fidelity/accepted.patch").read_text()
    assert expected in accepted
    assert "app/notes.md" in accepted
    assert "app/notes.md" not in expected


# --- the acceptance criterion ----------------------------------------------


def test_captured_candidate_passes_the_four_gates_in_an_external_repository(
    external_repo, tmp_path
):
    """End to end in a project that knows nothing about SEH.

    `capture` writes the fixtures and both patches; the agent writes templates,
    parameters and steps. No generated byte is edited by hand. If this passes,
    the mechanical half of authoring is genuinely off the developer's plate.
    """
    baseline = accept_change(external_repo)
    candidate, _, _ = capture(
        external_repo,
        tmp_path / "candidate",
        capability_id="app.add-registry-handler",
        baseline=baseline,
        declared=["app/registry.py"],
    )

    # --- the judgement half, which SEH deliberately does not generate ---
    (candidate / "capability.yaml").write_text(MANIFEST, encoding="utf-8")
    (candidate / "templates" / "handler.py.tmpl").write_text(
        'def handler_{{ name }}() -> str:\n    return "{{ name }}"', encoding="utf-8"
    )
    (candidate / "templates" / "registration.py.tmpl").write_text(
        'registry["{{ name }}"] = handler_{{ name }}', encoding="utf-8"
    )
    (candidate / "examples/fidelity/case.yaml").write_text(
        "parameters:\n  name: ping\n", encoding="utf-8"
    )

    after_pong = ACCEPTED_REGISTRY.replace(
        '    return "ping"\n',
        '    return "ping"\n\n\ndef handler_pong() -> str:\n    return "pong"\n',
        1,
    ).replace(
        '    registry["ping"] = handler_ping\n',
        '    registry["ping"] = handler_ping\n    registry["pong"] = handler_pong\n',
    )
    patch = "".join(
        difflib.unified_diff(
            ACCEPTED_REGISTRY.splitlines(keepends=True),
            after_pong.splitlines(keepends=True),
            fromfile="a/app/registry.py",
            tofile="b/app/registry.py",
        )
    )
    generalization = candidate / "examples" / "generalization"
    generalization.joinpath("before/app/registry.py").write_text(
        ACCEPTED_REGISTRY, encoding="utf-8"
    )
    generalization.joinpath("case.yaml").write_text(
        "parameters:\n  name: pong\napproved: true\n", encoding="utf-8"
    )
    generalization.joinpath("expected.patch").write_text(patch, encoding="utf-8")
    generalization.joinpath("accepted.patch").write_text(patch, encoding="utf-8")
    # The second case is authored, not captured, so its digests are recorded by
    # whoever wrote it. `capture` pre-fills this case from the fidelity change,
    # and every byte of that pre-fill is meant to be replaced.
    record_scope_digests(generalization)

    refusal = candidate / "examples" / "refusal"
    refusal.joinpath("before/app/registry.py").write_text(
        "from __future__ import annotations\n\n\ndef build_registry() -> dict:\n"
        "    return {}\n",
        encoding="utf-8",
    )
    refusal.joinpath("case.yaml").write_text(
        "parameters:\n  name: nope\n", encoding="utf-8"
    )

    report = validate_candidate(candidate, allow_verification=True)

    assert report.passed, [(gate.name, gate.detail) for gate in report.gates]
    assert [gate.name for gate in report.gates] == [
        "fidelity",
        "generalization",
        "idempotency",
        "safe_refusal",
    ]

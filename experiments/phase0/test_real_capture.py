from __future__ import annotations

import difflib
import hashlib
from pathlib import Path

import yaml

from seh.capability import (
    _load_case,
    _reproduction_gate,
    apply_candidate,
    load_candidate,
    validate_candidate,
)


ROOT = Path(__file__).parent
CANDIDATE = ROOT / "real_capture/add-capability-subcommand"
TARGET = "src/seh/capability_cli.py"


def _patch(before: dict[str, bytes], after: dict[str, bytes]) -> str:
    chunks: list[str] = []
    for path in sorted(set(before) | set(after)):
        chunks.extend(
            difflib.unified_diff(
                before.get(path, b"").decode().splitlines(keepends=True),
                after.get(path, b"").decode().splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )
    return "".join(chunks)


def test_install_capture_uses_the_recorded_historical_bytes():
    scope = yaml.safe_load(
        (CANDIDATE / "examples/fidelity/scope.yaml").read_text(encoding="utf-8")
    )
    before = (CANDIDATE / f"examples/fidelity/before/{TARGET}").read_bytes()
    accepted = (CANDIDATE / "examples/fidelity/accepted.patch").read_bytes()

    assert scope["baseline"] == {
        "commit": "717e87797ec2623fa0ce8de1e3b7424db3f14777",
        "tree": "f496004314c6f880f7dae4d7a7b6bcb50671da7c",
    }
    assert scope["accepted"] == {
        "commit": "abbb477cfb40671ec5a2f0d22e53be5dbea67248",
        "tree": "9c9ce3fc7175184777cf95a3eed9998ed2a5fee5",
    }
    assert hashlib.sha256(before).hexdigest() == scope["artifacts"]["before_sha256"]
    assert (
        hashlib.sha256(accepted).hexdigest()
        == scope["artifacts"]["accepted_patch_sha256"]
    )
    fixture_files = {
        path.relative_to(CANDIDATE / "examples/fidelity/before").as_posix()
        for path in (CANDIDATE / "examples/fidelity/before").rglob("*")
        if path.is_file()
    }
    assert fixture_files == {TARGET}


def test_install_fidelity_replays_the_literal_accepted_wiring():
    candidate = load_candidate(CANDIDATE)
    case = _load_case(candidate, "fidelity", expected=True)
    before = case.before

    after = apply_candidate(candidate, before, {"name": "install"})

    assert _patch(before, after) == case.expected_patch
    assert _reproduction_gate(candidate, case).passed


def test_run_proposal_changes_only_the_two_name_parameterized_fragments():
    candidate = load_candidate(CANDIDATE)
    generalization = CANDIDATE / "examples/generalization"
    before = {TARGET: (generalization / "before" / TARGET).read_bytes()}

    after = apply_candidate(candidate, before, {"name": "run"})

    proposal = (CANDIDATE / "proposals/run.patch").read_text(encoding="utf-8")
    assert proposal == (generalization / "expected.patch").read_text(encoding="utf-8")
    assert proposal == (generalization / "accepted.patch").read_text(encoding="utf-8")
    assert _patch(before, after) == proposal
    assert b"capability_run.py" not in after[TARGET]
    assert b"from .capability_run import execute" in after[TARGET]
    assert b"configure_run_parser(capability_subcommands, cmd_run)" in after[TARGET]


def test_real_candidate_passes_fidelity_generalization_idempotency_and_refusal():
    report = validate_candidate(CANDIDATE, allow_verification=True)

    assert report.passed
    assert [(gate.name, gate.passed) for gate in report.gates] == [
        ("fidelity", True),
        ("generalization", True),
        ("idempotency", True),
        ("safe_refusal", True),
    ]


def test_run_generalization_was_proposed_before_implementation_and_approved():
    scope = yaml.safe_load(
        (CANDIDATE / "examples/generalization/scope.yaml").read_text(encoding="utf-8")
    )
    proposal = (CANDIDATE / "proposals/run.patch").read_bytes()

    assert scope["proposal"]["commit"] == "548bd33ea5d19669a464b01353a6ca58b9087dfa"
    assert scope["proposal"]["patch_sha256"] == hashlib.sha256(proposal).hexdigest()
    assert scope["approval"] == {
        "status": "developer-approved",
        "instruction": "faça todos esses ajustes",
    }
    assert scope["honesty_test"]["provisional_primitive_added_for_coverage"] is False


def test_capture_declares_behavioral_exclusions_and_honesty_rationale():
    scope = yaml.safe_load(
        (CANDIDATE / "examples/fidelity/scope.yaml").read_text(encoding="utf-8")
    )

    excluded_paths = {item["path"] for item in scope["excluded"]}
    assert "src/seh/capability_install.py" in excluded_paths
    assert "src/seh/capability_catalog.py" in excluded_paths
    assert "tests/test_capability_install.py" in excluded_paths
    assert "would_refactor_without_capture" in scope["honesty_test"]
    assert scope["metrics"] == {
        "accepted_files": 12,
        "accepted_insertions": 831,
        "accepted_deletions": 13,
        "structural_files": 1,
        "structural_insertions": 10,
        "structural_share_of_insertions": 0.012,
        "interpretation": (
            "value is navigation and shape reuse, not bulk code generation; measure "
            "reduced rediscovery and retries across repeated invocations"
        ),
    }

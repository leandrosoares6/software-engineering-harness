"""Tests for anchoring a capability's patches outside the package.

These exist because of a real failure. A capability captured in a small external
project shipped a fidelity case whose `accepted.patch` claimed the developer had
written `help="TODO"`, when the accepted commit said `help="show status"`. The
patch had been adjusted to fit a limitation of the templates. Every gate passed,
because containment only ever compared `expected.patch` against `accepted.patch`
— two author-supplied files checked against each other and nothing else.

`scope.yaml` named the two commits that would have exposed it, and nothing read
them. The tests below pin both anchors that now close the loop: the recorded
digests, and the recomputation from Git.
"""

from __future__ import annotations

import difflib
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

from seh import provenance
from seh.capability import validate_candidate
from seh.capability_capture import capture
from seh.capability_cli import cmd_validate
from seh.errors import CapabilityError
from test_capability import candidate_package
from test_capability_capture import (  # noqa: F401 - external_repo is a fixture
    ACCEPTED_REGISTRY,
    MANIFEST,
    accept_change,
    external_repo,
)


def _rerecord(case: Path) -> None:
    """Rewrite a case's digests to match its patches, as a forger would."""
    scope = case / "scope.yaml"
    text = scope.read_text(encoding="utf-8")
    for artifact in ("accepted", "expected"):
        actual = provenance.digest(
            (case / f"{artifact}.patch").read_text(encoding="utf-8")
        )
        text = (
            "\n".join(
                f"  {artifact}_patch_sha256: {actual}"
                if line.startswith(f"  {artifact}_patch_sha256:")
                else line
                for line in text.splitlines()
            )
            + "\n"
        )
    scope.write_text(text, encoding="utf-8")


def _author(candidate: Path) -> Path:
    """Fill in the judgement half `capture` deliberately leaves as TODO."""
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
    _rerecord(generalization)

    refusal = candidate / "examples" / "refusal"
    refusal.joinpath("before/app/registry.py").write_text(
        "from __future__ import annotations\n\n\ndef build_registry() -> dict:\n"
        "    return {}\n",
        encoding="utf-8",
    )
    refusal.joinpath("case.yaml").write_text(
        "parameters:\n  name: nope\n", encoding="utf-8"
    )
    return candidate


@pytest.fixture
def captured(external_repo: Path) -> Path:  # noqa: F811
    """A fully authored capability, captured from a real accepted commit."""
    baseline = accept_change(external_repo)
    candidate, _, _ = capture(
        external_repo,
        external_repo / "candidate",
        capability_id="app.add-registry-handler",
        baseline=baseline,
        declared=["app/registry.py"],
    )
    return _author(candidate)


# --- the digest anchor, which needs no repository --------------------------


def test_editing_a_patch_without_its_record_is_refused(captured):
    """The careless half of the failure: adjust the patch, forget scope.yaml."""
    accepted = captured / "examples/fidelity/accepted.patch"
    accepted.write_text(
        accepted.read_text(encoding="utf-8").replace("behavioural work", "TODO"),
        encoding="utf-8",
    )

    with pytest.raises(CapabilityError, match="does not match its recorded digest"):
        validate_candidate(captured, allow_verification=True)


def test_a_package_without_recorded_digests_is_refused(captured):
    """A package predating the anchor must fail loudly, not pass by omission."""
    scope = captured / "examples/fidelity/scope.yaml"
    kept = [
        line
        for line in scope.read_text(encoding="utf-8").splitlines()
        if "sha256" not in line and line.strip() != "artifacts:"
    ]
    scope.write_text("\n".join(kept) + "\n", encoding="utf-8")

    with pytest.raises(CapabilityError, match="declares no artifacts block"):
        validate_candidate(captured, allow_verification=True)


def test_digest_error_reports_the_full_actual_sha256(captured):
    """The message must be actionable: a truncated hash cannot be pasted back."""
    accepted = captured / "examples/fidelity/accepted.patch"
    body = accepted.read_text(encoding="utf-8").replace("behavioural work", "TODO")
    accepted.write_text(body, encoding="utf-8")

    with pytest.raises(CapabilityError) as raised:
        validate_candidate(captured, allow_verification=True)
    assert provenance.digest(body) in str(raised.value)


# --- the history anchor, which is what a consistent forgery cannot survive --


def test_captured_package_is_verified_against_the_accepted_commit(captured):
    report = validate_candidate(captured, allow_verification=True)

    assert report.passed
    assert report.provenance.status == provenance.VERIFIED
    assert "is consistent with" in report.provenance.detail


def test_self_consistent_patches_are_still_contradicted_by_history(captured):
    """The failure that started this, reproduced exactly.

    The registration line is rewritten to what the templates happen to produce,
    in both patches, with both digests re-recorded. Containment holds, the two
    files agree, and nothing inside the package objects. Only the accepted commit
    disagrees — and that is now enough to refuse it.
    """
    case = captured / "examples/fidelity"
    for name in ("expected.patch", "accepted.patch"):
        artifact = case / name
        artifact.write_text(
            artifact.read_text(encoding="utf-8").replace(
                'registry["ping"] = handler_ping', 'registry["ping"] = TODO'
            ),
            encoding="utf-8",
        )
    _rerecord(case)

    with pytest.raises(CapabilityError, match="a line to app/registry.py"):
        validate_candidate(captured, allow_verification=True)


def test_unreachable_history_is_reported_rather_than_assumed(captured):
    """A rebase must not silently downgrade the check to digests only."""
    scope = captured / "examples/fidelity/scope.yaml"
    # Hex, not all-digit: an all-digit revision is a YAML integer, which
    # `test_a_numeric_commit_is_refused_rather_than_ignored` covers separately.
    absent = "abcdef" + "0" * 34
    scope.write_text(
        "\n".join(
            f"  commit: {absent}" if line.startswith("  commit:") else line
            for line in scope.read_text(encoding="utf-8").splitlines()
        )
        + "\n",
        encoding="utf-8",
    )

    report = validate_candidate(captured, allow_verification=True)

    assert report.passed
    assert report.provenance.status == provenance.UNREACHABLE
    assert "digest only" in report.provenance.detail


def test_a_numeric_commit_is_refused_rather_than_ignored(captured):
    """YAML reads an all-digit revision as an integer.

    Treating that as "no history declared" would silently downgrade the history
    anchor to the digest anchor, which is precisely the class of quiet weakening
    this module exists to prevent.
    """
    scope = captured / "examples/fidelity/scope.yaml"
    scope.write_text(
        "\n".join(
            f"  commit: {'0' * 40}" if line.startswith("  commit:") else line
            for line in scope.read_text(encoding="utf-8").splitlines()
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(CapabilityError, match="must be a quoted revision string"):
        validate_candidate(captured, allow_verification=True)


def test_synthesized_fixture_declares_no_history(tmp_path):
    """Packages built by hand in tests are honest about having no commits."""
    report = validate_candidate(candidate_package(tmp_path), allow_verification=True)

    assert report.passed
    assert report.provenance.status == provenance.NOT_DECLARED


# --- the developer has to be able to see which one they got ----------------


def test_validate_prints_the_provenance_status_on_every_run(captured, capsys):
    cmd_validate(Namespace(candidate=str(captured), allow_verification=True))

    output = capsys.readouterr().out
    assert provenance.VERIFIED in output
    assert "PASS fidelity" in output


def test_capture_writes_digests_a_second_reader_can_reproduce(external_repo):  # noqa: F811
    """Writer and verifier share one renderer, so the record is checkable."""
    baseline = accept_change(external_repo)
    candidate, _, _ = capture(
        external_repo,
        external_repo / "candidate",
        capability_id="app.add-registry-handler",
        baseline=baseline,
        declared=["app/registry.py"],
    )

    scope = (candidate / "examples/fidelity/scope.yaml").read_text(encoding="utf-8")
    accepted = (candidate / "examples/fidelity/accepted.patch").read_text(
        encoding="utf-8"
    )
    head = subprocess.run(
        ["git", "-C", str(external_repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    recomputed = provenance.accepted_change(external_repo, baseline, head)
    assert recomputed.patch == accepted
    assert f"accepted_patch_sha256: {provenance.digest(accepted)}" in scope


# --- shapes the claim parser has to survive --------------------------------


def test_a_deleted_file_contributes_no_added_lines(captured):
    """`+++ /dev/null` marks a deletion; its `-` lines are not claims of content.

    Attributing them to a path would make the parser check the deleted body
    against the accepted commit, where it correctly no longer exists.
    """
    claims = provenance._patch_claims(
        "--- a/app/gone.py\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-x = 1\n-y = 2\n"
    )

    assert claims == {}


def test_a_claim_against_a_file_absent_from_history_is_a_mismatch(captured):
    case = captured / "examples/fidelity"
    for name in ("expected.patch", "accepted.patch"):
        artifact = case / name
        artifact.write_text(
            artifact.read_text(encoding="utf-8").replace(
                "app/registry.py", "app/ghost.py"
            ),
            encoding="utf-8",
        )
    _rerecord(case)

    with pytest.raises(CapabilityError, match="app/ghost.py does not exist at"):
        validate_candidate(captured, allow_verification=True)

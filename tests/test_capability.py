from __future__ import annotations

import difflib
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest
import yaml

from seh.capability import load_candidate, validate_candidate
from seh.capability_cli import cmd_validate
from seh.cli import main
from seh.errors import CapabilityError, CapabilityValidationError


BASE_SOURCE = b"""from __future__ import annotations

import argparse


def cmd_existing(args: argparse.Namespace) -> int:
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)

    existing = subcommands.add_parser("existing")
    existing.set_defaults(handler=cmd_existing)
    return parser
"""

HANDLER = """def cmd_{{ name }}(args: argparse.Namespace) -> int:
    raise NotImplementedError("cmd_{{ name }}")"""

REGISTRATION = """{{ name }} = subcommands.add_parser("{{ name }}")
{{ name }}.set_defaults(handler=cmd_{{ name }})"""


def _manual_add(source: bytes, name: str) -> bytes:
    handler = (
        f"\n\ndef cmd_{name}(args: argparse.Namespace) -> int:\n"
        f'    raise NotImplementedError("cmd_{name}")\n'
    ).encode()
    source = source.replace(
        b"\n\ndef build_parser() -> argparse.ArgumentParser:\n",
        handler + b"\n\ndef build_parser() -> argparse.ArgumentParser:\n",
    )
    registration = (
        f'\n    {name} = subcommands.add_parser("{name}")\n'
        f"    {name}.set_defaults(handler=cmd_{name})\n"
    ).encode()
    return source.replace(b"    return parser\n", registration + b"    return parser\n")


def _patch(before: bytes, after: bytes) -> str:
    return "".join(
        difflib.unified_diff(
            before.decode().splitlines(keepends=True),
            after.decode().splitlines(keepends=True),
            fromfile="a/cli.py",
            tofile="b/cli.py",
        )
    )


def _write_case(
    candidate: Path,
    name: str,
    parameter: str,
    source: bytes,
    *,
    approved: bool | None = None,
    expected: bytes | None = None,
) -> None:
    case = candidate / "examples" / name
    (case / "before").mkdir(parents=True)
    (case / "before" / "cli.py").write_bytes(source)
    data: dict[str, object] = {"parameters": {"name": parameter}}
    if approved is not None:
        data["approved"] = approved
    (case / "case.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    if expected is not None:
        expected_patch = _patch(source, expected)
        (case / "expected.patch").write_text(expected_patch, encoding="utf-8")
        (case / "accepted.patch").write_text(expected_patch, encoding="utf-8")
        (case / "scope.yaml").write_text(
            "rationale: structural subset selected from an accepted change\n",
            encoding="utf-8",
        )


def candidate_package(tmp_path: Path) -> Path:
    candidate = tmp_path / "candidate"
    templates = candidate / "templates"
    templates.mkdir(parents=True)
    (templates / "handler.py.tmpl").write_text(HANDLER, encoding="utf-8")
    (templates / "registration.py.tmpl").write_text(REGISTRATION, encoding="utf-8")
    manifest = {
        "schema": "seh.capability.phase0/v0.1",
        "id": "seh.add-capability-subcommand",
        "version": 1,
        "parameters": {"name": {"type": "python_identifier"}},
        "preconditions": [
            {
                "uses": "text.absent",
                "with": {"file": "cli.py", "value": "def cmd_{{ name }}("},
            }
        ],
        "steps": [
            {
                "uses": "splice.after",
                "with": {
                    "file": "cli.py",
                    "locator": "python.symbol",
                    "selector": "last_with_prefix",
                    "prefix": "cmd_",
                    "template": "templates/handler.py.tmpl",
                },
            },
            {
                "uses": "splice.before",
                "with": {
                    "file": "cli.py",
                    "locator": "python.statement",
                    "function": "build_parser",
                    "statement": "return",
                    "lead": "\n",
                    "template": "templates/registration.py.tmpl",
                },
            },
        ],
        "verification": [
            {
                "uses": "verify.command",
                "with": {
                    "executable": sys.executable,
                    "args": ["-m", "py_compile", "cli.py"],
                    "timeout_seconds": 5,
                    "expected_exit": 0,
                },
            }
        ],
    }
    (candidate / "capability.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    _write_case(
        candidate,
        "fidelity",
        "install",
        BASE_SOURCE,
        expected=_manual_add(BASE_SOURCE, "install"),
    )
    _write_case(
        candidate,
        "generalization",
        "run",
        BASE_SOURCE,
        approved=True,
        expected=_manual_add(BASE_SOURCE, "run"),
    )
    _write_case(candidate, "refusal", "install", b"x = 1\n")
    return candidate


def _manifest(candidate: Path) -> dict:
    return yaml.safe_load((candidate / "capability.yaml").read_text())


def _save_manifest(candidate: Path, manifest: dict) -> None:
    (candidate / "capability.yaml").write_text(
        yaml.safe_dump(manifest), encoding="utf-8"
    )


def _validate(candidate: Path):
    return validate_candidate(candidate, allow_verification=True)


def set_different_expected_patch(candidate: Path) -> None:
    case = candidate / "examples/fidelity"
    different = _patch(BASE_SOURCE, BASE_SOURCE + b"# unexpected\n")
    (case / "expected.patch").write_text(different, encoding="utf-8")
    (case / "accepted.patch").write_text(different, encoding="utf-8")


def test_validate_candidate_passes_all_four_gates(tmp_path):
    report = _validate(candidate_package(tmp_path))

    assert report.passed
    assert [gate.name for gate in report.gates] == [
        "fidelity",
        "generalization",
        "idempotency",
        "safe_refusal",
    ]
    assert all(gate.passed for gate in report.gates)


def test_load_candidate_rejects_unknown_schema(tmp_path):
    candidate = candidate_package(tmp_path)
    manifest = yaml.safe_load((candidate / "capability.yaml").read_text())
    manifest["schema"] = "seh.capability/v99"
    (candidate / "capability.yaml").write_text(
        yaml.safe_dump(manifest), encoding="utf-8"
    )

    with pytest.raises(CapabilityError, match="unsupported capability schema"):
        load_candidate(candidate)


def test_load_candidate_rejects_unknown_primitive(tmp_path):
    candidate = candidate_package(tmp_path)
    manifest = yaml.safe_load((candidate / "capability.yaml").read_text())
    manifest["steps"][0]["uses"] = "python.eval"
    (candidate / "capability.yaml").write_text(
        yaml.safe_dump(manifest), encoding="utf-8"
    )

    with pytest.raises(CapabilityError, match="unsupported step primitive"):
        load_candidate(candidate)


def test_load_candidate_rejects_paths_outside_package(tmp_path):
    candidate = candidate_package(tmp_path)
    manifest = yaml.safe_load((candidate / "capability.yaml").read_text())
    manifest["steps"][0]["with"]["template"] = "../secret"
    (candidate / "capability.yaml").write_text(
        yaml.safe_dump(manifest), encoding="utf-8"
    )

    with pytest.raises(CapabilityError, match="relative path"):
        load_candidate(candidate)


def test_fidelity_reports_a_different_patch(tmp_path):
    candidate = candidate_package(tmp_path)
    set_different_expected_patch(candidate)

    report = _validate(candidate)

    gate = next(gate for gate in report.gates if gate.name == "fidelity")
    assert not gate.passed
    assert "patch differs" in gate.detail


def test_generalization_requires_developer_approval(tmp_path):
    candidate = candidate_package(tmp_path)
    case_path = candidate / "examples" / "generalization" / "case.yaml"
    case = yaml.safe_load(case_path.read_text())
    case["approved"] = False
    case_path.write_text(yaml.safe_dump(case), encoding="utf-8")

    report = _validate(candidate)

    gate = next(gate for gate in report.gates if gate.name == "generalization")
    assert not gate.passed
    assert "developer-approved" in gate.detail


def test_parameter_type_is_enforced(tmp_path):
    candidate = candidate_package(tmp_path)
    case_path = candidate / "examples" / "fidelity" / "case.yaml"
    case = yaml.safe_load(case_path.read_text())
    case["parameters"]["name"] = "not-valid-python"
    case_path.write_text(yaml.safe_dump(case), encoding="utf-8")

    report = _validate(candidate)

    gate = next(gate for gate in report.gates if gate.name == "fidelity")
    assert not gate.passed
    assert "python_identifier" in gate.detail


def test_verification_failure_fails_fidelity(tmp_path):
    candidate = candidate_package(tmp_path)
    manifest = yaml.safe_load((candidate / "capability.yaml").read_text())
    manifest["verification"][0]["with"]["expected_exit"] = 7
    (candidate / "capability.yaml").write_text(
        yaml.safe_dump(manifest), encoding="utf-8"
    )

    report = _validate(candidate)

    gate = next(gate for gate in report.gates if gate.name == "fidelity")
    assert not gate.passed
    assert "verification command exited" in gate.detail


def test_yaml_cannot_construct_python_objects(tmp_path):
    candidate = candidate_package(tmp_path)
    (candidate / "capability.yaml").write_text(
        "!!python/object/apply:os.system ['echo unsafe']\n", encoding="utf-8"
    )

    with pytest.raises(CapabilityError, match="invalid capability YAML"):
        load_candidate(candidate)


def test_capability_validate_command_prints_each_gate(tmp_path, capsys):
    assert (
        cmd_validate(
            Namespace(
                candidate=str(candidate_package(tmp_path)), allow_verification=True
            )
        )
        == 0
    )

    output = capsys.readouterr().out
    assert "Capability seh.add-capability-subcommand" in output
    assert output.count("PASS") == 4


def test_capability_validate_command_raises_for_failed_gate(tmp_path, capsys):
    candidate = candidate_package(tmp_path)
    set_different_expected_patch(candidate)

    with pytest.raises(CapabilityValidationError, match="fidelity"):
        cmd_validate(Namespace(candidate=str(candidate), allow_verification=True))

    assert "FAIL fidelity" in capsys.readouterr().out


def test_verification_execution_is_denied_by_default(tmp_path, monkeypatch):
    candidate = candidate_package(tmp_path)
    executed = False

    def unexpected_execution(*args, **kwargs):
        nonlocal executed
        executed = True
        raise AssertionError(
            "verification command must not execute without explicit consent"
        )

    monkeypatch.setattr("seh.capability.subprocess.run", unexpected_execution)

    with pytest.raises(CapabilityError, match="--allow-verification"):
        validate_candidate(candidate)
    assert not executed


def test_cli_refuses_verification_without_explicit_flag(tmp_path, monkeypatch, capsys):
    candidate = candidate_package(tmp_path)
    monkeypatch.setattr(sys, "argv", ["seh", "capability", "validate", str(candidate)])

    with pytest.raises(SystemExit) as failure:
        main()

    assert failure.value.code == 2
    assert "--allow-verification" in capsys.readouterr().err


def test_capability_validate_cli_has_deterministic_exit_codes(
    tmp_path, monkeypatch, capsys
):
    candidate = candidate_package(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["seh", "capability", "validate", str(candidate), "--allow-verification"],
    )
    with pytest.raises(SystemExit) as success:
        main()
    assert success.value.code == 0

    set_different_expected_patch(candidate)
    with pytest.raises(SystemExit) as failure:
        main()
    assert failure.value.code == 2
    assert "capability validation failed: fidelity" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("manifest_extra", "unsupported fields"),
        ("bad_id", "capability id is invalid"),
        ("bad_version", "positive integer"),
        ("keyword_parameter", "invalid parameter name"),
        ("unsupported_parameter", "unsupported parameter type"),
        ("no_parameters", "at least one parameter"),
        ("bad_precondition_value", "value must be a string"),
        ("bad_after_locator", "unsupported splice.after locator"),
        ("empty_prefix", "prefix must be a non-empty string"),
        ("bad_before_locator", "unsupported splice.before locator"),
        ("empty_function", "function must be a non-empty string"),
        ("bad_lead", "lead must be a string"),
        ("missing_template", "template does not exist"),
        ("bad_executable", "executable must be a non-empty string"),
        ("bad_args", "args must be a list of strings"),
        ("bad_timeout", "timeout_seconds must be an integer"),
        ("bad_expected_exit", "expected_exit must be an integer"),
        ("empty_steps", "must not be empty"),
    ],
)
def test_manifest_validation_is_fail_closed(tmp_path, mutation, message):
    candidate = candidate_package(tmp_path)
    manifest = _manifest(candidate)
    if mutation == "manifest_extra":
        manifest["surprise"] = True
    elif mutation == "bad_id":
        manifest["id"] = "Invalid ID"
    elif mutation == "bad_version":
        manifest["version"] = 0
    elif mutation == "keyword_parameter":
        manifest["parameters"] = {"class": {"type": "python_identifier"}}
    elif mutation == "unsupported_parameter":
        manifest["parameters"]["name"]["type"] = "source_code"
    elif mutation == "no_parameters":
        manifest["parameters"] = {}
    elif mutation == "bad_precondition_value":
        manifest["preconditions"][0]["with"]["value"] = 3
    elif mutation == "bad_after_locator":
        manifest["steps"][0]["with"]["locator"] = "text.guess"
    elif mutation == "empty_prefix":
        manifest["steps"][0]["with"]["prefix"] = ""
    elif mutation == "bad_before_locator":
        manifest["steps"][1]["with"]["statement"] = "anything"
    elif mutation == "empty_function":
        manifest["steps"][1]["with"]["function"] = ""
    elif mutation == "bad_lead":
        manifest["steps"][1]["with"]["lead"] = 1
    elif mutation == "missing_template":
        manifest["steps"][0]["with"]["template"] = "templates/missing"
    elif mutation == "bad_executable":
        manifest["verification"][0]["with"]["executable"] = ""
    elif mutation == "bad_args":
        manifest["verification"][0]["with"]["args"] = "cli.py"
    elif mutation == "bad_timeout":
        manifest["verification"][0]["with"]["timeout_seconds"] = 0
    elif mutation == "bad_expected_exit":
        manifest["verification"][0]["with"]["expected_exit"] = True
    elif mutation == "empty_steps":
        manifest["steps"] = []
    _save_manifest(candidate, manifest)

    with pytest.raises(CapabilityError, match=message):
        load_candidate(candidate)


def test_candidate_and_manifest_must_exist(tmp_path):
    with pytest.raises(CapabilityError, match="not a directory"):
        load_candidate(tmp_path / "missing")
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(CapabilityError, match="manifest not found"):
        load_candidate(empty)


def test_template_symlink_cannot_escape_candidate(tmp_path):
    candidate = candidate_package(tmp_path)
    outside = tmp_path / "outside.tmpl"
    outside.write_text("unsafe", encoding="utf-8")
    link = candidate / "templates" / "outside.tmpl"
    link.symlink_to(outside)
    manifest = _manifest(candidate)
    manifest["steps"][0]["with"]["template"] = "templates/outside.tmpl"
    _save_manifest(candidate, manifest)

    with pytest.raises(CapabilityError, match="inside the candidate package"):
        load_candidate(candidate)


def test_manifest_symlink_cannot_escape_candidate(tmp_path):
    candidate = candidate_package(tmp_path)
    manifest = candidate / "capability.yaml"
    outside = tmp_path / "outside.yaml"
    outside.write_bytes(manifest.read_bytes())
    manifest.unlink()
    manifest.symlink_to(outside)

    with pytest.raises(CapabilityError, match="inside the candidate package"):
        load_candidate(candidate)


def test_paths_reject_platform_dependent_backslashes(tmp_path):
    candidate = candidate_package(tmp_path)
    manifest = _manifest(candidate)
    manifest["steps"][0]["with"]["file"] = "..\\outside.py"
    _save_manifest(candidate, manifest)

    with pytest.raises(CapabilityError, match="POSIX separators"):
        load_candidate(candidate)


def test_fixture_directory_symlinks_are_rejected_without_traversal(tmp_path):
    candidate = candidate_package(tmp_path)
    before = candidate / "examples/fidelity/before"
    (before / "cycle").symlink_to(before, target_is_directory=True)

    with pytest.raises(CapabilityError, match="fixture symlinks are not supported"):
        _validate(candidate)


def test_fixture_file_limit_is_enforced_during_enumeration(tmp_path):
    candidate = candidate_package(tmp_path)
    before = candidate / "examples/fidelity/before"
    for index in range(100):
        (before / f"extra-{index}.py").write_text("pass\n", encoding="utf-8")

    with pytest.raises(CapabilityError, match="fixture exceeds 100 files"):
        _validate(candidate)


def test_template_rejects_undeclared_or_expression_slots(tmp_path):
    candidate = candidate_package(tmp_path)
    template = candidate / "templates" / "handler.py.tmpl"
    template.write_text("def cmd_{{ unknown }}(): pass", encoding="utf-8")
    report = _validate(candidate)
    assert "undeclared parameter" in report.gates[0].detail

    template.write_text("def cmd_{{ name.upper() }}(): pass", encoding="utf-8")
    report = _validate(candidate)
    assert "invalid template expression" in report.gates[0].detail


def test_case_files_are_required_and_must_be_well_formed(tmp_path):
    candidate = candidate_package(tmp_path)
    generalization = candidate / "examples" / "generalization"
    (generalization / "expected.patch").unlink()
    with pytest.raises(CapabilityError, match="expected.patch"):
        _validate(candidate)

    candidate = candidate_package(tmp_path / "second")
    case_path = candidate / "examples/generalization/case.yaml"
    case = yaml.safe_load(case_path.read_text())
    case["approved"] = "yes"
    case_path.write_text(yaml.safe_dump(case), encoding="utf-8")
    with pytest.raises(CapabilityError, match="approved must be boolean"):
        _validate(candidate)


def test_expected_patch_hunks_must_be_contained_in_accepted_patch(tmp_path):
    candidate = candidate_package(tmp_path)
    accepted = candidate / "examples/fidelity/accepted.patch"
    accepted.write_text(
        "--- a/other.py\n+++ b/other.py\n@@ -1 +1 @@\n-old\n+new\n",
        encoding="utf-8",
    )

    with pytest.raises(CapabilityError, match="not contained in accepted.patch"):
        _validate(candidate)


def test_accepted_patch_may_include_git_envelope_and_unrelated_hunks(tmp_path):
    candidate = candidate_package(tmp_path)
    case = candidate / "examples/fidelity"
    expected = (case / "expected.patch").read_text(encoding="utf-8")
    accepted = (
        "diff --git a/cli.py b/cli.py\n"
        "index 1111111..2222222 100644\n"
        f"{expected}"
        "diff --git a/other.py b/other.py\n"
        "--- a/other.py\n"
        "+++ b/other.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )
    (case / "accepted.patch").write_text(accepted, encoding="utf-8")

    assert _validate(candidate).passed


def test_scope_containment_ignores_only_git_hunk_section_labels(tmp_path):
    candidate = candidate_package(tmp_path)
    case = candidate / "examples/fidelity"
    expected = (case / "expected.patch").read_text(encoding="utf-8")
    git_labeled = expected.replace(" @@\n", " @@ def build_parser()\n")
    (case / "accepted.patch").write_text(git_labeled, encoding="utf-8")

    assert _validate(candidate).passed


@pytest.mark.parametrize("artifact", ["accepted.patch", "scope.yaml"])
def test_scope_evidence_is_required_for_expected_cases(tmp_path, artifact):
    candidate = candidate_package(tmp_path)
    (candidate / "examples/fidelity" / artifact).unlink()

    with pytest.raises(CapabilityError, match=artifact):
        _validate(candidate)


def test_scope_yaml_must_be_a_safe_mapping(tmp_path):
    candidate = candidate_package(tmp_path)
    (candidate / "examples/fidelity/scope.yaml").write_text(
        "- narrative without keys\n", encoding="utf-8"
    )

    with pytest.raises(CapabilityError, match="scope must be a mapping"):
        _validate(candidate)


@pytest.mark.parametrize(
    ("raised", "message"),
    [
        (subprocess.TimeoutExpired("verify", 5), "timed out"),
        (OSError("missing executable"), "unable to execute"),
    ],
)
def test_verification_process_failures_are_gate_failures(
    tmp_path, monkeypatch, raised, message
):
    candidate = candidate_package(tmp_path)

    def fail(*args, **kwargs):
        raise raised

    monkeypatch.setattr("seh.capability.subprocess.run", fail)
    report = _validate(candidate)

    assert not report.gates[0].passed
    assert message in report.gates[0].detail


def test_invalid_python_fixture_is_a_safe_refusal(tmp_path):
    candidate = candidate_package(tmp_path)
    refusal = candidate / "examples/refusal/before/cli.py"
    refusal.write_bytes(b"def broken(:\n")

    report = _validate(candidate)

    gate = next(gate for gate in report.gates if gate.name == "safe_refusal")
    assert gate.passed
    assert "not valid UTF-8 Python" in gate.detail

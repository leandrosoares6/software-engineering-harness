from __future__ import annotations

import os
import stat
from argparse import Namespace
from pathlib import Path

import pytest

from seh.capability_catalog import install_candidate
from seh.capability_run import _parameters, execute
from seh.cli import build_parser
from seh.capability_operation import (
    FileSnapshot,
    _restore_promoted,
    _write_through_temporaries,
    run_capability,
)
from seh.errors import CapabilityError, CapabilityRefusal
from test_capability import BASE_SOURCE, candidate_package


CAPABILITY_ID = "seh.add-capability-subcommand"


def _installed_capability(committed_repo: Path, tmp_path: Path) -> Path:
    target = committed_repo / "cli.py"
    target.write_bytes(BASE_SOURCE)
    install_candidate(
        candidate_package(tmp_path / "package"),
        committed_repo,
        allow_verification=True,
    )
    return target


def test_run_plans_without_writing_and_has_stable_immutable_identity(
    committed_repo, tmp_path
):
    target = _installed_capability(committed_repo, tmp_path)

    first = run_capability(CAPABILITY_ID, {"name": "report"}, committed_repo)
    second = run_capability(CAPABILITY_ID, {"name": "report"}, committed_repo)
    different = run_capability(CAPABILITY_ID, {"name": "doctor"}, committed_repo)

    assert target.read_bytes() == BASE_SOURCE
    assert first.operation_id == second.operation_id
    assert first.operation_id != different.operation_id
    assert len(first.operation_id) == 64
    assert first.parameters == (("name", "report"),)
    assert first.applied is False
    assert first.verified is False
    with pytest.raises(TypeError):
        first.parameters[0] = ("name", "changed")


def test_apply_requires_explicit_verification_consent_before_writing(
    committed_repo, tmp_path
):
    target = _installed_capability(committed_repo, tmp_path)

    with pytest.raises(CapabilityRefusal, match="--allow-verification"):
        run_capability(
            CAPABILITY_ID,
            {"name": "report"},
            committed_repo,
            apply=True,
        )

    assert target.read_bytes() == BASE_SOURCE


def test_apply_preserves_mode_and_unrelated_temporary_name(committed_repo, tmp_path):
    target = _installed_capability(committed_repo, tmp_path)
    target.chmod(0o755)
    unrelated = committed_repo / ".cli.py.seh-operation"
    unrelated.write_bytes(b"belongs to the developer\n")

    operation = run_capability(
        CAPABILITY_ID,
        {"name": "report"},
        committed_repo,
        apply=True,
        allow_verification=True,
    )

    assert operation.applied is True
    assert operation.verified is True
    assert stat.S_IMODE(target.stat().st_mode) == 0o755
    assert unrelated.read_bytes() == b"belongs to the developer\n"


def test_write_failure_restores_every_already_replaced_file(tmp_path, monkeypatch):
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_bytes(b"first-before\n")
    second.write_bytes(b"second-before\n")
    real_replace = os.replace
    calls = 0

    def fail_second_promotion(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated second rename failure")
        return real_replace(source, destination)

    monkeypatch.setattr("seh.capability_operation.os.replace", fail_second_promotion)

    with pytest.raises(CapabilityError, match="unable to replace declared files"):
        _write_through_temporaries(
            tmp_path,
            {"first.py": b"first-after\n", "second.py": b"second-after\n"},
        )

    assert first.read_bytes() == b"first-before\n"
    assert second.read_bytes() == b"second-before\n"


def test_apply_refuses_if_base_changes_between_plan_and_promotion(
    committed_repo, tmp_path, monkeypatch
):
    target = _installed_capability(committed_repo, tmp_path)
    original_write = _write_through_temporaries

    def race(root, changed, **kwargs):
        target.write_bytes(b"concurrent developer edit\n")
        return original_write(root, changed, **kwargs)

    monkeypatch.setattr("seh.capability_operation._write_through_temporaries", race)

    with pytest.raises(
        CapabilityRefusal, match="changed since the operation was planned"
    ):
        run_capability(
            CAPABILITY_ID,
            {"name": "report"},
            committed_repo,
            apply=True,
            allow_verification=True,
        )

    assert target.read_bytes() == b"concurrent developer edit\n"


def test_run_refuses_declared_file_symlink(committed_repo, tmp_path):
    target = _installed_capability(committed_repo, tmp_path)
    real = committed_repo / "real-cli.py"
    real.write_bytes(target.read_bytes())
    target.unlink()
    target.symlink_to(real.name)

    with pytest.raises(CapabilityError, match="must not be a symlink"):
        run_capability(CAPABILITY_ID, {"name": "report"}, committed_repo)

    assert real.read_bytes() == BASE_SOURCE


def test_failed_verification_restores_original_bytes_and_mode(
    committed_repo, tmp_path, monkeypatch
):
    target = _installed_capability(committed_repo, tmp_path)
    target.chmod(0o755)

    def fail(*args, **kwargs):
        raise CapabilityRefusal("verification failed")

    monkeypatch.setattr("seh.capability_operation.run_verification", fail)

    with pytest.raises(CapabilityRefusal, match="verification failed"):
        run_capability(
            CAPABILITY_ID,
            {"name": "report"},
            committed_repo,
            apply=True,
            allow_verification=True,
        )

    assert target.read_bytes() == BASE_SOURCE
    assert stat.S_IMODE(target.stat().st_mode) == 0o755


def test_failed_verification_restores_a_deleted_declared_file(
    committed_repo, tmp_path, monkeypatch
):
    target = _installed_capability(committed_repo, tmp_path)
    target.chmod(0o755)

    def delete_then_fail(*args, **kwargs):
        target.unlink()
        raise CapabilityRefusal("verification deleted the target")

    monkeypatch.setattr("seh.capability_operation.run_verification", delete_then_fail)

    with pytest.raises(CapabilityRefusal, match="verification deleted the target"):
        run_capability(
            CAPABILITY_ID,
            {"name": "report"},
            committed_repo,
            apply=True,
            allow_verification=True,
        )

    assert target.read_bytes() == BASE_SOURCE
    assert stat.S_IMODE(target.stat().st_mode) == 0o755


def test_successful_verifier_must_not_change_declared_result(
    committed_repo, tmp_path, monkeypatch
):
    target = _installed_capability(committed_repo, tmp_path)

    def mutate(*args, **kwargs):
        target.write_bytes(b"verification side effect\n")

    monkeypatch.setattr("seh.capability_operation.run_verification", mutate)

    with pytest.raises(CapabilityError, match="verification changed declared files"):
        run_capability(
            CAPABILITY_ID,
            {"name": "report"},
            committed_repo,
            apply=True,
            allow_verification=True,
        )

    assert target.read_bytes() == BASE_SOURCE


def test_successful_verifier_must_not_change_declared_mode(
    committed_repo, tmp_path, monkeypatch
):
    target = _installed_capability(committed_repo, tmp_path)
    target.chmod(0o755)

    def mutate_mode(*args, **kwargs):
        target.chmod(0o600)

    monkeypatch.setattr("seh.capability_operation.run_verification", mutate_mode)

    with pytest.raises(CapabilityError, match="verification changed declared files"):
        run_capability(
            CAPABILITY_ID,
            {"name": "report"},
            committed_repo,
            apply=True,
            allow_verification=True,
        )

    assert target.read_bytes() == BASE_SOURCE
    assert stat.S_IMODE(target.stat().st_mode) == 0o755


@pytest.mark.parametrize(
    ("capability_id", "setup", "message"),
    [
        ("../invalid", "none", "capability id is invalid"),
        (CAPABILITY_ID, "none", "no capability catalogue"),
        (CAPABILITY_ID, "empty_catalogue", "capability is not installed"),
        (CAPABILITY_ID, "catalogue_symlink", "catalogue must not be a symlink"),
        (CAPABILITY_ID, "capability_symlink", "capability must not be a symlink"),
    ],
)
def test_run_refuses_invalid_catalogue_boundaries(
    committed_repo, capability_id, setup, message
):
    catalog = committed_repo / ".seh-capabilities"
    if setup == "empty_catalogue":
        catalog.mkdir()
    elif setup == "catalogue_symlink":
        destination = committed_repo / "catalogue-target"
        destination.mkdir()
        catalog.symlink_to(destination.name, target_is_directory=True)
    elif setup == "capability_symlink":
        catalog.mkdir()
        destination = catalog / "actual"
        destination.mkdir()
        (catalog / CAPABILITY_ID).symlink_to(destination.name, target_is_directory=True)

    with pytest.raises(CapabilityError, match=message):
        run_capability(capability_id, {"name": "report"}, committed_repo)


def test_run_refuses_catalogue_directory_with_mismatched_manifest_id(
    committed_repo, tmp_path
):
    _installed_capability(committed_repo, tmp_path)
    catalog = committed_repo / ".seh-capabilities"
    (catalog / CAPABILITY_ID).rename(catalog / "seh.other")

    with pytest.raises(CapabilityError, match="does not match"):
        run_capability("seh.other", {"name": "report"}, committed_repo)


def test_run_refuses_absent_special_and_oversized_declared_files(
    committed_repo, tmp_path, monkeypatch
):
    target = _installed_capability(committed_repo, tmp_path)
    target.unlink()
    with pytest.raises(CapabilityRefusal, match="declared file is absent"):
        run_capability(CAPABILITY_ID, {"name": "report"}, committed_repo)

    target.mkdir()
    with pytest.raises(CapabilityRefusal, match="not a regular file"):
        run_capability(CAPABILITY_ID, {"name": "report"}, committed_repo)

    target.rmdir()
    target.write_bytes(BASE_SOURCE)
    monkeypatch.setattr("seh.capability_operation.MAX_FILE_BYTES", 1)
    with pytest.raises(CapabilityError, match="declared file exceeds 1 bytes"):
        run_capability(CAPABILITY_ID, {"name": "report"}, committed_repo)


def test_staging_failure_is_reported_without_modifying_source(
    committed_repo, tmp_path, monkeypatch
):
    target = _installed_capability(committed_repo, tmp_path)

    def fail_staging(*args, **kwargs):
        raise OSError("disk unavailable")

    monkeypatch.setattr("seh.capability_operation.tempfile.mkstemp", fail_staging)

    with pytest.raises(CapabilityError, match="unable to stage declared file"):
        run_capability(
            CAPABILITY_ID,
            {"name": "report"},
            committed_repo,
            apply=True,
            allow_verification=True,
        )

    assert target.read_bytes() == BASE_SOURCE


def test_rollback_failure_is_explicit(tmp_path, monkeypatch):
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_bytes(b"first-before\n")
    second.write_bytes(b"second-before\n")
    real_replace = os.replace
    calls = 0

    def fail_promotion_and_rollback(source, destination):
        nonlocal calls
        calls += 1
        if calls >= 2:
            raise OSError("replacement unavailable")
        return real_replace(source, destination)

    monkeypatch.setattr(
        "seh.capability_operation.os.replace", fail_promotion_and_rollback
    )

    with pytest.raises(CapabilityError, match="rollback failed"):
        _write_through_temporaries(
            tmp_path,
            {"first.py": b"first-after\n", "second.py": b"second-after\n"},
        )


def test_rollback_reports_symlink_race_without_following_it(tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_bytes(b"outside\n")
    target = tmp_path / "target.py"
    target.symlink_to(outside.name)

    failures = _restore_promoted(
        ["target.py"],
        tmp_path,
        {"target.py": FileSnapshot(b"original\n", 0o644)},
    )

    assert failures and "must not be a symlink" in failures[0]
    assert target.is_symlink()
    assert outside.read_bytes() == b"outside\n"


def test_empty_write_set_is_a_noop(tmp_path):
    _write_through_temporaries(tmp_path, {})


def test_run_parameter_parser_rejects_malformed_and_duplicate_values():
    assert _parameters(["name=value=with-equals"]) == {"name": "value=with-equals"}

    with pytest.raises(CapabilityError, match="name=value"):
        _parameters(["missing-separator"])
    with pytest.raises(CapabilityError, match="given twice"):
        _parameters(["name=first", "name=second"])


def test_run_cli_plans_by_default_and_prints_operation_id(
    committed_repo, tmp_path, capsys
):
    target = _installed_capability(committed_repo, tmp_path)

    result = execute(
        Namespace(
            capability_id=CAPABILITY_ID,
            param=["name=report"],
            repo=str(committed_repo),
            apply=False,
            allow_verification=False,
        )
    )

    assert result == 0
    assert target.read_bytes() == BASE_SOURCE
    output = capsys.readouterr().out
    assert "Planned seh.add-capability-subcommand v1" in output
    assert "Operation " in output
    assert "Rerun with --apply --allow-verification" in output


def test_run_cli_prints_verified_applied_operation(committed_repo, tmp_path, capsys):
    _installed_capability(committed_repo, tmp_path)

    result = execute(
        Namespace(
            capability_id=CAPABILITY_ID,
            param=["name=report"],
            repo=str(committed_repo),
            apply=True,
            allow_verification=True,
        )
    )

    assert result == 0
    output = capsys.readouterr().out
    assert "Applied seh.add-capability-subcommand v1 to 1 file(s), verified" in output
    assert "Operation " in output
    assert "  cli.py" in output


def test_run_parser_is_wired_as_the_generated_thin_adapter():
    parser = build_parser()

    args = parser.parse_args(
        [
            "capability",
            "run",
            CAPABILITY_ID,
            "--param",
            "name=report",
            "--repo",
            "./repository",
            "--apply",
            "--allow-verification",
        ]
    )

    from seh import capability_cli

    assert args.handler is capability_cli.cmd_run
    assert args.param == ["name=report"]
    assert args.repo == "./repository"
    assert args.apply is True
    assert args.allow_verification is True

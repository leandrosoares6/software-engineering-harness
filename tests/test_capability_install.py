from __future__ import annotations

import os
import inspect
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from seh.capability_catalog import install_candidate
from seh.capability_cli import cmd_install
from seh.cli import build_parser, main
from seh.errors import CapabilityError, CapabilityValidationError
from test_capability import candidate_package, set_different_expected_patch


def _inventory(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_install_promotes_validated_snapshot_into_canonical_repository(
    committed_repo, tmp_path
):
    candidate = candidate_package(tmp_path / "source")
    nested = committed_repo / "nested"
    nested.mkdir()

    installation = install_candidate(candidate, nested, allow_verification=True)

    expected = committed_repo / ".seh-capabilities/seh.add-capability-subcommand"
    assert installation.destination == expected
    assert installation.report.passed
    assert _inventory(expected) == _inventory(candidate)


def test_install_validates_staging_inside_ignored_local_state(
    committed_repo, tmp_path, monkeypatch
):
    candidate = candidate_package(tmp_path / "source")
    from seh import capability_catalog

    original_validate = capability_catalog.validate_candidate
    observed: list[Path] = []

    def observe_staging(path, *, allow_verification):
        observed.append(path)
        return original_validate(path, allow_verification=allow_verification)

    monkeypatch.setattr(capability_catalog, "validate_candidate", observe_staging)

    install_candidate(candidate, committed_repo, allow_verification=True)

    assert observed[0].parent == committed_repo / ".seh"
    assert not list((committed_repo / ".seh").glob("install-staging-*"))


def test_install_refuses_verification_by_default_without_creating_state(
    committed_repo, tmp_path
):
    candidate = candidate_package(tmp_path / "source")

    with pytest.raises(CapabilityError, match="--allow-verification"):
        install_candidate(candidate, committed_repo)

    assert not (committed_repo / ".seh-capabilities").exists()


def test_install_does_not_promote_candidate_that_fails_a_gate(committed_repo, tmp_path):
    candidate = candidate_package(tmp_path / "source")
    set_different_expected_patch(candidate)

    with pytest.raises(CapabilityValidationError, match="fidelity"):
        install_candidate(candidate, committed_repo, allow_verification=True)

    assert not (committed_repo / ".seh-capabilities").exists()
    state = committed_repo / ".seh"
    assert not state.exists() or not list(state.glob("install-staging-*"))


def test_install_never_overwrites_an_existing_capability(
    committed_repo, tmp_path, monkeypatch
):
    candidate = candidate_package(tmp_path / "source")
    first = install_candidate(candidate, committed_repo, allow_verification=True)
    before = _inventory(first.destination)

    def unexpected_verification(*args, **kwargs):
        raise AssertionError(
            "an existing capability must be rejected before validation"
        )

    monkeypatch.setattr("seh.capability._verify", unexpected_verification)

    with pytest.raises(CapabilityError, match="already installed"):
        install_candidate(candidate, committed_repo, allow_verification=True)

    assert _inventory(first.destination) == before


def test_install_rejects_any_symlink_in_candidate_package(committed_repo, tmp_path):
    candidate = candidate_package(tmp_path / "source")
    outside = tmp_path / "outside.txt"
    outside.write_text("not part of the candidate\n", encoding="utf-8")
    (candidate / "extra-link").symlink_to(outside)

    with pytest.raises(CapabilityError, match="symlinks are not supported"):
        install_candidate(candidate, committed_repo, allow_verification=True)

    assert not (committed_repo / ".seh-capabilities").exists()


def test_install_rejects_symlinked_local_state(committed_repo, tmp_path):
    candidate = candidate_package(tmp_path / "source")
    outside = tmp_path / "outside-state"
    outside.mkdir()
    (committed_repo / ".seh").symlink_to(outside, target_is_directory=True)

    with pytest.raises(CapabilityError, match="state directory must not be a symlink"):
        install_candidate(candidate, committed_repo, allow_verification=True)

    assert not list(outside.iterdir())


def test_install_rejects_local_state_that_is_not_a_directory(committed_repo, tmp_path):
    candidate = candidate_package(tmp_path / "source")
    (committed_repo / ".seh").write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(CapabilityError, match="state path is not a directory"):
        install_candidate(candidate, committed_repo, allow_verification=True)


@pytest.mark.parametrize(
    ("limit", "value", "message"),
    [
        ("MAX_PACKAGE_FILES", 1, "exceeds 1 files"),
        ("MAX_PACKAGE_FILE_BYTES", 1, "candidate file exceeds 1 bytes"),
        ("MAX_PACKAGE_BYTES", 1, "package exceeds 1 bytes"),
    ],
)
def test_install_enforces_candidate_package_bounds(
    committed_repo, tmp_path, monkeypatch, limit, value, message
):
    candidate = candidate_package(tmp_path / "source")
    monkeypatch.setattr(f"seh.capability_catalog.{limit}", value)

    with pytest.raises(CapabilityError, match=message):
        install_candidate(candidate, committed_repo, allow_verification=True)

    assert not (committed_repo / ".seh").exists()


def test_install_refuses_snapshot_changed_by_verification(
    committed_repo, tmp_path, monkeypatch
):
    candidate = candidate_package(tmp_path / "source")
    from seh import capability

    original_verify = capability._verify

    def mutate_snapshot(candidate, state, parameters):
        (candidate.root / "verification-created.txt").write_text(
            "changed\n", encoding="utf-8"
        )
        original_verify(candidate, state, parameters)

    monkeypatch.setattr(capability, "_verify", mutate_snapshot)

    with pytest.raises(CapabilityError, match="changed during validation"):
        install_candidate(candidate, committed_repo, allow_verification=True)

    assert not (committed_repo / ".seh-capabilities").exists()


def test_install_rechecks_catalogue_after_verification(
    committed_repo, tmp_path, monkeypatch
):
    candidate = candidate_package(tmp_path / "source")
    diverted = committed_repo / "diverted"
    diverted.mkdir()
    from seh import capability

    original_verify = capability._verify

    def replace_catalogue(candidate, state, parameters):
        catalog = committed_repo / ".seh-capabilities"
        if not catalog.exists():
            catalog.symlink_to(diverted, target_is_directory=True)
        original_verify(candidate, state, parameters)

    monkeypatch.setattr(capability, "_verify", replace_catalogue)

    with pytest.raises(CapabilityError, match="catalogue must not be a symlink"):
        install_candidate(candidate, committed_repo, allow_verification=True)

    assert not (diverted / "seh.add-capability-subcommand").exists()


def test_install_rejects_catalogue_that_is_not_a_directory(committed_repo, tmp_path):
    candidate = candidate_package(tmp_path / "source")
    (committed_repo / ".seh-capabilities").write_text(
        "not a directory\n", encoding="utf-8"
    )

    with pytest.raises(CapabilityError, match="catalogue is not a directory"):
        install_candidate(candidate, committed_repo, allow_verification=True)


def test_install_respects_existing_catalogue_lock(committed_repo, tmp_path):
    candidate = candidate_package(tmp_path / "source")
    catalog = committed_repo / ".seh-capabilities"
    catalog.mkdir()
    lock = catalog / ".install.lock"
    lock.write_text("held\n", encoding="utf-8")

    with pytest.raises(CapabilityError, match="installation is in progress"):
        install_candidate(candidate, committed_repo, allow_verification=True)

    assert lock.read_text(encoding="utf-8") == "held\n"


def test_install_rechecks_destination_while_holding_lock(
    committed_repo, tmp_path, monkeypatch
):
    candidate = candidate_package(tmp_path / "source")
    from seh import capability_catalog

    original_validate = capability_catalog.validate_candidate

    def create_racing_destination(path, *, allow_verification):
        report = original_validate(path, allow_verification=allow_verification)
        destination = (
            committed_repo / ".seh-capabilities" / "seh.add-capability-subcommand"
        )
        destination.mkdir(parents=True)
        return report

    monkeypatch.setattr(
        capability_catalog, "validate_candidate", create_racing_destination
    )

    with pytest.raises(CapabilityError, match="already installed"):
        install_candidate(candidate, committed_repo, allow_verification=True)


def test_install_cleans_staging_if_atomic_promotion_fails(
    committed_repo, tmp_path, monkeypatch
):
    candidate = candidate_package(tmp_path / "source")

    def fail_replace(source, destination):
        raise OSError("simulated rename failure")

    monkeypatch.setattr("seh.capability_catalog.os.replace", fail_replace)

    with pytest.raises(CapabilityError, match="unable to promote capability"):
        install_candidate(candidate, committed_repo, allow_verification=True)

    catalog = committed_repo / ".seh-capabilities"
    assert not (catalog / "seh.add-capability-subcommand").exists()
    state = committed_repo / ".seh"
    assert not state.exists() or not list(state.glob("install-staging-*"))
    assert not catalog.exists() or not any(catalog.iterdir())


def test_install_rejects_special_files(committed_repo, tmp_path):
    candidate = candidate_package(tmp_path / "source")
    fifo = candidate / "named-pipe"
    os.mkfifo(fifo)

    with pytest.raises(CapabilityError, match="regular files"):
        install_candidate(candidate, committed_repo, allow_verification=True)

    assert not (committed_repo / ".seh-capabilities").exists()


def test_capability_install_parser_is_nested_in_existing_group():
    parser = build_parser()

    denied = parser.parse_args(["capability", "install", "./candidate"])
    allowed = parser.parse_args(
        [
            "capability",
            "install",
            "./candidate",
            "--repo",
            "./repository",
            "--allow-verification",
        ]
    )

    assert denied.handler is cmd_install
    assert denied.allow_verification is False
    assert allowed.repo == "./repository"
    assert allowed.allow_verification is True


def test_install_wiring_is_a_thin_name_parameterized_adapter():
    handler = inspect.getsource(cmd_install)
    parser = inspect.getsource(build_parser)
    capability_parser = Path("src/seh/capability_cli.py").read_text(encoding="utf-8")

    assert "from .capability_install import execute" in handler
    assert "return execute(args)" in handler
    assert "install_candidate" not in handler
    assert "from .capability_install import configure_parser" in capability_parser
    assert (
        "configure_install_parser(capability_subcommands, cmd_install)"
        in capability_parser
    )
    assert "configure_capability_parser(subcommands)" in parser


def test_success_does_not_use_failed_installation_catalog_cleanup(
    committed_repo, tmp_path, monkeypatch
):
    candidate = candidate_package(tmp_path / "source")
    original_rmdir = Path.rmdir

    def reject_catalog_cleanup(path):
        if path.name == ".seh-capabilities":
            raise AssertionError("successful promotion must disable failure cleanup")
        return original_rmdir(path)

    monkeypatch.setattr(Path, "rmdir", reject_catalog_cleanup)

    install_candidate(candidate, committed_repo, allow_verification=True)


def test_capability_install_cli_prints_installed_destination(
    committed_repo, tmp_path, monkeypatch, capsys
):
    candidate = candidate_package(tmp_path / "source")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "seh",
            "capability",
            "install",
            str(candidate),
            "--repo",
            str(committed_repo),
            "--allow-verification",
        ],
    )

    with pytest.raises(SystemExit) as result:
        main()

    assert result.value.code == 0
    output = capsys.readouterr().out
    assert "Installed seh.add-capability-subcommand v1" in output
    assert str(committed_repo / ".seh-capabilities") in output


def test_cmd_install_reports_failed_gates_before_raising(
    committed_repo, tmp_path, capsys
):
    candidate = candidate_package(tmp_path / "source")
    set_different_expected_patch(candidate)

    with pytest.raises(CapabilityValidationError, match="fidelity"):
        cmd_install(
            Namespace(
                candidate=str(candidate),
                repo=str(committed_repo),
                allow_verification=True,
            )
        )

    assert "FAIL fidelity" in capsys.readouterr().out

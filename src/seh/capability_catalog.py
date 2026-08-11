from __future__ import annotations

import os
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .capability import ValidationReport, load_candidate, validate_candidate
from .errors import CapabilityError, CapabilityValidationError
from .git import repository_root

CATALOG_DIRECTORY = ".seh-capabilities"
MAX_PACKAGE_FILES = 500
MAX_PACKAGE_FILE_BYTES = 1_048_576
MAX_PACKAGE_BYTES = 16_777_216


@dataclass(frozen=True)
class PackageFile:
    relative: Path
    content: bytes
    mode: int


@dataclass(frozen=True)
class Installation:
    report: ValidationReport
    version: int
    destination: Path


def _read_regular_file(path: Path) -> tuple[bytes, int]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise CapabilityError(
            f"unable to snapshot candidate file {path}: {exc}"
        ) from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise CapabilityError(
                f"capability packages may contain only directories and regular files: {path}"
            )
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            content = stream.read(MAX_PACKAGE_FILE_BYTES + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(content) > MAX_PACKAGE_FILE_BYTES:
        raise CapabilityError(
            f"candidate file exceeds {MAX_PACKAGE_FILE_BYTES} bytes: {path}"
        )
    return content, stat.S_IMODE(metadata.st_mode) & 0o777


def _snapshot_candidate(path: Path) -> tuple[Path, tuple[PackageFile, ...]]:
    if path.is_symlink():
        raise CapabilityError(f"capability package symlinks are not supported: {path}")
    root = path.resolve()
    if not root.is_dir():
        raise CapabilityError(f"capability candidate is not a directory: {path}")

    files: list[PackageFile] = []
    total_bytes = 0
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    item = Path(entry.path)
                    if entry.is_symlink():
                        raise CapabilityError(
                            f"capability package symlinks are not supported: {item}"
                        )
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(item)
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        raise CapabilityError(
                            "capability packages may contain only directories and "
                            f"regular files: {item}"
                        )
                    content, mode = _read_regular_file(item)
                    files.append(PackageFile(item.relative_to(root), content, mode))
                    total_bytes += len(content)
                    if len(files) > MAX_PACKAGE_FILES:
                        raise CapabilityError(
                            f"capability package exceeds {MAX_PACKAGE_FILES} files"
                        )
                    if total_bytes > MAX_PACKAGE_BYTES:
                        raise CapabilityError(
                            f"capability package exceeds {MAX_PACKAGE_BYTES} bytes"
                        )
        except CapabilityError:
            raise
        except OSError as exc:
            raise CapabilityError(
                f"unable to enumerate capability package {directory}: {exc}"
            ) from exc
    return root, tuple(sorted(files, key=lambda item: item.relative.as_posix()))


def _materialize_snapshot(files: tuple[PackageFile, ...], destination: Path) -> None:
    for item in files:
        target = destination / item.relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(item.content)
        target.chmod(item.mode)


def _validation_failure(report: ValidationReport) -> CapabilityValidationError:
    failed = ", ".join(gate.name for gate in report.gates if not gate.passed)
    return CapabilityValidationError(
        f"capability validation failed: {failed}", report=report
    )


def install_candidate(
    candidate_path: Path,
    repository_path: Path,
    *,
    allow_verification: bool = False,
) -> Installation:
    root = repository_root(repository_path)
    _, files = _snapshot_candidate(candidate_path)
    state = root / ".seh"
    if state.is_symlink():
        raise CapabilityError(f"SEH state directory must not be a symlink: {state}")
    if state.exists() and not state.is_dir():
        raise CapabilityError(f"SEH state path is not a directory: {state}")
    state_created = False
    if not state.exists():
        state.mkdir()
        state_created = True
    staging = Path(tempfile.mkdtemp(prefix="install-staging-", dir=state))
    catalog = root / CATALOG_DIRECTORY
    catalog_created = False
    lock_descriptor: int | None = None
    lock_path = catalog / ".install.lock"
    try:
        _materialize_snapshot(files, staging)
        candidate = load_candidate(staging)
        destination = catalog / candidate.capability_id
        if catalog.is_symlink():
            raise CapabilityError(
                f"capability catalogue must not be a symlink: {catalog}"
            )
        if catalog.exists() and not catalog.is_dir():
            raise CapabilityError(f"capability catalogue is not a directory: {catalog}")
        if destination.exists() or destination.is_symlink():
            raise CapabilityError(
                f"capability is already installed: {candidate.capability_id}"
            )

        report = validate_candidate(staging, allow_verification=allow_verification)
        if not report.passed:
            raise _validation_failure(report)
        _, validated_files = _snapshot_candidate(staging)
        if validated_files != files:
            raise CapabilityError("capability snapshot changed during validation")

        if catalog.is_symlink():
            raise CapabilityError(
                f"capability catalogue must not be a symlink: {catalog}"
            )
        if catalog.exists() and not catalog.is_dir():
            raise CapabilityError(f"capability catalogue is not a directory: {catalog}")
        if not catalog.exists():
            catalog.mkdir()
            catalog_created = True
        if catalog.resolve().parent != root:
            raise CapabilityError(
                f"capability catalogue must resolve inside the repository: {catalog}"
            )

        try:
            lock_descriptor = os.open(
                lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
            )
        except FileExistsError as exc:
            raise CapabilityError(
                "another capability installation is in progress"
            ) from exc
        except OSError as exc:
            raise CapabilityError(
                f"unable to lock capability catalogue: {exc}"
            ) from exc

        if destination.exists() or destination.is_symlink():
            raise CapabilityError(
                f"capability is already installed: {candidate.capability_id}"
            )
        try:
            os.replace(staging, destination)
        except OSError as exc:
            raise CapabilityError(
                f"unable to promote capability atomically: {exc}"
            ) from exc
        catalog_created = False
        return Installation(
            report=report, version=candidate.version, destination=destination
        )
    finally:
        if lock_descriptor is not None:
            os.close(lock_descriptor)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass
        if staging.exists():
            shutil.rmtree(staging)
        if catalog_created:
            try:
                catalog.rmdir()
            except OSError:
                pass
        if state_created:
            try:
                state.rmdir()
            except OSError:
                pass

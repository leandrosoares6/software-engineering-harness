from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .capability import (
    MAX_FILE_BYTES,
    Candidate,
    apply_candidate,
    declared_files,
    load_candidate,
    render_patch,
    run_verification,
)
from .capability_catalog import CATALOG_DIRECTORY
from .errors import CapabilityError, CapabilityRefusal
from .git import repository_root


_CAPABILITY_ID = re.compile(r"[a-z0-9][a-z0-9._-]*\Z")


@dataclass(frozen=True)
class FileSnapshot:
    content: bytes
    mode: int


@dataclass(frozen=True)
class Operation:
    """One immutable, content-addressed capability invocation."""

    operation_id: str
    capability_id: str
    version: int
    parameters: tuple[tuple[str, str], ...]
    files: tuple[str, ...]
    patch: str
    applied: bool
    verified: bool
    duration_ms: int


def _installed(root: Path, capability_id: str) -> Candidate:
    if not isinstance(capability_id, str) or not _CAPABILITY_ID.fullmatch(
        capability_id
    ):
        raise CapabilityError("capability id is invalid")
    catalog = root / CATALOG_DIRECTORY
    if catalog.is_symlink():
        raise CapabilityError(f"capability catalogue must not be a symlink: {catalog}")
    if not catalog.is_dir():
        raise CapabilityRefusal(f"no capability catalogue in {root}")
    destination = catalog / capability_id
    if destination.is_symlink():
        raise CapabilityError(
            f"installed capability must not be a symlink: {destination}"
        )
    if not destination.is_dir():
        raise CapabilityRefusal(f"capability is not installed: {capability_id}")
    if destination.resolve().parent != catalog.resolve():
        raise CapabilityError(
            f"installed capability must resolve inside the catalogue: {destination}"
        )
    candidate = load_candidate(destination)
    if candidate.capability_id != capability_id:
        raise CapabilityError(
            "installed capability id does not match its catalogue directory"
        )
    return candidate


def _target(root: Path, relative: str) -> Path:
    """Resolve a normalized repository path without following symlinks."""
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise CapabilityError("declared file must be a normalized relative path")
    normalized = PurePosixPath(relative)
    if normalized.is_absolute() or any(
        part in {".", ".."} for part in normalized.parts
    ):
        raise CapabilityError("declared file must be a normalized relative path")

    current = root
    for index, part in enumerate(normalized.parts):
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            if index != len(normalized.parts) - 1:
                raise CapabilityRefusal(
                    f"declared file parent is absent: {relative}"
                ) from None
            return current
        except OSError as exc:
            raise CapabilityError(
                f"unable to inspect declared file {relative}: {exc}"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise CapabilityError(f"declared file must not be a symlink: {relative}")
        if index != len(normalized.parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
            raise CapabilityRefusal(
                f"declared file parent is not a directory: {relative}"
            )
    return current


def _read_snapshot(root: Path, relative: str) -> FileSnapshot:
    path = _target(root, relative)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        raise CapabilityRefusal(f"declared file is absent: {relative}") from None
    except OSError as exc:
        raise CapabilityError(
            f"unable to open declared file {relative}: {exc}"
        ) from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise CapabilityRefusal(f"declared file is not a regular file: {relative}")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            content = stream.read(MAX_FILE_BYTES + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(content) > MAX_FILE_BYTES:
        raise CapabilityError(
            f"declared file exceeds {MAX_FILE_BYTES} bytes: {relative}"
        )
    return FileSnapshot(content=content, mode=stat.S_IMODE(metadata.st_mode))


def _read_base_state(root: Path, candidate: Candidate) -> dict[str, FileSnapshot]:
    return {
        relative: _read_snapshot(root, relative)
        for relative in declared_files(candidate)
    }


def _stage(path: Path, content: bytes, mode: int) -> Path:
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{path.name}.seh-operation-", dir=path.parent
        )
        temporary = Path(name)
        try:
            os.fchmod(descriptor, mode)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        return temporary
    except OSError as exc:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass
        raise CapabilityError(f"unable to stage declared file {path}: {exc}") from exc


def _restore_promoted(
    promoted: list[str], root: Path, originals: dict[str, FileSnapshot]
) -> list[str]:
    failures: list[str] = []
    for relative in reversed(promoted):
        snapshot = originals[relative]
        temporary: Path | None = None
        try:
            path = _target(root, relative)
            temporary = _stage(path, snapshot.content, snapshot.mode)
            os.replace(temporary, path)
        except (CapabilityError, OSError) as exc:
            failures.append(f"{relative}: {exc}")
        finally:
            if temporary is not None:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    failures.append(f"{relative} cleanup: {exc}")
    return failures


def _write_through_temporaries(
    root: Path,
    changed: dict[str, bytes],
    *,
    expected: dict[str, FileSnapshot] | None = None,
    modes: dict[str, int] | None = None,
) -> None:
    """Optimistically replace a bounded set and restore it on ordinary failures."""
    if not changed:
        return
    originals = {relative: _read_snapshot(root, relative) for relative in changed}
    if expected is not None:
        for relative, snapshot in originals.items():
            if snapshot != expected[relative]:
                raise CapabilityRefusal(
                    f"declared file changed since the operation was planned: {relative}"
                )

    staged: list[tuple[str, Path, Path]] = []
    try:
        for relative, content in changed.items():
            path = _target(root, relative)
            mode = modes[relative] if modes is not None else originals[relative].mode
            staged.append((relative, _stage(path, content, mode), path))
    except CapabilityError:
        for _, temporary, _ in staged:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        raise

    promoted: list[str] = []
    try:
        for relative, temporary, path in staged:
            if _read_snapshot(root, relative) != originals[relative]:
                raise CapabilityRefusal(
                    f"declared file changed since the operation was planned: {relative}"
                )
            os.replace(temporary, path)
            promoted.append(relative)
    except (CapabilityError, OSError) as exc:
        rollback_failures = _restore_promoted(promoted, root, originals)
        if isinstance(exc, CapabilityRefusal) and not rollback_failures:
            raise
        detail = (
            f"; rollback failed for {', '.join(rollback_failures)}"
            if rollback_failures
            else ""
        )
        raise CapabilityError(
            f"unable to replace declared files: {exc}{detail}"
        ) from exc
    finally:
        for _, temporary, _ in staged:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass


def _operation_id(
    candidate: Candidate,
    parameters: tuple[tuple[str, str], ...],
    before: dict[str, FileSnapshot],
    patch: str,
) -> str:
    payload = {
        "schema": "seh.operation/v1",
        "capability": {"id": candidate.capability_id, "version": candidate.version},
        "parameters": parameters,
        "base": {
            path: {
                "sha256": hashlib.sha256(snapshot.content).hexdigest(),
                "mode": snapshot.mode,
            }
            for path, snapshot in sorted(before.items())
        },
        "patch_sha256": hashlib.sha256(patch.encode("utf-8")).hexdigest(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _restore_base(root: Path, before: dict[str, FileSnapshot]) -> None:
    staged: list[tuple[Path, Path]] = []
    try:
        for relative, snapshot in before.items():
            path = _target(root, relative)
            staged.append((path, _stage(path, snapshot.content, snapshot.mode)))
        for path, temporary in staged:
            os.replace(temporary, path)
    except (CapabilityError, OSError) as exc:
        raise CapabilityError(f"unable to restore declared files: {exc}") from exc
    finally:
        for _, temporary in staged:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass


def run_capability(
    capability_id: str,
    parameters: dict[str, Any],
    repository_path: Path,
    *,
    apply: bool = False,
    allow_verification: bool = False,
) -> Operation:
    """Plan or apply one deterministic invocation of an installed capability."""
    started = time.monotonic()
    root = repository_root(repository_path)
    candidate = _installed(root, capability_id)

    before = _read_base_state(root, candidate)
    before_content = {path: snapshot.content for path, snapshot in before.items()}
    after = apply_candidate(candidate, before_content, parameters)
    patch = render_patch(before_content, after)
    changed = {
        path: content
        for path, content in after.items()
        if content != before_content[path]
    }
    immutable_parameters = tuple(
        sorted((name, str(value)) for name, value in parameters.items())
    )
    operation_id = _operation_id(candidate, immutable_parameters, before, patch)

    def finish(*, applied: bool, verified: bool) -> Operation:
        return Operation(
            operation_id=operation_id,
            capability_id=candidate.capability_id,
            version=candidate.version,
            parameters=immutable_parameters,
            files=tuple(sorted(changed)),
            patch=patch,
            applied=applied,
            verified=verified,
            duration_ms=int((time.monotonic() - started) * 1000),
        )

    if not apply:
        return finish(applied=False, verified=False)
    if not allow_verification:
        raise CapabilityRefusal(
            "verification commands are disabled; review the operation and rerun with "
            "--allow-verification"
        )

    _write_through_temporaries(
        root,
        changed,
        expected={path: before[path] for path in changed},
        modes={path: before[path].mode for path in changed},
    )
    try:
        run_verification(candidate, parameters, root)
        observed = _read_base_state(root, candidate)
        expected_after = {
            path: FileSnapshot(content=after[path], mode=before[path].mode)
            for path in before
        }
        if observed != expected_after:
            raise CapabilityError("verification changed declared files")
    except CapabilityError as exc:
        try:
            _restore_base(root, before)
        except CapabilityError as rollback_error:
            raise CapabilityError(
                f"{exc}; unable to restore declared files: {rollback_error}"
            ) from exc
        raise
    return finish(applied=True, verified=True)

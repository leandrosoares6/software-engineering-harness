from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from .errors import GitError

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def _run_bytes(root: Path, *args: str, allow_failure: bool = False) -> tuple[int, bytes, bytes]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise GitError(f"unable to execute git: {exc}") from exc
    if result.returncode != 0 and not allow_failure:
        message = result.stderr.decode(errors="replace").strip()
        raise GitError(message or "git command failed")
    return result.returncode, result.stdout, result.stderr


def _run(root: Path, *args: str) -> str:
    _, stdout, _ = _run_bytes(root, *args)
    return stdout.decode(errors="strict")


def repository_root(path: Path) -> Path:
    candidate = path.resolve()
    root = _run(candidate, "rev-parse", "--show-toplevel").strip()
    return Path(root).resolve()


def assert_repo(root: Path) -> None:
    repository_root(root)


def tracked_files(root: Path) -> list[Path]:
    canonical_root = repository_root(root)
    raw = _run(canonical_root, "ls-files", "-z")
    return [canonical_root / item for item in raw.split("\0") if item]


def head(root: Path) -> str | None:
    canonical_root = repository_root(root)
    returncode, stdout, _ = _run_bytes(
        canonical_root,
        "rev-parse",
        "--verify",
        "HEAD",
        allow_failure=True,
    )
    if returncode != 0:
        return None
    return stdout.decode().strip()


def state_fingerprint(root: Path) -> str:
    canonical_root = repository_root(root)
    current_head = head(canonical_root)
    base = current_head or EMPTY_TREE
    _, diff, _ = _run_bytes(
        canonical_root,
        "diff",
        "--binary",
        "--no-ext-diff",
        "--no-textconv",
        base,
        "--",
    )
    digest = hashlib.sha256()
    digest.update((current_head or "UNBORN").encode())
    digest.update(b"\0")
    digest.update(diff)
    return digest.hexdigest()

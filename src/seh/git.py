from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


def _run(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or "git command failed")
    return result.stdout


def assert_repo(root: Path) -> None:
    _run(root, "rev-parse", "--show-toplevel")


def tracked_files(root: Path) -> list[Path]:
    raw = _run(root, "ls-files", "-z")
    return [root / item for item in raw.split("\0") if item]


def head(root: Path) -> str:
    return _run(root, "rev-parse", "HEAD").strip()

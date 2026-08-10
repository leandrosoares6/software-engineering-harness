from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SehConfig:
    root: Path
    state_dir: Path
    db_path: Path

    @classmethod
    def for_repo(cls, root: Path) -> "SehConfig":
        from .git import repository_root

        root = repository_root(root)
        state_dir = root / ".seh"
        return cls(root=root, state_dir=state_dir, db_path=state_dir / "seh.db")

    def ensure(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        (self.state_dir / "tasks").mkdir(exist_ok=True)
        (self.state_dir / "cache").mkdir(exist_ok=True)

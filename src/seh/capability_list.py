from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .capability import Candidate, load_candidate
from .capability_catalog import CATALOG_DIRECTORY
from .errors import CapabilityError
from .git import repository_root


@dataclass(frozen=True)
class Installed:
    capability_id: str
    version: int | None
    parameters: tuple[str, ...]
    problem: str | None


def installed_capabilities(repository_path: Path) -> list[Installed]:
    """Enumerate the catalogue, reporting unreadable entries instead of hiding them.

    An entry that fails to load is still listed, with its problem. Silently
    skipping it would make a broken capability indistinguishable from an absent
    one, which is the opposite of what a catalogue is for.
    """
    root = repository_root(repository_path)
    catalog = root / CATALOG_DIRECTORY
    if catalog.is_symlink():
        raise CapabilityError(f"capability catalogue must not be a symlink: {catalog}")
    if not catalog.is_dir():
        return []

    found: list[Installed] = []
    for entry in sorted(catalog.iterdir(), key=lambda item: item.name):
        if entry.name.startswith("."):
            continue
        if entry.is_symlink() or not entry.is_dir():
            found.append(Installed(entry.name, None, (), "not a directory"))
            continue
        try:
            candidate: Candidate = load_candidate(entry)
        except CapabilityError as exc:
            found.append(Installed(entry.name, None, (), str(exc)))
            continue
        mismatch = (
            "id does not match its directory"
            if candidate.capability_id != entry.name
            else None
        )
        found.append(
            Installed(
                candidate.capability_id,
                candidate.version,
                tuple(sorted(candidate.parameters)),
                mismatch,
            )
        )
    return found


def execute(args: argparse.Namespace) -> int:
    entries = installed_capabilities(Path(args.repo or "."))
    if not entries:
        print("No capabilities installed.")
        print("Install one with: seh capability install ./candidate --allow-verification")
        return 0

    width = max(len(entry.capability_id) for entry in entries)
    for entry in entries:
        version = f"v{entry.version}" if entry.version is not None else "-"
        parameters = ", ".join(entry.parameters) or "-"
        print(f"{entry.capability_id:{width}}  {version:>4}  {parameters}")
        if entry.problem:
            print(f"{'':{width}}  !!    {entry.problem}")
    return 0


def configure_parser(
    subcommands: argparse._SubParsersAction,
    handler: Callable[[argparse.Namespace], int],
) -> None:
    command = subcommands.add_parser(
        "list", help="enumerate the capabilities installed in this repository"
    )
    command.add_argument("--repo")
    command.set_defaults(handler=handler)

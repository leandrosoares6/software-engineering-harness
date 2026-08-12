"""Anchoring a capability's patches to facts outside the package.

A capability's strongest claim is that its fidelity case reproduces a change the
developer actually accepted. Until this module existed, that claim rested on two
author-supplied text files checked only against each other: `expected.patch` had
to be contained in `accepted.patch`, and both were editable. Editing them
together to suit a limitation of the templates produced a package that passed
every gate while misrepresenting history.

Two independent anchors close that:

`digest`      records each patch's sha256 in `scope.yaml`. It travels inside the
              package, needs no repository, and catches a patch edited without
              its record being updated. It is a consistency anchor, not a
              security boundary: whoever edits the patch can edit the digest.

`accepted_change` recomputes the accepted patch from the two commits
              `scope.yaml` names. That is ground truth, and it is the check a
              self-consistent forgery cannot survive. It needs the commits to
              still be reachable, so its outcome is reported as data rather than
              assumed.

The renderer here is the single implementation used both by `capability capture`
when it writes a package and by validation when it verifies one. Two renderers
would let the writer and the verifier drift until the check became vacuous.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .capability import render_patch
from .git import changed_files, file_at_commit, repository_root, resolve_commit


def digest(text: str) -> str:
    """The recorded sha256 of a patch, over its UTF-8 bytes."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AcceptedChange:
    """The full change between two commits, as bytes and as a rendered patch."""

    baseline: str
    accepted: str
    changed: list[str]
    before: dict[str, bytes]
    after: dict[str, bytes]
    patch: str


def _state(root: Path, commit: str, paths: list[str]) -> dict[str, bytes]:
    state: dict[str, bytes] = {}
    for path in paths:
        content = file_at_commit(root, commit, path)
        if content is not None:
            state[path] = content
    return state


def accepted_change(root: Path, baseline: str, accepted: str) -> AcceptedChange:
    """Render the accepted change between two commits.

    Both endpoints are historical facts read from Git, never reconstructed by
    subtracting from the current tree: ordering and surrounding bytes belong to
    the commit, not to the working copy.
    """
    base = resolve_commit(root, baseline)
    target = resolve_commit(root, accepted)
    changed = changed_files(root, base, target)
    before = _state(root, base, changed)
    after = _state(root, target, changed)
    return AcceptedChange(
        baseline=base,
        accepted=target,
        changed=changed,
        before=before,
        after=after,
        patch=render_patch(before, after),
    )


# Provenance outcomes. `verified` and `mismatch` are conclusions; the other two
# record why no conclusion was reachable, and must never read as equivalent to
# `verified`.
VERIFIED = "verified"
MISMATCH = "mismatch"
UNREACHABLE = "unreachable"
NOT_DECLARED = "not_declared"


@dataclass(frozen=True)
class ProvenanceResult:
    """Whether a package's accepted patch was confirmed against Git history."""

    status: str
    detail: str

    @property
    def contradicted(self) -> bool:
        """True only when history was reached and disagreed with the package."""
        return self.status == MISMATCH


def _patch_claims(patch: str) -> dict[str, tuple[list[str], list[str]]]:
    """Group a unified diff's added and removed lines by target path.

    Only line content is extracted, never hunk offsets or file headers. Offsets
    and headers are renderer-dependent — `git diff` writes `/dev/null` for a
    created file where `render_patch` writes `a/<path>` — and a check sensitive to
    those would fail on honest packages while catching no fabrication.
    """
    claims: dict[str, tuple[list[str], list[str]]] = {}
    path: str | None = None
    for line in patch.splitlines():
        if line.startswith("+++ "):
            target = line[4:].split("\t", 1)[0].strip()
            if target == "/dev/null":
                path = None
                continue
            path = target[2:] if target.startswith("b/") else target
            claims.setdefault(path, ([], []))
        elif line.startswith(("--- ", "@@", "diff --git ", "index ")):
            continue
        elif path is not None and line.startswith("+"):
            claims[path][0].append(line[1:])
        elif path is not None and line.startswith("-"):
            claims[path][1].append(line[1:])
    return claims


def verify_structural_claim(
    candidate_root: Path, baseline: str | None, accepted: str | None, expected: str
) -> ProvenanceResult:
    """Check the structural surface against the commits `scope.yaml` names.

    `expected.patch` is what the capability reproduces, so it carries the claim
    worth verifying: every line it adds must really be in the declared file at the
    accepted commit, and every line it removes must really have been there at the
    baseline. That is what the POC package violated — it claimed the developer
    accepted `help="TODO"` when the commit says `help="show status"` — and no
    amount of internal consistency can satisfy it.

    Two repositories are tried: the one containing the package, and the one the
    command was invoked from. A candidate written inside its project resolves via
    the first; one written to a scratch directory and validated from the project
    resolves via the second. Both are ordinary flows.

    Reports `unreachable` rather than failing when neither resolves the commits: a
    rebase, a squash-merge, a shallow clone or a package copied out of its origin
    repository all destroy reachability without implying dishonesty. That outcome
    is printed on every run, so a digest-only package cannot be mistaken for a
    history-verified one.
    """
    if not baseline or not accepted:
        return ProvenanceResult(
            NOT_DECLARED, "scope.yaml names no baseline and accepted commit pair"
        )
    claims = _patch_claims(expected)
    if not claims:
        return ProvenanceResult(
            NOT_DECLARED, "expected.patch claims no lines against any declared file"
        )
    reasons: list[str] = []
    for search_from in (candidate_root, Path.cwd()):
        try:
            root = repository_root(search_from)
            base = resolve_commit(root, baseline)
            target = resolve_commit(root, accepted)
        except Exception as exc:  # noqa: BLE001 - any Git failure means unreachable
            reasons.append(str(exc).splitlines()[0] if str(exc) else type(exc).__name__)
            continue
        span = f"{base[:12]}..{target[:12]}"
        for path, (added, removed) in sorted(claims.items()):
            for commit, lines, where in (
                (target, added, "added"),
                (base, removed, "removed"),
            ):
                if not lines:
                    continue
                blob = file_at_commit(root, commit, path)
                if blob is None:
                    return ProvenanceResult(
                        MISMATCH, f"{path} does not exist at {commit[:12]}"
                    )
                present = set(blob.decode("utf-8", "replace").splitlines())
                absent = [line for line in lines if line not in present]
                if absent:
                    return ProvenanceResult(
                        MISMATCH,
                        f"expected.patch {where} a line to {path} that is not in "
                        f"{commit[:12]}: {absent[0].strip()!r}",
                    )
        return ProvenanceResult(
            VERIFIED, f"expected.patch is consistent with {span} ({len(claims)} file/s)"
        )
    return ProvenanceResult(
        UNREACHABLE,
        f"{baseline[:12]}..{accepted[:12]} not reachable from the package or the "
        f"working directory ({'; '.join(reasons)}); patches are anchored by digest "
        "only",
    )

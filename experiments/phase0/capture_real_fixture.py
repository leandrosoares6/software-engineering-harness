from __future__ import annotations

import difflib
import hashlib
import re
import shutil
import subprocess
from pathlib import Path

import yaml

from seh.capability import apply_candidate, load_candidate


REPOSITORY = Path(__file__).resolve().parents[2]
ROOT = Path(__file__).parent / "real_capture/add-capability-subcommand"
TARGET = "src/seh/capability_cli.py"
BASELINE_COMMIT = "717e87797ec2623fa0ce8de1e3b7424db3f14777"
BASELINE_TREE = "f496004314c6f880f7dae4d7a7b6bcb50671da7c"
INSTALL_COMMIT = "abbb477cfb40671ec5a2f0d22e53be5dbea67248"
INSTALL_TREE = "9c9ce3fc7175184777cf95a3eed9998ed2a5fee5"
_HUNK_LABEL = re.compile(
    rb"^(@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@)[^\r\n]*$", re.MULTILINE
)


def _git(*args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(REPOSITORY), *args],
        check=True,
        capture_output=True,
    ).stdout


def _write(relative: str, content: str | bytes) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        path.write_bytes(content)


def _patch(before: dict[str, bytes], after: dict[str, bytes]) -> str:
    chunks: list[str] = []
    for path in sorted(set(before) | set(after)):
        chunks.extend(
            difflib.unified_diff(
                before.get(path, b"").decode().splitlines(keepends=True),
                after.get(path, b"").decode().splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )
    return "".join(chunks)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def capture() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    before_source = _git("show", f"{BASELINE_COMMIT}:{TARGET}")
    install_source = _git("show", f"{INSTALL_COMMIT}:{TARGET}")
    accepted_patch = _git(
        "diff", "--binary", "--no-ext-diff", BASELINE_COMMIT, INSTALL_COMMIT
    )
    target_git_patch = _git(
        "diff",
        "--no-ext-diff",
        BASELINE_COMMIT,
        INSTALL_COMMIT,
        "--",
        TARGET,
    )
    file_header = target_git_patch.index(f"--- a/{TARGET}\n".encode())
    expected_patch = _HUNK_LABEL.sub(rb"\1", target_git_patch[file_header:])

    manifest = f'''schema: seh.capability.phase0/v0.1
id: seh.add-capability-subcommand
version: 1

parameters:
  name:
    type: python_identifier

preconditions:
  - uses: text.absent
    with:
      file: {TARGET}
      value: "def cmd_{{{{ name }}}}("

steps:
  - uses: splice.after
    with:
      file: {TARGET}
      locator: python.symbol
      selector: last_with_prefix
      prefix: cmd_
      template: templates/handler.py.tmpl
  - uses: splice.before
    with:
      file: {TARGET}
      locator: python.statement
      function: configure_capability_parser
      statement: return
      lead: "\\n"
      template: templates/parser-registration.py.tmpl

verification:
  - uses: verify.command
    with:
      executable: python
      args: ["-m", "py_compile", "{TARGET}"]
      timeout_seconds: 30
      expected_exit: 0
'''
    handler = """def cmd_{{ name }}(args: argparse.Namespace) -> int:
    from .capability_{{ name }} import execute

    return execute(args)"""
    registration = """from .capability_{{ name }} import configure_parser as configure_{{ name }}_parser

configure_{{ name }}_parser(capability_subcommands, cmd_{{ name }})"""

    _write("capability.yaml", manifest)
    _write("templates/handler.py.tmpl", handler)
    _write("templates/parser-registration.py.tmpl", registration)
    _write(f"examples/fidelity/before/{TARGET}", before_source)
    _write(
        "examples/fidelity/case.yaml",
        yaml.safe_dump({"parameters": {"name": "install"}}, sort_keys=False),
    )
    _write("examples/fidelity/accepted.patch", accepted_patch)
    _write("examples/fidelity/expected.patch", expected_patch)

    excluded = [
        {
            "path": ".claude/PRPs/prds/seh-runtime-evidencia-medicao.prd.md",
            "reason": "product decision record, not recurring command wiring",
        },
        {"path": "README.md", "reason": "user documentation"},
        {
            "path": "docs/CAPABILITY_MODEL.md",
            "reason": "capability model documentation",
        },
        {"path": "docs/PHASE0_FINDINGS.md", "reason": "experiment findings"},
        {"path": "docs/ROADMAP.md", "reason": "roadmap state"},
        {
            "path": "src/seh/capability.py",
            "reason": "validator and capture-proof behavior, not subcommand wiring",
        },
        {
            "path": "src/seh/capability_catalog.py",
            "reason": "install domain behavior and atomic storage",
        },
        {
            "path": "src/seh/capability_install.py",
            "reason": "command-specific parser configuration, behavior, and presentation",
        },
        {
            "path": "src/seh/errors.py",
            "reason": "validation error transport",
        },
        {
            "path": "tests/test_capability.py",
            "reason": "validator verification, not generated product structure",
        },
        {
            "path": "tests/test_capability_install.py",
            "reason": "install verification, not generated product structure",
        },
    ]
    changed_paths = set(
        _git("diff", "--name-only", BASELINE_COMMIT, INSTALL_COMMIT)
        .decode()
        .splitlines()
    )
    assert changed_paths == {TARGET, *(item["path"] for item in excluded)}
    numstat = _git("diff", "--numstat", BASELINE_COMMIT, INSTALL_COMMIT).decode()
    accepted_insertions = sum(
        int(line.split("\t", 1)[0]) for line in numstat.splitlines()
    )
    accepted_deletions = sum(
        int(line.split("\t", 2)[1]) for line in numstat.splitlines()
    )
    expected_insertions = sum(
        line.startswith(b"+") and not line.startswith(b"+++")
        for line in expected_patch.splitlines()
    )

    scope = {
        "baseline": {"commit": BASELINE_COMMIT, "tree": BASELINE_TREE},
        "accepted": {"commit": INSTALL_COMMIT, "tree": INSTALL_TREE},
        "artifacts": {
            "before_sha256": _sha256(before_source),
            "accepted_patch_sha256": _sha256(accepted_patch),
            "expected_patch_sha256": _sha256(expected_patch),
        },
        "included": [
            {
                "path": TARGET,
                "hunks": 2,
                "reason": "two thin local-import adapters parameterized only by command name",
            }
        ],
        "excluded": excluded,
        "metrics": {
            "accepted_files": len(changed_paths),
            "accepted_insertions": accepted_insertions,
            "accepted_deletions": accepted_deletions,
            "structural_files": 1,
            "structural_insertions": expected_insertions,
            "structural_share_of_insertions": round(
                expected_insertions / accepted_insertions, 4
            ),
            "interpretation": (
                "value is navigation and shape reuse, not bulk code generation; measure "
                "reduced rediscovery and retries across repeated invocations"
            ),
        },
        "honesty_test": {
            "would_refactor_without_capture": (
                "yes; module-per-command separates growing command behavior from wiring "
                "even without the capability experiment"
            ),
            "why_validate_stays_inline": (
                "refactoring previously committed validate now would contaminate the "
                "historical install event"
            ),
            "why_no_file_render": (
                "the capability generates only existing-file wiring; command modules remain "
                "ordinary behavioral work until repeated file-creation evidence exists"
            ),
        },
    }
    _write("examples/fidelity/scope.yaml", yaml.safe_dump(scope, sort_keys=False))

    candidate = load_candidate(ROOT)
    fidelity_before = {TARGET: before_source}
    fidelity_after = apply_candidate(candidate, fidelity_before, {"name": "install"})
    assert _patch(fidelity_before, fidelity_after).encode() == expected_patch
    assert fidelity_after[TARGET] == install_source

    run_before = {TARGET: install_source}
    run_after = apply_candidate(candidate, run_before, {"name": "run"})
    _write("proposals/run.patch", _patch(run_before, run_after))


if __name__ == "__main__":
    capture()

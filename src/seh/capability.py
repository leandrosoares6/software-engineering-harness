from __future__ import annotations

import difflib
import keyword
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from .errors import CapabilityError, CapabilityRefusal
from .source_edit import (
    locate_last_function_with_prefix,
    locate_return_in_function,
    splice_after,
    splice_before,
)

SCHEMA = "seh.capability.phase0/v0.1"
MAX_FILE_BYTES = 1_048_576
MAX_FIXTURE_FILES = 100
SUPPORTED_STEPS = {"splice.after", "splice.before"}
_PLACEHOLDER = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")
_CAPABILITY_ID = re.compile(r"[a-z0-9][a-z0-9._-]*\Z")


@dataclass(frozen=True)
class Invocation:
    uses: str
    config: dict[str, Any]


@dataclass(frozen=True)
class Candidate:
    root: Path
    capability_id: str
    version: int
    parameters: dict[str, str]
    preconditions: tuple[Invocation, ...]
    steps: tuple[Invocation, ...]
    verification: tuple[Invocation, ...]


@dataclass(frozen=True)
class GateResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ValidationReport:
    capability_id: str
    gates: tuple[GateResult, ...]

    @property
    def passed(self) -> bool:
        return all(gate.passed for gate in self.gates)


@dataclass(frozen=True)
class Case:
    name: str
    parameters: dict[str, Any]
    before: dict[str, bytes]
    expected_patch: str | None
    approved: bool | None


def _read_limited(path: Path) -> bytes:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise CapabilityError(f"unable to read {path}: {exc}") from exc
    if size > MAX_FILE_BYTES:
        raise CapabilityError(f"file exceeds {MAX_FILE_BYTES} bytes: {path}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise CapabilityError(f"unable to read {path}: {exc}") from exc


def _safe_yaml(path: Path, label: str) -> Any:
    try:
        return yaml.safe_load(_read_limited(path))
    except yaml.YAMLError as exc:
        raise CapabilityError(f"invalid {label} YAML: {exc}") from exc


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise CapabilityError(f"{label} must be a mapping with string keys")
    return value


def _sequence(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise CapabilityError(f"{label} must be a list")
    return value


def _strict_keys(mapping: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise CapabilityError(f"{label} has unsupported fields: {', '.join(unknown)}")


def _relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise CapabilityError(f"{label} must be a non-empty relative path")
    if "\\" in value:
        raise CapabilityError(f"{label} must use normalized POSIX separators")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise CapabilityError(f"{label} must be a normalized relative path")
    return path.as_posix()


def _inside(root: Path, relative: str, label: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise CapabilityError(
            f"{label} must resolve inside the candidate package"
        ) from exc
    return path


def _invocations(value: Any, label: str, allowed: set[str]) -> tuple[Invocation, ...]:
    result: list[Invocation] = []
    for index, raw in enumerate(_sequence(value, label)):
        item = _mapping(raw, f"{label}[{index}]")
        _strict_keys(item, {"uses", "with"}, f"{label}[{index}]")
        uses = item.get("uses")
        if not isinstance(uses, str) or uses not in allowed:
            kind = "step" if label == "steps" else label.rstrip("s")
            raise CapabilityError(f"unsupported {kind} primitive: {uses!r}")
        config = _mapping(item.get("with"), f"{label}[{index}].with")
        result.append(Invocation(uses=uses, config=config))
    return tuple(result)


def _validate_precondition(invocation: Invocation, index: int) -> None:
    label = f"preconditions[{index}].with"
    _strict_keys(invocation.config, {"file", "value"}, label)
    _relative_path(invocation.config.get("file"), f"{label}.file")
    if not isinstance(invocation.config.get("value"), str):
        raise CapabilityError(f"{label}.value must be a string")


def _validate_step(candidate_root: Path, invocation: Invocation, index: int) -> None:
    label = f"steps[{index}].with"
    config = invocation.config
    if invocation.uses == "splice.after":
        allowed = {"file", "locator", "selector", "prefix", "template"}
        _strict_keys(config, allowed, label)
        if (
            config.get("locator") != "python.symbol"
            or config.get("selector") != "last_with_prefix"
        ):
            raise CapabilityError(f"{label} uses an unsupported splice.after locator")
        if not isinstance(config.get("prefix"), str) or not config["prefix"]:
            raise CapabilityError(f"{label}.prefix must be a non-empty string")
    else:
        allowed = {"file", "locator", "function", "statement", "lead", "template"}
        _strict_keys(config, allowed, label)
        if (
            config.get("locator") != "python.statement"
            or config.get("statement") != "return"
        ):
            raise CapabilityError(f"{label} uses an unsupported splice.before locator")
        if not isinstance(config.get("function"), str) or not config["function"]:
            raise CapabilityError(f"{label}.function must be a non-empty string")
        if not isinstance(config.get("lead", ""), str):
            raise CapabilityError(f"{label}.lead must be a string")
    _relative_path(config.get("file"), f"{label}.file")
    template = _relative_path(config.get("template"), f"{label}.template")
    template_path = _inside(candidate_root, template, f"{label}.template")
    if not template_path.is_file():
        raise CapabilityError(f"template does not exist: {template}")


def _validate_verification(invocation: Invocation, index: int) -> None:
    label = f"verification[{index}].with"
    config = invocation.config
    _strict_keys(
        config,
        {"executable", "args", "timeout_seconds", "expected_exit"},
        label,
    )
    if not isinstance(config.get("executable"), str) or not config["executable"]:
        raise CapabilityError(f"{label}.executable must be a non-empty string")
    args = config.get("args")
    if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
        raise CapabilityError(f"{label}.args must be a list of strings")
    timeout = config.get("timeout_seconds")
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, int)
        or not 1 <= timeout <= 300
    ):
        raise CapabilityError(
            f"{label}.timeout_seconds must be an integer from 1 to 300"
        )
    expected = config.get("expected_exit")
    if isinstance(expected, bool) or not isinstance(expected, int):
        raise CapabilityError(f"{label}.expected_exit must be an integer")


def load_candidate(path: Path) -> Candidate:
    root = path.resolve()
    if not root.is_dir():
        raise CapabilityError(f"capability candidate is not a directory: {path}")
    manifest_path = _inside(root, "capability.yaml", "capability manifest")
    if not manifest_path.is_file():
        raise CapabilityError(f"capability manifest not found: {manifest_path}")
    manifest = _mapping(_safe_yaml(manifest_path, "capability"), "capability manifest")
    _strict_keys(
        manifest,
        {
            "schema",
            "id",
            "version",
            "parameters",
            "preconditions",
            "steps",
            "verification",
        },
        "capability manifest",
    )
    if manifest.get("schema") != SCHEMA:
        raise CapabilityError(
            f"unsupported capability schema: {manifest.get('schema')!r}"
        )
    capability_id = manifest.get("id")
    if not isinstance(capability_id, str) or not _CAPABILITY_ID.fullmatch(
        capability_id
    ):
        raise CapabilityError("capability id is invalid")
    version = manifest.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise CapabilityError("capability version must be a positive integer")

    raw_parameters = _mapping(manifest.get("parameters"), "parameters")
    parameters: dict[str, str] = {}
    for name, raw_spec in raw_parameters.items():
        if not name.isidentifier() or keyword.iskeyword(name):
            raise CapabilityError(f"invalid parameter name: {name!r}")
        spec = _mapping(raw_spec, f"parameters.{name}")
        _strict_keys(spec, {"type"}, f"parameters.{name}")
        if spec.get("type") != "python_identifier":
            raise CapabilityError(f"unsupported parameter type: {spec.get('type')!r}")
        parameters[name] = "python_identifier"
    if not parameters:
        raise CapabilityError("candidate must declare at least one parameter")

    preconditions = _invocations(
        manifest.get("preconditions"), "preconditions", {"text.absent"}
    )
    steps = _invocations(manifest.get("steps"), "steps", SUPPORTED_STEPS)
    verification = _invocations(
        manifest.get("verification"), "verification", {"verify.command"}
    )
    if not preconditions or not steps or not verification:
        raise CapabilityError(
            "preconditions, steps, and verification must not be empty"
        )
    for index, invocation in enumerate(preconditions):
        _validate_precondition(invocation, index)
    for index, invocation in enumerate(steps):
        _validate_step(root, invocation, index)
    for index, invocation in enumerate(verification):
        _validate_verification(invocation, index)
    return Candidate(
        root=root,
        capability_id=capability_id,
        version=version,
        parameters=parameters,
        preconditions=preconditions,
        steps=steps,
        verification=verification,
    )


def _render(text: str, parameters: dict[str, Any], label: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in parameters:
            raise CapabilityError(f"{label} references undeclared parameter {name!r}")
        return str(parameters[name])

    rendered = _PLACEHOLDER.sub(replace, text)
    if "{{" in rendered or "}}" in rendered:
        raise CapabilityError(f"{label} contains an invalid template expression")
    return rendered


def _validate_parameters(candidate: Candidate, values: dict[str, Any]) -> None:
    if set(values) != set(candidate.parameters):
        missing = sorted(set(candidate.parameters) - set(values))
        extra = sorted(set(values) - set(candidate.parameters))
        detail = []
        if missing:
            detail.append(f"missing: {', '.join(missing)}")
        if extra:
            detail.append(f"unexpected: {', '.join(extra)}")
        raise CapabilityRefusal(f"invalid parameters ({'; '.join(detail)})")
    for name, kind in candidate.parameters.items():
        value = values[name]
        if kind == "python_identifier" and (
            not isinstance(value, str)
            or not value.isidentifier()
            or keyword.iskeyword(value)
        ):
            raise CapabilityRefusal(f"parameter {name!r} must be a python_identifier")


def _patch_hunks(patch: str, label: str) -> tuple[tuple[str, str], ...]:
    lines = patch.splitlines(keepends=True)
    hunks: list[tuple[str, str]] = []
    path: str | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("+++ "):
            path = line[4:].rstrip("\r\n").split("\t", 1)[0]
            index += 1
            continue
        if line.startswith("@@ "):
            if path is None:
                raise CapabilityError(f"{label} contains a hunk without a file")
            start = index
            index += 1
            while index < len(lines) and not (
                lines[index].startswith("@@ ")
                or lines[index].startswith("diff --git ")
                or lines[index].startswith("--- ")
            ):
                index += 1
            hunks.append((path, "".join(lines[start:index])))
            continue
        index += 1
    if not hunks:
        raise CapabilityError(f"{label} contains no unified-diff hunks")
    return tuple(hunks)


def _validate_patch_scope(case_root: Path, name: str, expected_patch: str) -> None:
    accepted_path = _inside(case_root, "accepted.patch", f"{name} accepted.patch")
    if not accepted_path.is_file():
        raise CapabilityError(f"missing {name} accepted.patch")
    scope_path = _inside(case_root, "scope.yaml", f"{name} scope.yaml")
    if not scope_path.is_file():
        raise CapabilityError(f"missing {name} scope.yaml")
    _mapping(_safe_yaml(scope_path, f"{name} scope"), f"{name} scope")
    try:
        accepted_patch = _read_limited(accepted_path).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CapabilityError(f"{name} accepted.patch is not UTF-8") from exc

    accepted_hunks = set(_patch_hunks(accepted_patch, f"{name} accepted.patch"))
    for hunk in _patch_hunks(expected_patch, f"{name} expected.patch"):
        if hunk not in accepted_hunks:
            raise CapabilityError(
                f"{name} expected.patch hunk is not contained in accepted.patch"
            )


def _load_case(candidate: Candidate, name: str, *, expected: bool) -> Case:
    relative_root = f"examples/{name}"
    _inside(candidate.root, relative_root, f"{name} case")
    case_path = _inside(candidate.root, f"{relative_root}/case.yaml", f"{name} case")
    if not case_path.is_file():
        raise CapabilityError(f"missing {name} case: {case_path}")
    raw = _mapping(_safe_yaml(case_path, f"{name} case"), f"{name} case")
    _strict_keys(raw, {"parameters", "approved"}, f"{name} case")
    parameters = _mapping(raw.get("parameters"), f"{name} parameters")
    before_root = _inside(
        candidate.root, f"{relative_root}/before", f"{name} before fixture"
    )
    if not before_root.is_dir():
        raise CapabilityError(f"missing {name} before fixture")
    paths = _fixture_paths(before_root, name)
    before: dict[str, bytes] = {}
    for path in paths:
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(before_root.resolve()).as_posix()
        except ValueError as exc:
            raise CapabilityError(
                f"{name} fixture contains a path outside before/"
            ) from exc
        before[relative] = _read_limited(resolved)
    if not before:
        raise CapabilityError(f"{name} before fixture is empty")
    expected_patch: str | None = None
    if expected:
        patch_path = _inside(
            candidate.root, f"{relative_root}/expected.patch", f"{name} expected.patch"
        )
        if not patch_path.is_file():
            raise CapabilityError(f"missing {name} expected.patch")
        try:
            expected_patch = _read_limited(patch_path).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CapabilityError(f"{name} expected.patch is not UTF-8") from exc
        _validate_patch_scope(case_path.parent, name, expected_patch)
    approved = raw.get("approved")
    if approved is not None and not isinstance(approved, bool):
        raise CapabilityError(f"{name} approved must be boolean")
    return Case(name, parameters, before, expected_patch, approved)


def _fixture_paths(root: Path, name: str) -> list[Path]:
    paths: list[Path] = []
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    if entry.is_symlink():
                        raise CapabilityError(
                            f"{name} fixture symlinks are not supported: {path}"
                        )
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(path)
                    elif entry.is_file(follow_symlinks=False):
                        paths.append(path)
                        if len(paths) > MAX_FIXTURE_FILES:
                            raise CapabilityError(
                                f"{name} fixture exceeds {MAX_FIXTURE_FILES} files"
                            )
        except CapabilityError:
            raise
        except OSError as exc:
            raise CapabilityError(f"unable to enumerate {name} fixture: {exc}") from exc
    return sorted(paths)


def _target(
    state: dict[str, bytes], config: dict[str, Any], label: str
) -> tuple[str, bytes]:
    path = _relative_path(config.get("file"), f"{label}.file")
    if path not in state:
        raise CapabilityRefusal(f"declared file is absent from fixture: {path}")
    return path, state[path]


def _template(
    candidate: Candidate, config: dict[str, Any], parameters: dict[str, Any]
) -> bytes:
    relative = _relative_path(config.get("template"), "step template")
    path = _inside(candidate.root, relative, "step template")
    try:
        text = _read_limited(path).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CapabilityError(f"template is not UTF-8: {relative}") from exc
    return _render(text, parameters, relative).encode()


def apply_candidate(
    candidate: Candidate, before: dict[str, bytes], parameters: dict[str, Any]
) -> dict[str, bytes]:
    _validate_parameters(candidate, parameters)
    state = dict(before)
    for index, invocation in enumerate(candidate.preconditions):
        path, source = _target(state, invocation.config, f"preconditions[{index}]")
        value = _render(
            invocation.config["value"], parameters, f"preconditions[{index}]"
        )
        if value.encode() in source:
            raise CapabilityRefusal(
                f"precondition failed: {value!r} already exists in {path}"
            )

    for index, invocation in enumerate(candidate.steps):
        path, source = _target(state, invocation.config, f"steps[{index}]")
        fragment = _template(candidate, invocation.config, parameters)
        if invocation.uses == "splice.after":
            anchor = locate_last_function_with_prefix(
                source, invocation.config["prefix"]
            )
            state[path] = splice_after(source, anchor, fragment)
        elif invocation.uses == "splice.before":
            anchor = locate_return_in_function(source, invocation.config["function"])
            lead = invocation.config.get("lead", "").encode()
            state[path] = splice_before(source, anchor, fragment, lead=lead)
        else:  # load_candidate makes this unreachable; retain fail-closed behavior.
            raise CapabilityError(f"unsupported step primitive: {invocation.uses!r}")
    return state


def _patch(before: dict[str, bytes], after: dict[str, bytes]) -> str:
    chunks: list[str] = []
    for path in sorted(set(before) | set(after)):
        old = before.get(path, b"")
        new = after.get(path, b"")
        try:
            old_lines = old.decode("utf-8").splitlines(keepends=True)
            new_lines = new.decode("utf-8").splitlines(keepends=True)
        except UnicodeDecodeError as exc:
            raise CapabilityError(
                f"cannot render patch for non-UTF-8 file: {path}"
            ) from exc
        chunks.extend(
            difflib.unified_diff(
                old_lines, new_lines, fromfile=f"a/{path}", tofile=f"b/{path}"
            )
        )
    return "".join(chunks)


def _verify(
    candidate: Candidate, state: dict[str, bytes], parameters: dict[str, Any]
) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for relative, content in state.items():
            path = _inside(
                root, _relative_path(relative, "fixture file"), "fixture file"
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        for index, invocation in enumerate(candidate.verification):
            config = invocation.config
            executable = _render(
                config["executable"], parameters, f"verification[{index}]"
            )
            args = [
                _render(arg, parameters, f"verification[{index}]")
                for arg in config["args"]
            ]
            try:
                result = subprocess.run(
                    [executable, *args],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    shell=False,
                    timeout=config["timeout_seconds"],
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise CapabilityRefusal(
                    f"verification command timed out after {config['timeout_seconds']}s"
                ) from exc
            except OSError as exc:
                raise CapabilityRefusal(
                    f"unable to execute verification command: {exc}"
                ) from exc
            if result.returncode != config["expected_exit"]:
                detail = (result.stderr or result.stdout).strip()
                suffix = f": {detail}" if detail else ""
                raise CapabilityRefusal(
                    f"verification command exited {result.returncode}; "
                    f"expected {config['expected_exit']}{suffix}"
                )


def _reproduction_gate(candidate: Candidate, case: Case) -> GateResult:
    if case.name == "generalization" and case.approved is not True:
        return GateResult(
            case.name, False, "generalization case is not developer-approved"
        )
    try:
        after = apply_candidate(candidate, case.before, case.parameters)
        actual = _patch(case.before, after)
        if actual != case.expected_patch:
            return GateResult(
                case.name, False, "generated patch differs from expected.patch"
            )
        _verify(candidate, after, case.parameters)
    except CapabilityError as exc:
        return GateResult(case.name, False, str(exc))
    return GateResult(case.name, True, "patch and verification match")


def _idempotency_gate(candidate: Candidate, case: Case) -> GateResult:
    try:
        once = apply_candidate(candidate, case.before, case.parameters)
        try:
            twice = apply_candidate(candidate, once, case.parameters)
        except CapabilityRefusal:
            return GateResult(
                "idempotency", True, "second application refused explicitly"
            )
        if twice == once:
            return GateResult("idempotency", True, "second application is a no-op")
        return GateResult(
            "idempotency", False, "second application changed the fixture"
        )
    except CapabilityError as exc:
        return GateResult("idempotency", False, str(exc))


def _refusal_gate(candidate: Candidate, case: Case) -> GateResult:
    original = dict(case.before)
    try:
        apply_candidate(candidate, case.before, case.parameters)
    except CapabilityRefusal as exc:
        if case.before != original:
            return GateResult(
                "safe_refusal", False, "refusal mutated the input fixture"
            )
        return GateResult("safe_refusal", True, str(exc))
    except CapabilityError as exc:
        return GateResult(
            "safe_refusal", False, f"candidate error is not a safe refusal: {exc}"
        )
    return GateResult("safe_refusal", False, "incompatible fixture was accepted")


def validate_candidate(
    path: Path, *, allow_verification: bool = False
) -> ValidationReport:
    if not allow_verification:
        raise CapabilityError(
            "verification commands are disabled; review the candidate and rerun with "
            "--allow-verification"
        )
    candidate = load_candidate(path)
    fidelity = _load_case(candidate, "fidelity", expected=True)
    generalization = _load_case(candidate, "generalization", expected=True)
    refusal = _load_case(candidate, "refusal", expected=False)
    gates = (
        _reproduction_gate(candidate, fidelity),
        _reproduction_gate(candidate, generalization),
        _idempotency_gate(candidate, fidelity),
        _refusal_gate(candidate, refusal),
    )
    return ValidationReport(candidate.capability_id, gates)

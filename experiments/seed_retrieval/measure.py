"""Can the text of a request find which earlier change matters?

Phase 0.5 measured that the opportunity is abundant: the fraction of a commit's
files that some earlier commit already touched has a median of 1.00. What it
could not measure is retrieval, and that is where the whole product risk now
sits. This script measures it, offline, from `git log` alone.

For each target commit, its own subject is used as the prompt, the index is
truncated to commits that predate it, priors are ranked by IDF-weighted term
overlap of their subjects, and the top-K are scored on how much of the target's
region they cover. Using the literal subject is deliberate: a real request is a
paraphrase and matches worse, so this measures the ceiling of the mechanism in
PRD §10.2. A ceiling that fails needs no implementation to be refuted.

Targets are split into two classes before any statistic is computed. When a term
of the subject already appears in one of the target's own paths, retrieval is
identifier matching — the easy case of §10.1, a grep with extra steps. The hard
class, where no term appears, is the one §5 uses to justify the product, and it
is the only one that decides.

Design, thresholds and predictions are fixed in PRE_REGISTRATION.md, committed
before this file existed.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "region_recurrence"))

from measure import (  # noqa: E402
    DEFAULT_EXCLUDES,
    DEFAULT_EXTENSIONS,
    DAY,
    Commit,
    MeasurementError,
    _git,
    read_commits,
    select,
)

K_VALUES = (1, 3, 5, 10)
K_DECISIVE = 5

NOISE = frozenset(
    """
    feat fix docs chore refactor test tests perf build ci style revert
    maint mnt enh tst bug doc mrg api wip merge bump release version
    """.split()
)

STOPWORDS = frozenset(
    """
    the and for with from that this into when only not but are was were
    para com que dos das uma umas uns por pelo pela nos nas sem sobre
    add adds added remove removes removed update updates updated use uses used
    make makes made allow allows fix fixes fixed support new old all any
    """.split()
)


@dataclass
class Scored:
    """One target, with every ranking's outcome already reduced to a number."""

    sha: str
    subject: str
    size: int
    hard: bool
    oracle: float
    top: dict[str, dict[int, float]] = field(default_factory=dict)
    best_prior_sha: str = ""
    best_prior_subject: str = ""


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def tokenize(subject: str) -> frozenset[str]:
    """Domain terms of a commit subject, with conventional noise removed.

    Accents are stripped so a Portuguese subject tokenizes stably; tokens shorter
    than three characters, pure digits (PR numbers), commit-type prefixes and
    stopwords are dropped because they match everything and carry no domain.
    """
    tokens: set[str] = set()
    current: list[str] = []
    for char in normalize(subject):
        if char.isalnum():
            current.append(char)
            continue
        if current:
            tokens.add("".join(current))
            current = []
    if current:
        tokens.add("".join(current))
    return frozenset(
        token
        for token in tokens
        if len(token) >= 3
        and not token.isdigit()
        and token not in NOISE
        and token not in STOPWORDS
    )


def is_hard(subject_tokens: frozenset[str], paths: frozenset[str]) -> bool:
    """True when no term of the subject occurs in any of the target's own paths.

    This is the case that requires domain-to-code translation, and the coarse
    substring test pushes ambiguous targets into the easy class, which shrinks
    the deciding sample rather than inflating it.
    """
    blob = normalize(" ".join(paths))
    return not any(token in blob for token in subject_tokens)


def _containment(target: frozenset[str], priors: list[Commit]) -> tuple[float, int]:
    best, best_index = 0.0, -1
    for position, prior in enumerate(priors):
        score = len(target & prior.files) / len(target)
        if score > best:
            best, best_index = score, position
    return best, best_index


def analyze(
    commits: list[Commit],
    cooldown_days: float,
    min_target_files: int,
    seed: int,
) -> list[Scored]:
    rng = random.Random(seed)
    cooldown = cooldown_days * DAY

    file_index: dict[str, list[int]] = {}
    term_index: dict[str, list[int]] = {}
    document_frequency: Counter[str] = Counter()
    tokens_of: list[frozenset[str]] = [tokenize(commit.subject) for commit in commits]
    admitted: list[int] = []
    frontier = 0

    results: list[Scored] = []

    for position, target in enumerate(commits):
        while (
            frontier < position
            and commits[frontier].timestamp <= target.timestamp - cooldown
        ):
            for path in commits[frontier].files:
                file_index.setdefault(path, []).append(frontier)
            for token in tokens_of[frontier]:
                term_index.setdefault(token, []).append(frontier)
                document_frequency[token] += 1
            admitted.append(frontier)
            frontier += 1

        if len(target.files) < min_target_files or not admitted:
            continue

        size = len(target.files)
        counts: Counter[int] = Counter()
        for path in target.files:
            for candidate in file_index.get(path, ()):
                counts[candidate] += 1
        if not counts:
            continue
        oracle_index = max(counts.items(), key=lambda item: (item[1], item[0]))[0]
        oracle = counts[oracle_index] / size

        query = tokens_of[position]
        total = len(admitted)
        idf_scores: Counter[int] = Counter()
        plain_scores: Counter[int] = Counter()
        for token in query:
            postings = term_index.get(token)
            if not postings:
                continue
            weight = math.log(total / (1 + document_frequency[token]))
            if weight <= 0:
                continue
            for candidate in postings:
                idf_scores[candidate] += weight
                plain_scores[candidate] += 1

        rankings: dict[str, list[int]] = {
            "idf": [
                index
                for index, _ in sorted(
                    idf_scores.items(), key=lambda item: (-item[1], -item[0])
                )
            ],
            "plain": [
                index
                for index, _ in sorted(
                    plain_scores.items(), key=lambda item: (-item[1], -item[0])
                )
            ],
            "recency": admitted[::-1],
            "random": rng.sample(admitted, min(len(admitted), max(K_VALUES))),
        }

        scored = Scored(
            sha=target.sha,
            subject=target.subject,
            size=size,
            hard=is_hard(query, target.files),
            oracle=oracle,
        )
        for name, ranked in rankings.items():
            scored.top[name] = {}
            for k in K_VALUES:
                chosen = [commits[index] for index in ranked[:k]]
                value, which = _containment(target.files, chosen)
                scored.top[name][k] = value
                if name == "idf" and k == K_DECISIVE and which >= 0:
                    scored.best_prior_sha = chosen[which].sha
                    scored.best_prior_subject = chosen[which].subject
        results.append(scored)

    return results


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _capture(rows: list[Scored], name: str, k: int) -> list[float]:
    return [row.top[name][k] / row.oracle for row in rows if row.oracle > 0]


def render(root: Path, head: str, params: dict[str, object], rows: list[Scored]) -> str:
    lines: list[str] = []
    out = lines.append

    out("# Seed retrieval — can the request text find the right prior?")
    out("")
    out(f"- repository: `{root}`")
    out(f"- HEAD: `{head}`")
    for key, value in params.items():
        out(f"- {key}: `{value}`")
    out("")

    hard = [row for row in rows if row.hard]
    easy = [row for row in rows if not row.hard]
    out("## Sample")
    out("")
    out(f"- targets scored: **{len(rows)}**")
    out(f"- **hard class** (no subject term in the target's own paths): **{len(hard)}**"
        f" ({len(hard) / len(rows):.1%})" if rows else "- no targets")
    out(f"- easy class (identifier match available): {len(easy)}")
    out("")
    if rows and len(hard) / len(rows) < 0.15:
        out(
            "> **Warning, pre-registered.** The hard class is under 15% of the sample, "
            "so the deciding statistic rests on few targets and is noisy. Reported "
            "rather than hidden."
        )
        out("")

    if not hard:
        out("No hard-class target. Nothing decisive can be read from this repository.")
        return "\n".join(lines)

    out(f"## Decisive — hard class, K = {K_DECISIVE}, IDF ranking")
    out("")
    out("| quantity | median |")
    out("| --- | --- |")
    out(f"| oracle containment (all priors) | {_median([r.oracle for r in hard]):.2f} |")
    out(
        f"| top-{K_DECISIVE} containment | "
        f"{_median([r.top['idf'][K_DECISIVE] for r in hard]):.2f} |"
    )
    out(
        f"| **capture = top-{K_DECISIVE} ÷ oracle** | "
        f"**{_median(_capture(hard, 'idf', K_DECISIVE)):.2f}** |"
    )
    out("")

    idf_capture = _median(_capture(hard, "idf", K_DECISIVE))
    out("### Against the nulls, same class and K")
    out("")
    out("| ranking | median capture | margin over IDF |")
    out("| --- | --- | --- |")
    for name, label in (
        ("idf", "IDF-weighted overlap (primary)"),
        ("plain", "plain term overlap (secondary)"),
        ("recency", "recency-K (the cheap product)"),
        ("random", "random-K (floor)"),
    ):
        value = _median(_capture(hard, name, K_DECISIVE))
        margin = "—" if name == "idf" else f"{(idf_capture - value) * 100:+.1f} pp"
        out(f"| {label} | {value:.2f} | {margin} |")
    out("")
    out(
        "The margin over **recency-K** is the one that decides. It is the version of "
        "the product that needs no index, no prompt and no resolver: look at the last "
        "few commits. Not clearly beating it refutes §10.2 regardless of the absolute "
        "value."
    )
    out("")

    out("## Sensitivity to K")
    out("")
    out("| K | IDF capture (hard) | recency capture (hard) | IDF capture (easy) |")
    out("| --- | --- | --- | --- |")
    for k in K_VALUES:
        out(
            f"| {k} | {_median(_capture(hard, 'idf', k)):.2f} "
            f"| {_median(_capture(hard, 'recency', k)):.2f} "
            f"| {_median(_capture(easy, 'idf', k)):.2f} |"
        )
    out("")

    out("## Easy class, for contrast")
    out("")
    out(
        f"- capture at K = {K_DECISIVE}: "
        f"**{_median(_capture(easy, 'idf', K_DECISIVE)):.2f}**"
    )
    out(
        "- If the easy class scores well and the hard class does not, the mechanism is "
        "identifier matching (§10.1) and the product is a grep."
    )
    out("")

    out("## Hard-class targets where retrieval worked")
    out("")
    ranked = sorted(hard, key=lambda r: (-r.top["idf"][K_DECISIVE], -r.size))[:8]
    out("| capture | files | target | retrieved prior |")
    out("| --- | --- | --- | --- |")
    for row in ranked:
        capture = row.top["idf"][K_DECISIVE] / row.oracle if row.oracle else 0.0
        out(
            f"| {capture:.2f} | {row.size} | {row.subject[:52]} "
            f"| {row.best_prior_subject[:52]} |"
        )
    out("")

    out("## Hard-class targets where it failed")
    out("")
    misses = sorted(hard, key=lambda r: (r.top["idf"][K_DECISIVE], -r.size))[:8]
    out("| capture | oracle | files | target |")
    out("| --- | --- | --- | --- |")
    for row in misses:
        capture = row.top["idf"][K_DECISIVE] / row.oracle if row.oracle else 0.0
        out(f"| {capture:.2f} | {row.oracle:.2f} | {row.size} | {row.subject[:60]} |")
    out("")
    out(
        "Read both lists before the tables. The failures say whether the mechanism "
        "misses randomly or misses a recognizable kind of task."
    )

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--since", default=None)
    parser.add_argument("--until", default=None)
    parser.add_argument("--extensions", default=DEFAULT_EXTENSIONS)
    parser.add_argument("--exclude", action="append", default=None)
    parser.add_argument("--max-files", type=int, default=50)
    parser.add_argument("--min-target-files", type=int, default=4)
    parser.add_argument("--cooldown-days", type=float, default=30.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    root = args.repo.resolve()
    extensions = tuple(
        item.strip() for item in args.extensions.split(",") if item.strip()
    )
    excludes = tuple(args.exclude) if args.exclude is not None else DEFAULT_EXCLUDES

    try:
        head = _git(root, "rev-parse", "HEAD").decode().strip()
        commits = read_commits(root, args.since, args.until)
        pool, _ = select(commits, extensions, excludes, 1, args.max_files)
        rows = analyze(pool, args.cooldown_days, args.min_target_files, args.seed)
    except MeasurementError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    params = {
        "pool commits": len(pool),
        "min_target_files": args.min_target_files,
        "max_files": args.max_files,
        "cooldown_days": args.cooldown_days,
        "K decisive": K_DECISIVE,
        "seed": args.seed,
        "since": args.since or "(repository start)",
    }
    print(render(root, head, params, rows))

    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "repository": str(root),
                    "head": head,
                    "parameters": params,
                    "targets": [
                        {**vars(row), "top": {k: v for k, v in row.top.items()}}
                        for row in rows
                    ],
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

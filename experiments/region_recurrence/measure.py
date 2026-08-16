"""Field measurement: how often does a commit's file region repeat an earlier one?

The capability result killed *procedure identity* — the same mechanical wiring
recurring — at 3 events in 5 months. A context record needs something weaker:
that a new change lands in a region some earlier change already visited. This
script measures that weaker property directly from `git log`, on any repository,
before a resolver exists to be argued about.

Primary quantity, for each target commit A:

    containment(A) = max over eligible prior commits B of  |A n B| / |A|

"How much of this change's region had already been visited by one earlier
change?" A record written after B would have pointed at that fraction of A.

Two null models run alongside it, both computed from the prefix only, so
neither reads the future:

  * hot-k    — the k most frequently touched files so far, k sized to one
               commit. If a static list of hot files scores like the best
               prior commit, recurrence carries no information and no
               resolver is worth building.
  * random   — a random eligible prior commit, the floor.

Nothing here is a product. It is descriptive, stdlib-only, and reports the
distribution rather than a single mean.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import random
import statistics
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

DEFAULT_EXTENSIONS = (
    ".py,.js,.jsx,.ts,.tsx,.vue,.svelte,.go,.rb,.java,.kt,.kts,.rs,.php,"
    ".cs,.swift,.scala,.ex,.exs,.sql,.c,.h,.cc,.cpp,.hpp,.m,.mm"
)

DEFAULT_EXCLUDES = (
    "*/migrations/*",
    "*/node_modules/*",
    "*/vendor/*",
    "*_pb2.py",
    "*.generated.*",
    "*.min.js",
)

SIZE_BUCKETS = ((1, 1), (2, 3), (4, 7), (8, 15), (16, 10**9))

CONTAINMENT_BUCKETS = ((0.0, 0.25), (0.25, 0.5), (0.5, 0.8), (0.8, 1.0), (1.0, 1.01))

DAY = 86400


class MeasurementError(RuntimeError):
    """The repository or the parameters cannot support an honest measurement."""


@dataclass(frozen=True)
class Commit:
    sha: str
    timestamp: int
    author: str
    subject: str
    files: frozenset[str]


@dataclass
class TargetResult:
    sha: str
    timestamp: int
    subject: str
    size: int
    best_containment: float
    best_prior_sha: str
    best_prior_subject: str
    lag_days: float
    lag_commits: int
    union_containment: float
    hot_containment: float
    random_containment: float


def _git(root: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise MeasurementError(f"unable to execute git: {exc}") from exc
    if result.returncode != 0:
        message = result.stderr.decode(errors="replace").strip()
        raise MeasurementError(message or "git command failed")
    return result.stdout


def read_commits(root: Path, since: str | None, until: str | None) -> list[Commit]:
    """Every non-merge commit with its changed paths, oldest first.

    Records are framed with control characters rather than newlines because a
    path may contain almost anything else. `%s` is guaranteed single-line by
    git, which is what lets the header be split off at the first newline.
    """
    args = [
        "log",
        "--no-merges",
        "--reverse",
        "--no-renames",
        "--pretty=format:%x01%H%x1f%at%x1f%aN%x1f%s",
        "--name-only",
        "-z",
    ]
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")
    raw = _git(root, *args).decode("utf-8", errors="replace")

    commits: list[Commit] = []
    for chunk in raw.split("\x01")[1:]:
        header, _, tail = chunk.partition("\n")
        fields = header.split("\x1f", 3)
        if len(fields) != 4:
            raise MeasurementError(f"unparseable log header: {header!r}")
        sha, timestamp, author, subject = fields
        files = frozenset(path for path in tail.split("\0") if path)
        commits.append(
            Commit(
                sha=sha,
                timestamp=int(timestamp),
                author=author,
                subject=subject,
                files=files,
            )
        )
    commits.sort(key=lambda commit: (commit.timestamp, commit.sha))
    return commits


def _keep_path(path: str, extensions: tuple[str, ...], excludes: tuple[str, ...]) -> bool:
    if any(fnmatch.fnmatch(path, pattern) for pattern in excludes):
        return False
    if not extensions:
        return True
    return path.endswith(extensions)


def select(
    commits: list[Commit],
    extensions: tuple[str, ...],
    excludes: tuple[str, ...],
    min_files: int,
    max_files: int,
) -> tuple[list[Commit], dict[str, int]]:
    """Commits reduced to their in-scope paths, with the exclusion tally.

    A commit above `max_files` is dropped as target *and* as candidate: a
    repository-wide rename would trivially contain every later change and
    manufacture recurrence that no record could have predicted.
    """
    kept: list[Commit] = []
    tally = {"empty_after_path_filter": 0, "below_min_files": 0, "above_max_files": 0}
    for commit in commits:
        files = frozenset(
            path for path in commit.files if _keep_path(path, extensions, excludes)
        )
        if not files:
            tally["empty_after_path_filter"] += 1
            continue
        if len(files) < min_files:
            tally["below_min_files"] += 1
            continue
        if len(files) > max_files:
            tally["above_max_files"] += 1
            continue
        kept.append(
            Commit(
                sha=commit.sha,
                timestamp=commit.timestamp,
                author=commit.author,
                subject=commit.subject,
                files=files,
            )
        )
    return kept, tally


def _greedy_union(
    target: frozenset[str],
    index: dict[str, list[int]],
    priors: list[Commit],
    depth: int,
) -> float:
    """Best coverage of the target by up to `depth` prior commits, greedily."""
    uncovered = set(target)
    for _ in range(depth):
        counts: Counter[int] = Counter()
        for path in uncovered:
            for prior in index.get(path, ()):
                counts[prior] += 1
        if not counts:
            break
        best = max(counts.items(), key=lambda item: (item[1], item[0]))[0]
        uncovered -= priors[best].files
        if not uncovered:
            break
    return (len(target) - len(uncovered)) / len(target)


def analyze(
    commits: list[Commit],
    cooldown_days: float,
    union_depth: int,
    hot_k: int,
    seed: int,
) -> tuple[list[TargetResult], int]:
    """Containment of every target against the prefix that predates its cooldown.

    The cooldown is the load-bearing control. Consecutive commits from one piece
    of work are not a recurrence — `PHASE0_FINDINGS.md` records that mistake in
    its structural form. Only commits at least `cooldown_days` older are
    admitted as candidates.
    """
    rng = random.Random(seed)
    cooldown = cooldown_days * DAY

    index: dict[str, list[int]] = {}
    hotness: Counter[str] = Counter()
    admitted: list[int] = []
    frontier = 0

    results: list[TargetResult] = []
    without_prior = 0

    for position, target in enumerate(commits):
        while (
            frontier < position
            and commits[frontier].timestamp <= target.timestamp - cooldown
        ):
            prior = commits[frontier]
            for path in prior.files:
                index.setdefault(path, []).append(frontier)
                hotness[path] += 1
            admitted.append(frontier)
            frontier += 1

        if not admitted:
            without_prior += 1
            continue

        counts: Counter[int] = Counter()
        for path in target.files:
            for candidate in index.get(path, ()):
                counts[candidate] += 1

        size = len(target.files)
        if counts:
            best = max(counts.items(), key=lambda item: (item[1], item[0]))[0]
            best_commit = commits[best]
            best_containment = counts[best] / size
            lag_days = (target.timestamp - best_commit.timestamp) / DAY
            lag_commits = position - best
            best_sha, best_subject = best_commit.sha, best_commit.subject
        else:
            best_containment, lag_days, lag_commits = 0.0, 0.0, 0
            best_sha, best_subject = "", ""

        budget = hot_k or max(
            1, int(statistics.median(len(commits[i].files) for i in admitted))
        )
        hot = {path for path, _ in sorted(hotness.items(), key=lambda i: (-i[1], i[0]))[:budget]}
        chance = commits[rng.choice(admitted)]

        results.append(
            TargetResult(
                sha=target.sha,
                timestamp=target.timestamp,
                subject=target.subject,
                size=size,
                best_containment=best_containment,
                best_prior_sha=best_sha,
                best_prior_subject=best_subject,
                lag_days=lag_days,
                lag_commits=lag_commits,
                union_containment=_greedy_union(
                    target.files, index, commits, union_depth
                ),
                hot_containment=len(target.files & hot) / size,
                random_containment=len(target.files & chance.files) / size,
            )
        )

    return results, without_prior


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _share(values: list[float], threshold: float) -> float:
    return sum(v >= threshold for v in values) / len(values) if values else 0.0


def render(
    root: Path,
    head: str,
    params: dict[str, object],
    total: int,
    tally: dict[str, int],
    eligible: int,
    results: list[TargetResult],
    without_prior: int,
) -> str:
    best = [r.best_containment for r in results]
    lines: list[str] = []
    out = lines.append

    out("# Region recurrence — field measurement")
    out("")
    out(f"- repository: `{root}`")
    out(f"- HEAD: `{head}`")
    for key, value in params.items():
        out(f"- {key}: `{value}`")
    out("")

    out("## Scope")
    out("")
    out(f"- non-merge commits read: **{total}**")
    for reason, count in tally.items():
        out(f"- excluded, {reason.replace('_', ' ')}: {count}")
    out(f"- eligible commits: **{eligible}**")
    out(f"- targets with no prior outside the cooldown: {without_prior}")
    out(f"- targets measured: **{len(results)}**")
    out("")

    if not results:
        out("No target had an eligible prior. Widen the window or the filters.")
        return "\n".join(lines)

    out("## Primary — containment by the single best prior commit")
    out("")
    out("| containment | targets | share |")
    out("| --- | --- | --- |")
    for low, high in CONTAINMENT_BUCKETS:
        count = sum(low <= value < high for value in best)
        label = "= 1.00" if low == 1.0 else f"[{low:.2f}, {high:.2f})"
        out(f"| {label} | {count} | {count / len(best):.1%} |")
    out("")
    out(f"- median: **{_median(best):.2f}**")
    out(f"- share >= 0.50: **{_share(best, 0.5):.1%}**")
    out(f"- share >= 0.80: **{_share(best, 0.8):.1%}**")
    out(f"- share = 1.00: **{_share(best, 1.0):.1%}**")
    out("")

    out("## Against the null models")
    out("")
    out("| model | median | >= 0.50 | >= 0.80 |")
    out("| --- | --- | --- | --- |")
    for label, values in (
        ("best prior commit", best),
        (
            f"union of up to {params['union_depth']} priors",
            [r.union_containment for r in results],
        ),
        ("hot-k static list", [r.hot_containment for r in results]),
        ("random prior commit", [r.random_containment for r in results]),
    ):
        out(
            f"| {label} | {_median(values):.2f} "
            f"| {_share(values, 0.5):.1%} | {_share(values, 0.8):.1%} |"
        )
    out("")
    out(
        "The row that decides is **best prior vs hot-k**. If a static list of "
        "frequently touched files scores the same, the recurrence signal is "
        "redundant and no resolver recovers it."
    )
    out("")

    out("## Lag to the best prior")
    out("")
    hits = [r for r in results if r.best_containment >= 0.5]
    if hits:
        out(f"- targets counted (containment >= 0.50): {len(hits)}")
        out(f"- median lag: **{_median([r.lag_days for r in hits]):.1f} days**")
        out(f"- median lag: **{_median([float(r.lag_commits) for r in hits]):.0f} commits**")
    else:
        out("- no target reached containment 0.50")
    out("")

    out("## By target size")
    out("")
    out("| files changed | targets | median containment | median hot-k |")
    out("| --- | --- | --- | --- |")
    for low, high in SIZE_BUCKETS:
        bucket = [r for r in results if low <= r.size <= high]
        if not bucket:
            continue
        label = f"{low}" if low == high else (f"{low}+" if high > 10**8 else f"{low}-{high}")
        out(
            f"| {label} | {len(bucket)} "
            f"| {_median([r.best_containment for r in bucket]):.2f} "
            f"| {_median([r.hot_containment for r in bucket]):.2f} |"
        )
    out("")

    out("## Strongest recurrences observed")
    out("")
    ranked = sorted(
        results, key=lambda r: (-r.best_containment, -r.size, -r.lag_days)
    )[:10]
    out("| containment | files | lag (days) | target | best prior |")
    out("| --- | --- | --- | --- | --- |")
    for item in ranked:
        out(
            f"| {item.best_containment:.2f} | {item.size} | {item.lag_days:.0f} "
            f"| `{item.sha[:8]}` {item.subject[:48]} "
            f"| `{item.best_prior_sha[:8]}` {item.best_prior_subject[:48]} |"
        )
    out("")
    out(
        "Read these before the tables. A high score built on `__init__.py` and "
        "a settings module is not a region a record could have described."
    )

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--since", default=None, help="git --since expression")
    parser.add_argument("--until", default=None, help="git --until expression")
    parser.add_argument(
        "--extensions",
        default=DEFAULT_EXTENSIONS,
        help="comma-separated source extensions; empty string keeps every path",
    )
    parser.add_argument(
        "--exclude", action="append", default=None, help="fnmatch pattern, repeatable"
    )
    parser.add_argument("--min-files", type=int, default=1)
    parser.add_argument(
        "--max-files",
        type=int,
        default=50,
        help="commits above this are dropped as target and as candidate",
    )
    parser.add_argument(
        "--cooldown-days",
        type=float,
        default=7.0,
        help="priors nearer than this are the same piece of work, not a recurrence",
    )
    parser.add_argument("--union-depth", type=int, default=3)
    parser.add_argument(
        "--hot-k",
        type=int,
        default=0,
        help="size of the static null list; 0 sizes it to the median commit",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--json", type=Path, default=None, help="dump per-target rows")
    args = parser.parse_args(argv)

    root = args.repo.resolve()
    extensions = tuple(
        item.strip() for item in args.extensions.split(",") if item.strip()
    )
    excludes = tuple(args.exclude) if args.exclude is not None else DEFAULT_EXCLUDES

    try:
        head = _git(root, "rev-parse", "HEAD").decode().strip()
        commits = read_commits(root, args.since, args.until)
        eligible, tally = select(
            commits, extensions, excludes, args.min_files, args.max_files
        )
        results, without_prior = analyze(
            eligible, args.cooldown_days, args.union_depth, args.hot_k, args.seed
        )
    except MeasurementError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    params = {
        "extensions": ",".join(extensions) or "(all paths)",
        "excludes": ";".join(excludes) or "(none)",
        "min_files": args.min_files,
        "max_files": args.max_files,
        "cooldown_days": args.cooldown_days,
        "union_depth": args.union_depth,
        "hot_k": args.hot_k or "median commit size",
        "seed": args.seed,
        "since": args.since or "(repository start)",
        "until": args.until or "(HEAD)",
    }
    print(
        render(
            root, head, params, len(commits), tally, len(eligible), results, without_prior
        )
    )

    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "repository": str(root),
                    "head": head,
                    "parameters": params,
                    "targets": [vars(item) for item in results],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

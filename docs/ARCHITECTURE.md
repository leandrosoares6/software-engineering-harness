# SEH Architecture

## Thesis

A coding agent should not spend model tokens rediscovering facts that the software environment can compute. SEH separates deterministic engineering operations from probabilistic reasoning and introduces explicit escalation boundaries.

Before AI agents, IDEs already automated much of this deterministically: IntelliSense, live templates,
"Generate →", refactorings that composed whole classes for a single purpose. Agents redo that same work
probabilistically — slower, costlier, and error-prone. SEH's core idea is to give that determinism back:
**record a project-specific engineering operation once (LLM-assisted, expensive), replay it forever with no
inference in the path (~0 tokens, milliseconds).** It is the IntelliJ live template, for agents, measured.

Cost is tracked on **two axes, not one**: tokens *and* latency. Replacing an inference round-trip (3–8s)
with an AST operation (ms) is measured at 8.7x latency improvement and up to 99% token savings on repeated
tasks — latency is often the more perceptible win day to day.

SEH is **self-contained**: it does not require an externally installed server to operate, and it ships as
an MCP server so it works unmodified across MCP-speaking coding agents (Claude Code, Codex, Kimi CLI, and
others). The differentiator is *not* repository indexing (solved by Serena and Aider) nor universal
refactoring (solved by act101, OHM-MCP, Code Scalpel) — those are consumed or kept deliberately minimal.
It is the **composite, project-specific operation**: one that both creates new files and inserts
structurally into existing ones, which template scaffolders (cookiecutter, plop, hygen) cannot do. Full
rationale in `.claude/PRPs/prds/seh-runtime-evidencia-medicao.prd.md`.

## Core components

### seh-graph
Builds and stores a repository graph containing code artifacts and relationships.
The default implementation discovers the canonical Git root, parses tracked Python
sources with the stdlib `ast` module (zero external dependency), and atomically
stores a versioned graph in SQLite. Symbol resolution never guesses: ambiguous
name matches (e.g. two symbols reachable through different import paths) are
reported as `ambiguous`, never silently picked.

Every graph records the canonical repository root, Git HEAD (including unborn
repositories), tracked-worktree fingerprint, index timestamp, indexer version,
and schema version. Read operations reject stale or incompatible evidence.

This layer is deliberately minimal — enough for evidence to reference
`file:line:symbol` and for recorded operations to anchor structural insertions,
not an attempt to match the indexing depth or language coverage of Serena or
Aider. The Java/Tree-sitter adapter built in PR #1 is frozen as an architectural
reference (it originated the provenance/fingerprint discipline described above)
but is out of the default indexing path.

### seh-operations *(the product)*
Records and replays composite, project-specific engineering operations — the live-template layer.

An operation (`seh.operation/v0.1`) declares parameters, effects, verification and provenance. Effects are
of two kinds: creating new files from templates, and **AST-anchored insertion into existing files**. The
second is the hard one, and the reason this layer cannot be a template scaffolder: adding a CLI subcommand
means inserting a subparser block into an existing `cli.py`, not just writing a new module.

Lifecycle: **record** (once, LLM-assisted, expensive) → **store** (`.seh/operations/`, versioned in the
repository and reviewable in a PR) → **run** (deterministic, no inference in the path) → **verify**
(`seh-runtime` executes the suite) → **measure** (`seh-evidence` records tokens and latency avoided).

Replay is deterministic by contract: same operation and parameters produce byte-identical results, and an
operation whose AST anchor no longer exists fails explicitly rather than generating plausible garbage.

### seh-ir
Represents engineering intent, scope, constraints, verification requirements, budgets and escalation policy in a model-neutral form.

### seh-context
Compiles an Engineering IR task plus repository evidence into a bounded context package.

### seh-runtime
Executes deterministic engineering operations — build, test, lint, diff, impact analysis and policy checks —
**outside the model's context window**. This is the primary economic lever: the agent never ingests raw
tool output directly.

### seh-evidence
Normalizes runtime outcomes into structured evidence for local recovery or frontier escalation, reusing the
provenance/fingerprint discipline from `seh-graph` (confident evidence or an explicit error, never stale
data served silently). Also owns token measurement: capturing input/output/cache consumption per agent
session so the economics of `seh-runtime` are provable, not asserted.

### seh-adapters
Integrates external coding agents and model providers without coupling them to SEH internals.

The Python language adapter (stdlib `ast`) is the default. The Java adapter from PR #1 remains available but
frozen. Third-party context tools such as Serena may be wired in as an **optional benchmark reference**
(quantifying how much economy comes from semantic navigation alone) — never as a runtime dependency of SEH
itself. Engineering IR, context compilation, deterministic runtime, evidence policy, and model adapters
remain roadmap capabilities; see `docs/ROADMAP.md`.

## Architectural invariants

1. No model should be invoked when the requested operation can be answered by a deterministic SEH capability with sufficient confidence.
2. **No inference in the replay path.** Once an operation is recorded, running it must never call a model.
   Recording pays the model cost once; every replay after that is pure execution.
3. **Deterministic or explicitly failed — never plausible.** A replay produces byte-identical results, or it
   fails loudly. An operation whose AST anchor has drifted must not guess.
4. SEH must install and operate without requiring any externally installed server. Third-party tools may be
   consumed optionally, never as a hard dependency.
5. Every deterministic capability must be measurable in **both tokens and latency** — a capability that
   cannot show its savings cannot justify its existence.
6. Local model integration and inter-model routing are explicitly deferred (see `docs/ROADMAP.md`, M5) — the
   v1 differentiator is recorded operations, not model selection.

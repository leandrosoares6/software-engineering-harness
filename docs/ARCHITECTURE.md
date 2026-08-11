# SEH Architecture

## Thesis

A coding agent should not spend model tokens rediscovering facts that the software environment can compute. SEH separates deterministic engineering operations from probabilistic reasoning and introduces explicit escalation boundaries.

SEH is **self-contained**: it does not require an externally installed server to operate, and it ships as
an MCP server so it works unmodified across MCP-speaking coding agents (Claude Code, Codex, Kimi CLI, and
others). The primary differentiator is not repository indexing — that layer is already solved by mature
open-source tools (Serena's MCP+LSP toolkit, Aider's tree-sitter repo-map) — it is **compressing the cost of
runtime execution and re-try loops into measured, structured evidence**. Full rationale in
`.claude/PRPs/prds/seh-runtime-evidencia-medicao.prd.md`.

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
`file:line:symbol`, not an attempt to match the indexing depth or language
coverage of Serena or Aider. The Java/Tree-sitter adapter built in PR #1 is
frozen as an architectural reference (it originated the provenance/fingerprint
discipline described above) but is out of the default indexing path; see
`plans/engineering_ir_context_package.md`.

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
2. SEH must install and operate without requiring any externally installed server. Third-party tools may be
   consumed optionally, never as a hard dependency.
3. Local model integration and inter-model routing are explicitly deferred (see `docs/ROADMAP.md`, M4) — the
   v1 differentiator is the runtime/evidence/measurement loop, not model selection.

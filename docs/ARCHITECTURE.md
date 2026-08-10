# SEH Architecture

## Thesis

A coding agent should not spend model tokens rediscovering facts that the software environment can compute. SEH separates deterministic engineering operations from probabilistic reasoning and introduces explicit escalation boundaries.

## Core components

### seh-graph
Builds and stores a repository graph containing code artifacts and relationships.
The current implementation discovers the canonical Git root, parses tracked Java
sources with Tree-sitter, and atomically stores a versioned graph in SQLite.

Every graph records the canonical repository root, Git HEAD (including unborn
repositories), tracked-worktree fingerprint, index timestamp, indexer version,
and schema version. Read operations reject stale or incompatible evidence.

### seh-ir
Represents engineering intent, scope, constraints, verification requirements, budgets and escalation policy in a model-neutral form.

### seh-context
Compiles an Engineering IR task plus repository evidence into a bounded context package.

### seh-runtime
Executes deterministic engineering operations such as Git inspection, build, test, lint, diff, impact analysis and policy checks.

### seh-evidence
Normalizes runtime outcomes into structured evidence for local recovery or frontier escalation.

### seh-adapters
Integrates external coding agents and model providers without coupling them to SEH internals.

The Java language adapter is the first implemented adapter. Engineering IR,
context compilation, deterministic runtime, evidence policy, and model adapters
remain roadmap capabilities.

## Architectural invariant

No model should be invoked when the requested operation can be answered by a deterministic SEH capability with sufficient confidence.

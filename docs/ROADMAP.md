# Roadmap

> Positioning decided in `.claude/PRPs/prds/seh-runtime-evidencia-medicao.prd.md`.
>
> **The product is `seh op`: the IntelliJ live template, for agents, measured.** Record a project-specific
> engineering operation once (LLM-assisted, expensive), replay it deterministically forever (no inference,
> ~0 tokens, milliseconds). Symbol indexing and evidence compression are supporting levers, not the
> differentiator — that layer is occupied by Serena, Aider, act101 and OHM-MCP.
>
> Both **tokens and latency** are primary metrics: replacing inference (3–8s) with AST execution (ms) is
> measured at 8.7x latency improvement and up to 99% token savings on repeated tasks.
>
> SEH is self-contained (no external server required) and ships as an MCP server so it works with any
> MCP-speaking coding agent. The Java/Tree-sitter adapter from PR #1 is frozen; indexing moved to Python
> via the stdlib `ast` module.

## M0 — Foundation
- [x] CLI skeleton
- [x] Git integration
- [x] SQLite graph store
- [x] Java symbol prototype *(frozen — superseded by the Python adapter in M1)*
- [x] graph inspection
- [x] AST-backed Java language adapter *(frozen, out of the default indexing path)*
- [x] graph schema versioning

## M1 — Python Context Compiler
- [ ] **M1a (pulled into MVP Fase 1 — see PRD)**: Python adapter via stdlib `ast` (zero external dependency;
      replaces Java/Tree-sitter as the default) + `seh inspect`/`seh neighbors` working on Python repos.
      This is the exploration-compression lever: it exists mainly to let the agent locate a symbol and its
      relations without grepping and reading whole files — a cost that shows up on *every* task, not just
      the error-retry loop, which is why it could not wait for the full M1.
- [ ] **M1b (after the MVP verdict)**: Engineering IR v0.1 schema, task validation, budgeted/prioritized
      context package generation, blast-radius analysis — the full Context Compiler.

Deliberately minimal: enough for evidence to reference `file:line:symbol` and for the agent to query
structure directly, not an attempt to match Serena/Aider in indexing depth or language coverage.

## M2 — Deterministic Runtime, Evidence & Measurement
- [ ] command runner (executes test/build/lint outside the model's context)
- [ ] `pytest` output → structured evidence compressor
- [ ] structured evidence model (reuses the provenance/fingerprint discipline built in PR #1)
- [ ] measurement harness — **tokens and wall-clock latency** per task
- [ ] baseline vs. SEH benchmark on a reproducible POC project

## M3 — `seh op`: Recorded Operations *(the product)*
- [ ] `seh.operation/v0.1` format — parameters, effects, verification, provenance
- [ ] `seh op record` — LLM-assisted, runs once per pattern
- [ ] `seh op run` — fully deterministic replay, no inference in the path
- [ ] **AST-anchored insertion into existing files** (the hard part scaffolders skip; one well-defined
      anchor kind in the MVP, not a generic engine)
- [ ] operations versioned in `.seh/operations/`, reviewable in PR like project live templates were
- [ ] idempotency + explicit failure when an anchor no longer exists
- [ ] dogfooding: record `add-cli-command` from the pattern already in `src/seh/cli.py`, then use it to
      create SEH's own new commands
- [ ] payback curve: how many replays before a recorded operation pays for its recording cost

M1a, M2 and M3 all belong to the MVP, but M3 is the differentiator. M1a and M2 exist largely to serve it:
M1a provides the AST substrate that structural insertion needs, M2 verifies every replay and reports the
numbers. The falsification point is **payback**: if a recorded operation needs too many repetitions to pay
for itself, the thesis fails — cheaply and early.

## M4 — Distribution
- [ ] MCP server exposure (single-command install, no external process to configure) — exposes
      `op run`, `inspect`, `neighbors`, `test`
- [ ] works unmodified across Claude Code, Codex, and Kimi CLI
- [ ] optional benchmark arm against Serena / OHM-MCP — market reference only, never a runtime dependency

## M5 — Hybrid Intelligence *(deferred; future evolution, out of v1 scope)*
- [ ] derive operations automatically from past commits (record without an explicit session)
- [ ] local model adapter
- [ ] frontier planner adapter
- [ ] coding-agent adapters
- [ ] model routing policy

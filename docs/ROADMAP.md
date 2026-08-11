# Roadmap

> Positioning decided in `.claude/PRPs/prds/seh-runtime-evidencia-medicao.prd.md`: the differentiator is
> **deterministic runtime + structured evidence + measurement**, not repository indexing depth. SEH is
> self-contained (no external server required) and ships as an MCP server so it works with any MCP-speaking
> coding agent. The Java/Tree-sitter adapter from PR #1 is frozen; the default indexing paradigm moved to
> Python via the stdlib `ast` module — see `plans/engineering_ir_context_package.md`.

## M0 — Foundation
- [x] CLI skeleton
- [x] Git integration
- [x] SQLite graph store
- [x] Java symbol prototype *(frozen — superseded by the Python adapter in M1)*
- [x] graph inspection
- [x] AST-backed Java language adapter *(frozen, out of the default indexing path)*
- [x] graph schema versioning

## M1 — Python Context Compiler
- [ ] Python adapter via stdlib `ast` (zero external dependency; replaces Java/Tree-sitter as the default)
- [ ] Engineering IR v0.1 schema
- [ ] task validation
- [ ] symbol-scoped context selection
- [ ] token estimation
- [ ] deterministic context package generation
- [ ] blast-radius analysis

Deliberately minimal: enough for evidence to reference `file:line:symbol`, not an attempt to match
Serena/Aider in indexing depth or language coverage.

## M2 — Deterministic Runtime, Evidence & Measurement *(primary differentiator)*
- [ ] command runner (executes test/build/lint outside the model's context)
- [ ] `pytest` output → structured evidence compressor
- [ ] structured evidence model (reuses the provenance/fingerprint discipline built in PR #1)
- [ ] token measurement harness (input/output/cache capture per agent session)
- [ ] baseline vs. SEH benchmark on a reproducible POC project
- [ ] retry and escalation policy engine

## M3 — Distribution
- [ ] MCP server exposure (single-command install, no external process to configure)
- [ ] works unmodified across Claude Code, Codex, and Kimi CLI
- [ ] optional Serena benchmark arm — market reference only, never a runtime dependency

## M4 — Hybrid Intelligence *(deferred; future evolution, out of v1 scope)*
- [ ] local model adapter
- [ ] frontier planner adapter
- [ ] coding-agent adapters
- [ ] model routing policy

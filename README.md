# Software Engineering Harness (SEH)

> **Spend intelligence where it matters.**

SEH is a model-agnostic engineering harness designed to reduce unnecessary LLM usage during software development. It moves repository navigation, verification, orchestration, and repeatable engineering operations into deterministic code, leaving models to handle work that genuinely requires reasoning.

## Status

`0.1.0-alpha` — foundation prototype.

The first milestone intentionally contains **no LLM integration**. It proves the deterministic substrate first: Git-aware repository indexing, a structural graph, and queryable engineering context.

## Principles

1. **Code before tokens.** If a task can be solved deterministically, do not ask an LLM.
2. **Local before frontier.** Prefer local intelligence for bounded implementation work.
3. **Frontier only for uncertainty.** Architecture, decomposition, ambiguity and replanning justify expensive reasoning.
4. **Evidence over conversation.** Runtime outcomes are structured evidence, not unbounded chat history.
5. **Context is compiled.** Agents receive the smallest useful context package, not the repository by default.
6. **Model agnostic.** SEH should wrap coding agents rather than become one.

## Current CLI

```bash
seh init
seh index
seh inspect UserService
seh neighbors UserService
```

## Architecture direction

```text
Requirement
    │
    ▼
Engineering IR
    │
    ├──────── Repository Graph
    │
    ▼
Context Compiler
    │
    ▼
Agent Adapter
    │
    ▼
Deterministic Runtime ──► Evidence ──► Policy / Escalation
```

## v0.1 scope

- Git repository discovery
- zero-infrastructure SQLite graph store
- Java structural indexing prototype
- symbol inspection
- neighborhood queries
- no LLM dependency

The Java parser in this alpha is deliberately minimal and will be replaced by an AST-backed language adapter.

## License

Apache-2.0 (proposed for the initial open-source release).

# Software Engineering Harness (SEH)

> **Spend intelligence where it matters.**

SEH is a model-agnostic engineering harness designed to reduce unnecessary LLM usage during software development. It moves repository navigation, verification, orchestration, and repeatable engineering operations into deterministic code, leaving models to handle work that genuinely requires reasoning.

## Status

`0.1.0a2` — foundation prototype.

The first milestone intentionally contains **no LLM integration**. It proves the deterministic substrate first: Git-aware repository indexing, a structural graph, and queryable engineering context.

## Principles

1. **Code before tokens.** If a task can be solved deterministically, do not ask an LLM.
2. **Local before frontier.** Prefer local intelligence for bounded implementation work.
3. **Frontier only for uncertainty.** Architecture, decomposition, ambiguity and replanning justify expensive reasoning.
4. **Evidence over conversation.** Runtime outcomes are structured evidence, not unbounded chat history.
5. **Context is compiled.** Agents receive the smallest useful context package, not the repository by default.
6. **Model agnostic.** SEH should wrap coding agents rather than become one.

## Product vision

SEH is the project's versioned procedural memory. A coding agent handles a new pattern once; when that
pattern proves reusable, it can be crystallized as a deterministic capability. Instantiating that capability
produces an operation the project can execute, verify, and measure without inference. The developer continues
to work through natural-language prompts, while recurring engineering procedures progressively move out of
the model's context and into reviewable project capabilities.

See [Product Scenario: A Python Project That Learns How It Is Built](docs/PRODUCT_SCENARIO.md) for the
end-to-end developer experience and [SEH Capability Model](docs/CAPABILITY_MODEL.md) for the primitive,
capability, and operation mechanics.

## Current CLI

```bash
seh init
seh index
seh inspect UserService
seh neighbors UserService
seh neighbors --id class:0123456789abcdef0123
seh capability validate ./candidate --allow-verification
```

`inspect` lists every partial match with its stable node ID and qualified name.
`neighbors` succeeds only for an unambiguous query; when several nodes match, it
lists candidates that can be selected with `--id`. Read commands reject missing,
legacy, or stale indexes and never create repository state.

`capability validate` is the hand-built Phase 0 vertical slice. It loads a restricted
`seh.capability.phase0/v0.1` candidate, executes fidelity, developer-approved generalization,
idempotency, and safe-refusal gates in memory, and runs declared verification commands in a temporary
working copy. It validates candidates but never installs or runs them against the working tree. Verification
is denied by default: review the candidate locally, especially every command, then opt in with
`--allow-verification`. Commands use an argument vector with no shell and a bounded timeout, but they are not
an operating-system sandbox.

## Architecture direction

```text
Developer prompt
    │
    ▼
External coding agent
    │
    ├── novel work ──► reason and implement ──► propose capability
    │
    └── learned work ──► select installed capability
                              │
                              ▼
                    deterministic primitive plan
                              │
                              ▼
                         operation patch
                              │
                              ▼
                    verification and evidence
```

## v0.1 scope

- Git repository discovery
- zero-infrastructure SQLite graph store
- Java AST indexing with Tree-sitter
- symbol inspection
- neighborhood queries
- schema-versioned graph provenance and freshness checks
- no LLM dependency

The Java adapter indexes classes, interfaces, enums, records, nested types,
methods, constructors, imports, inheritance, and interface implementation.
Only Git-tracked files are indexed; unsupported, external, or ambiguous
references are reported without creating speculative graph edges.

## License

Apache-2.0.

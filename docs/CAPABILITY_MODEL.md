# SEH Capability Model

## Purpose

SEH learns the recurring engineering procedures of a project as versioned capabilities. This document
defines the unit of learning, the deterministic vocabulary used to express it, and the mechanics that make
source-preserving replay possible.

The model has three levels:

```text
primitive
    ↓ composed into
capability
    ↓ instantiated with parameters as
operation
```

- A **primitive** is a small, project-agnostic deterministic instruction implemented by SEH.
- A **capability** is a versioned, project-specific procedure composed from primitives, templates, contracts,
  and examples.
- An **operation** is one immutable invocation of a capability against a compatible base state. It produces a
  plan, patch, verification result, and evidence.

The versioned artifact is therefore a capability, not an operation. Capabilities live in
`.seh-capabilities/`; operation records are runtime evidence and remain in local `.seh/` state.

## Granularity

A capability begins where a decision ends and ends where another decision begins.

Too small:

```text
insert-import
create-file
append-to-list
```

Those are primitives. They manipulate code but contain no knowledge of how a particular project works.

Too large:

```text
implement-billing-module
redesign-agent-memory
migrate-to-event-driven-architecture
```

Those requests contain domain or architectural decisions that cannot be reduced safely to typed parameters.

Appropriate capability boundaries look like:

```text
add-agent-tool
add-authenticated-route
add-knowledge-source
add-event-consumer
add-agent-evaluation-case
```

A candidate has suitable granularity when:

1. it represents one recognizable engineering intent;
2. it coordinates more than a trivial textual edit;
3. its variation is expressible through typed parameters;
4. its effects are bounded and known before writing;
5. correctness is objectively verifiable;
6. replay requires no new architectural or domain decision.

## Closed capabilities in the MVP

MVP capabilities are **closed**: every variation required for replay must fit in declared, typed parameters.
They do not accept model-generated source-code slots or callbacks.

An extension point would make two invocations of the same capability incur different inference cost depending
on how the slot was filled. That is incompatible with the MVP measurement protocol, even though SEH itself
would not call the model. If extension-bearing capabilities are ever introduced, they must be a separate
category with a separate economic baseline.

Capabilities also cannot invoke other capabilities in the MVP. They compose only versioned SEH primitives.
Capability-to-capability composition is deferred because it introduces dependency versions, cycles, parameter
propagation, effect conflicts, and distributed rollback.

## A closed primitive algebra

The primitive vocabulary is closed and deliberately small. A consuming project cannot add arbitrary Python
plugins or lifecycle scripts as new primitives. If two real capabilities require a missing primitive, that is
product evidence: the primitive can be added to SEH deliberately, versioned, reviewed, and tested.

The initial vocabulary to test in Phase 0 is:

```text
LOCATORS (Python AST → source span)    EFFECTS (source text → patch)
├── python.module                     ├── file.render
├── python.symbol                     ├── splice.before
├── python.assignment                 ├── splice.after
├── python.collection_literal         └── splice.into_collection
└── python.import_block

VERIFICATION
└── verify.command
```

This list is a hypothesis, not a frozen API. Phase 0 must derive the smallest useful vocabulary empirically
from two capabilities with different shapes.

Each structural primitive supports one declared syntactic form and refuses the others. For example,
`splice.into_collection` for a list literal is not a generic “register this value somewhere” operation. A
set literal, dictionary, `.extend()` call, decorator registry, and annotation-based registry are different
forms that require different support or explicit refusal.

## Source-preserving Python edits

Python's stdlib `ast` is a locator, not a source rewriter. A parse/unparse round trip changes source even when
the tree is untouched: comments disappear and quote style, blank lines, and collection formatting may change.
Consequently, mutation must never use `ast.unparse()`.

The supported mechanism is:

```text
Python AST → locate and validate a structural anchor → exact source offset
source text + rendered fragment → splice at that offset → patch
```

The AST provides node positions (`lineno`, `col_offset`, `end_lineno`, `end_col_offset`). SEH converts the
validated source span into an insertion offset and changes only the declared fragment. Untouched files remain
byte-identical; within a touched file, bytes outside the splice remain identical.

Inserted text derives local style from neighboring source, including indentation, separators, and trailing
commas. SEH must not impose a formatter-specific style during replay. Formatting tools may be verification
commands, but they are not a hidden prerequisite for fidelity.

Every effect contributes to an in-memory plan. SEH validates all preconditions and detects conflicting
effects before writing. The complete patch is applied atomically; a failed precondition or verification must
not leave a partial structural edit.

## Capability package

A capability candidate is an agent-authored package such as:

```text
.seh-capabilities/
└── add-agent-tool/
    ├── capability.yaml
    ├── templates/
    │   ├── tool.py.j2
    │   └── test_tool.py.j2
    └── examples/
        ├── fidelity/
        │   ├── before/
        │   └── expected.patch
        ├── generalization/
        │   ├── before/
        │   └── expected.patch
        ├── idempotency/
        └── refusal/
```

The schema is `seh.capability/v0.1`. A conceptual manifest is:

```yaml
schema: seh.capability/v0.1
id: python-chat-agent.add-agent-tool
version: 1

intent:
  summary: Add a callable tool to the chat agent
  use_when:
    - A service function must become available to the chat agent
  do_not_use_when:
    - The request changes how tools are discovered

parameters:
  name:
    type: python_identifier
  service_symbol:
    type: python_symbol
    must_exist: true

applicability:
  all:
    - python_assignment_exists: app.agents.registry.CHAT_AGENT_TOOLS

steps:
  - uses: file.render
    with:
      template: templates/tool.py.j2
      destination: app/tools/{{ name }}.py
  - uses: splice.into_collection
    with:
      symbol: app.agents.registry.CHAT_AGENT_TOOLS
      value: "{{ name }}"

verification:
  - uses: verify.command
    with:
      command: pytest
      args:
        - tests/tools/test_{{ name }}.py
```

Arbitrary `before` and `after` hooks are excluded. In the MVP, project commands may appear only as declared
verification with explicit executable, arguments, timeout, and expected exit status.

## Base-state fixtures and the four gates

A candidate is authored after the accepted implementation exists, so fidelity cannot run against the current
working tree: the created artifacts are already present. Each gate therefore uses a versioned fixture that
represents the relevant pre-implementation state.

Fixtures are scoped snapshots of declared files, not Git references. They survive rebases and squash merges
and contain only the minimum state needed to exercise the capability.

`seh capability validate` runs four gates:

1. **Fidelity** — instantiate the candidate against the first `before/` fixture and reproduce the accepted
   patch over declared files.
2. **Generalization** — instantiate it against a different fixture and parameter set proposed by the agent
   and approved or edited by the developer.
3. **Idempotency** — run it over its own result; the second invocation is a no-op or an explicit
   already-applied refusal, never a duplicate edit.
4. **Safe refusal** — run it against an incompatible fixture; it must reject before writing anything.

Only a candidate that clears all four can be promoted by `seh capability install`.

## Replay contract

The deterministic contract is:

```text
capability + parameters + compatible base state → same operation plan and patch
```

Compatibility uses local preconditions: expected symbols, exact anchor kind, relevant structural-fragment
hash, artifact absence, and supported capability schema. Unrelated repository changes do not invalidate the
capability.

`seh capability run CAPABILITY_ID ...` instantiates an operation. The operation has an immutable identifier
and records:

- capability ID and version;
- validated parameters;
- base-state precondition results;
- expanded primitive plan;
- patch and affected files;
- verification evidence;
- duration and economic measurements.

## Cheap capability selection

The external coding agent selects capabilities semantically, but it must not read every full manifest. SEH
exposes a compact catalogue projection containing only:

```text
id + version + intent.summary + use_when + do_not_use_when + parameter summary
```

Templates, examples, primitive steps, and applicability internals remain outside the model context. SEH first
filters the catalogue deterministically using repository applicability; the agent then chooses from the small
remaining projection and supplies parameters.

Selection therefore follows:

```text
installed catalogue
    → deterministic applicability filter
        → compact intent projection
            → semantic choice by the external agent
                → deterministic operation
```

## Phase 0 output

Phase 0 must hand-author **two capabilities of different shapes**. One capability can prove that a case was
hard-coded; two begin to reveal whether a reusable primitive algebra exists.

The phase delivers:

1. a provisional closed primitive vocabulary derived from both capabilities;
2. two capability packages with pre-implementation fixtures;
3. source-preserving AST-location plus textual-splice prototypes;
4. all four gates passing for both capabilities;
5. an explicit record of primitives that were shared, split, added, or rejected.

No production CLI, final schema parser, MCP surface, arbitrary scripts, capability composition, or extension
points belong to this phase. Its question is narrower:

> What is the smallest deterministic language that can express two real recurring procedures of this
> project without losing source fidelity?

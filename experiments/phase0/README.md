# Phase 0 executable evidence

This directory preserves the prospective `install` → `run` capture that closed
the technical feasibility gate. It is not part of the runtime, and the default
product suite does not collect it (`testpaths = ["tests"]`).

Run it explicitly:

```bash
pytest experiments/phase0
```

`real_capture/add-capability-subcommand/` contains:

- the true pre-implementation bytes recorded from a clean Git baseline;
- the accepted structural subset for `install`;
- the `run` proposal committed before its behavioral implementation;
- developer approval of the generalization case;
- executable fidelity, generalization, idempotency, and safe-refusal checks.

The experiment proves technical feasibility for one retained capability. It
does not prove broad primitive coverage or economic payback. Those remain
separate product questions documented in
[`../../docs/PHASE0_FINDINGS.md`](../../docs/PHASE0_FINDINGS.md) and
[`../../docs/M2_MEASUREMENT_PROTOCOL.md`](../../docs/M2_MEASUREMENT_PROTOCOL.md).

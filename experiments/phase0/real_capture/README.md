# First real capture

`add-capability-subcommand/` is derived from the accepted `install` event between commits `717e877` and
`abbb477`. The fidelity fixture is complete and prospectively grounded in the recorded Git baseline.

The candidate is deliberately not installable yet. `proposals/run.patch` is only the deterministic wiring
produced for `name=run`; it has no `capability_run.py`, no developer approval, and no accepted generalization
fixture. Those artifacts must come from a subsequent real event. Creating the behavioral module through this
capability would incorrectly admit the still-unproven `file.render` primitive.

Regenerate the captured bytes from the immutable commits with:

```bash
PYTHONPATH=src python experiments/phase0/capture_real_fixture.py
```

The generator replaces only its owned `add-capability-subcommand/` directory so ignored build residue cannot
silently enter the fixture. Do not point `compileall` recursively at `real_capture/`: the `before/` tree is
source data, not importable experiment code.

Then verify them with:

```bash
pytest experiments/phase0/test_real_capture.py
```

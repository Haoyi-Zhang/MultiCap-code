# Additional finite validation

These scripts are post-development checks within the paper's finite, model-relative scope. They are not external review, a statistical held-out study, or evidence about production throughput.

`independent_finite_checks.py` imports none of the project implementation. It independently re-derives 700 finite residual encodings, all 256 two-by-two nonnegative matrices with entries 0--3, exact two-slot all-pairs costs for dimensions one through four, and the equations of all 64 retained rank witnesses.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 validation/independent_finite_checks.py --root . --out /tmp/independent-finite-checks.json
```

`structured_cases.py` constructs fresh structured matrices whose explicit nonnegative factor width is matched by exact rational rank, checks semantics and permutations, and compares the declared cut-traffic formula with a column-decomposition baseline.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 validation/structured_cases.py --out-dir /tmp/structured-cases
```

`check_all.py` runs the documented payload audit, end-to-end check, unit tests, proof kernels, both validation scripts, a fresh reproduction, input regeneration, pilot recomputation, and package-clean audit. A pass is an internal consistency result only.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 validation/check_all.py --out /tmp/artifact-check.json
```

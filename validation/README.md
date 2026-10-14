# Additional finite validation

These scripts are post-development checks within the paper's finite, model-relative scope. They are not external review, a statistical held-out study, or evidence about production throughput.

`independent_finite_checks.py` imports none of the project implementation. It independently re-derives 700 finite residual encodings, all 256 two-by-two nonnegative matrices with entries 0--3, exact two-slot all-pairs costs for dimensions one through four, and the equations of all 64 retained rank witnesses.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 validation/independent_finite_checks.py --root . --out /tmp/independent-finite-checks.json
```

`structured_cases.py` constructs structured matrices whose explicit nonnegative factor width is matched by exact rational rank. Its default campaign checks numeric factor identities, permutations and the cut-traffic formula against a column decomposition. `--execute-schedules` additionally compiles both factorizations and independently checks the complete event streams on the same matrices and numeric draws.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 validation/structured_cases.py --out-dir /tmp/structured-cases
PYTHONDONTWRITEBYTECODE=1 python3 validation/structured_cases.py --execute-schedules --out-dir /tmp/structured-execution
```

`check_all.py` runs the documented payload audit, end-to-end check, unit tests,
proof kernels, both validation scripts, a fresh reproduction, input
regeneration, pilot recomputation, and package-clean audit.  It compares
regenerated inputs byte-for-byte and all primary campaign files, including
certificates, plus the 4,760 factor, 4,760 column and 580 permuted event schedules
in the supplemental execution campaign. These use the same 580 matrices,
not additional independent workloads. Only documented timing/RSS fields in summary and pilot JSON
are ignored; the structured-case summary excludes its elapsed time.  Missing
directories/files, scientific drift, unsuccessful commands, and timeouts fail
the gate.  A pass is an internal consistency result only.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONUTF8=1 python3 -B validation/check_all.py \
  --work-dir /tmp/p093-scientific-check --out /tmp/artifact-check.json
```

The work directory must be fresh and outside the repository.  It retains all
generated files and complete raw command logs, including failures; it is never
deleted by the checker.  Without `--work-dir`, a persistent temporary directory
is created and reported.  Each invoked command has a 150-second timeout.
The supplied workflow additionally bounds the whole run.  `--quick` omits the
full campaign reproduction and must not be described as a full reproduction.

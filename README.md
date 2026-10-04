# Capability-indexed materialization bounds for multiset programs

This standalone repository supports the internal article **Capability-Indexed
Materialization Bounds for Multiset Programs**.  It contains exact inputs,
source/interpreters, proof-producing compilers, independent certificate
checkers, handwritten proofs, a small purpose-built proof kernel, negative
controls, and retained results.  It does not require the paper directory.

## Scientific contents

- `proofs/capability.md` defines capability signatures, simulation monotonicity,
  strict same-denotation separations, and the no-denotation-only-bound result.
- `proofs/replay.md` proves typing, multiplicity preservation, termination, and
  a sufficient zero-derived-store replay budget for the declared pure bag
  fragment.
- `proofs/residual.md` proves the exact finite one-way bit-barrier theorem and
  describes the residual-class compiler.
- `proofs/integer-rank.md` proves the positive substitution lemma and exact
  count-word barrier theorem, with a factorization compiler.
- `proofs/cache.md` proves the occurrence-record product results.
- `formal/` kernel-checks the residual semantic core and 64 polynomial factor
  identities.  Its README states the exact non-claims.

The mathematical measures are model-specific.  Residual classes and
nonnegative integer rank are established concepts; the article's contribution
is the capability-indexed semantics, strict separations, and their integration
with typed bag compilation—not a claim to have invented those measures.

## Reproduction

Use POSIX/Linux with Python 3.10 or newer and the standard library.  Do not use
Python's `-O` flag.  From the repository root:

```sh
python audit.py --package-clean
python run.py check
python run.py reproduce --out /tmp/resource-semantics-reproduction
python -m unittest discover -s tests -v
python formal/check.py
python src/generate_inputs.py --out /tmp/resource-semantics-inputs
python src/pilot.py
```

The two output directories must be absent or empty.  `audit.py` binds each full
input payload—not merely its ID—to certificate contents, checker returns, CSV
rows, summary fields, evidence paths, reference records, and package hygiene.
`audit.py` and `run.py check` both execute every factor schedule through the
independent phase/address/liveness checker as part of the payload binding.  Compare generated
input files with `inputs/`; `reproduce` reruns the bounded campaign.  The cache
pilot is a current recomputation and is intentionally separate; its JSON says
that the earlier raw record was not retained.

Expected main logical counts are:

- 985 declared program/certificate instances;
- 896 replay semantic cases;
- nine occurrence-cache certificates;
- 64 exact integer-rank packets;
- all 16 Boolean two-by-two residual functions and 44 capacity variants;
- 33 legacy controls, split into 12 cache-certificate rejections, eight
  syntax/type rejections, four semantic differences, two lifecycle tests, and
  seven positive-source cases;
- four additional factor-schedule mutation rejections;
- 30,083 counted validation/transition obligations under the retained legacy
  counting rule, plus 10,743 event-checked schedules and 313,123 checked events;
- 57 focused unit/mutation/integrity tests;
- 81 audited scholarly references, each cited and carrying a persistent
  identifier; and
- one first-order theorem plus 64 semiring identities checked by the
  purpose-built kernels.

CPU time, wall time, RSS, PDF bytes, and temporary paths are measurements rather
than deterministic outputs.  Logical inputs, CSVs, JSON certificates, reference-audit records, and
checker judgments are deterministic.

## Evidence interpretation

The source-language oracle intentionally materializes bags; the replay
interpreter is separate.  The exact rank and cache synthesizers are separate
from their checkers.  Rank packets include both a factor witness and a Bellman
potential over every bounded residual state.  Residual packets include the
reconstructed equivalence classes and shortest fixed-width codes.  Negative
controls mutate dimensions, partitions, costs, witnesses, potentials, types,
and semantic operators.

Finite checks do not prove the general theorems.  Conversely, successful
commands do not verify CPython, the operating system, or physical performance.
The paper and proof documents state which results are handwritten, kernel
checked, finite checked, or measured.

## Machine boundaries

The bit-barrier theorem forbids uncharged input-dependent addresses or trace
lengths, permits output only after the barrier, and charges bit stores and
loads.  The positive-word theorem permits only static positive natural
arithmetic and forbids subtraction, division, bit extraction, branches on
packed values, and readable output.  Its compiler has exactly two transient
buffers: prefix T0 accumulates one left summary; the barrier clears T0/T1;
continuation T0 is the output accumulator and T1 the right linear form; a fixed
persistent slot is consumed by one fused multiply-add.  The occurrence model charges identity
records and does not allow multiplicity compression.  Changing any of these
features changes the capability signature and may change the optimum.

## Provenance and external use

The evidence is not independently blind-reviewed. Authors must inspect and take responsibility for all content and recheck current venue policies before any external use. No email, account action, external model API, private data, GPU, institutional compute, or human-subject evidence was used.


## Additional finite validation

The neutral `validation/` directory contains two post-development robustness
checks and one fail-closed aggregate command.  They are not external review or
a statistical held-out study.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 validation/independent_finite_checks.py \
  --root . --out /tmp/independent-finite-checks.json
PYTHONDONTWRITEBYTECODE=1 python3 validation/structured_cases.py \
  --out-dir /tmp/structured-cases
PYTHONDONTWRITEBYTECODE=1 python3 validation/check_all.py \
  --out /tmp/artifact-check.json
```

The independent script imports none of the project implementation and rechecks
finite residual encodings, all 256 small two-by-two matrices, exact two-slot
all-pairs costs through four by four, and all 64 retained rank-witness
equations.  The structured cases are exact model-relative checks, not production
performance measurements.  See `validation/README.md`.

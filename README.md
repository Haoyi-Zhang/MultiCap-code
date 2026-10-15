# Capability-indexed materialization bounds for multiset programs

This standalone artifact accompanies **Capability-Indexed Materialization Bounds
for Multiset Programs**. It contains deterministic inputs, bag interpreters,
proof-producing compilers, certificate checkers, written proofs, purpose-built
proof kernels, negative controls, and retained results. No paper directory,
external dataset, solver, or network service is required.

## Environment and entry points

The complete workflow requires POSIX/Linux, Python 3.10 or newer, and the
standard library. Keep assertions enabled (do not use `-O`). The runner and
pilot use POSIX resource limits; they are not native Windows entry points.
Run commands from this directory.

```sh
python -B audit.py --package-clean
python -B run.py check
python -B -m unittest discover -s tests -v
python -B tests/regression_predicate_dispatch.py -v
python -B formal/check.py
```

The audit binds full input payloads to certificates, checker returns, result
rows, summaries, evidence paths, and reference records. Both the audit and
`run.py check` execute retained factor schedules through the independent
phase/address/liveness checker.

## Reproduction

Use fresh output directories; do not overwrite the retained `inputs/` or
`results/`:

```sh
python -B run.py reproduce --out /tmp/resource-semantics-reproduction
python -B src/generate_inputs.py --out /tmp/resource-semantics-inputs
python -B src/pilot.py
```

Compare regenerated inputs under `/tmp/resource-semantics-inputs/inputs/` with
`inputs/`. The pilot prints a current recomputation; its JSON records that an
earlier raw pilot record was not retained.

For the aggregate reproduction and comparison, use:

```sh
PYTHONUTF8=1 python -B validation/check_all.py \
  --work-dir /tmp/p093-scientific-check --out /tmp/artifact-check.json
```

The work directory must not exist and must be outside the repository. The
aggregate retains command logs and generated outputs, compares all five input
files and 98 primary result files, and checks both structured validation modes.
Only documented timing/RSS fields are excluded from comparisons. `--quick`
omits the full campaign reproduction. See [validation/README.md](validation/README.md)
for individual commands, structured-case counts, and comparison rules.

## Inputs, results, and proofs

- `inputs/`: semantic programs/databases, cache cases, rank matrices, residual
  functions, and the rectangle diagnostic.
- `results/`: logical CSVs, JSON certificates, summaries, negative controls,
  and retained validation/reproduction outputs.
- `proofs/`: capability, replay, residual, integer-rank, and occurrence-cache
  arguments. `claim_evidence_ledger.csv` maps claims to their evidence.
- `formal/`: one sorted first-order theorem and 64 semiring factor identities;
  [formal/README.md](formal/README.md) describes the kernel scope.
- `reference-audit.csv`, `literature-notes.md`, and `external_resources.csv`:
  reference identities, technical roles, and source provenance.

The primary summary records 985 program/certificate instances: 896 replay
cases, nine cache packets, 64 rank packets, and 16 residual functions. It retains
30,083 legacy validation/transition obligations and separately reports 10,743
event-checked schedules, 313,123 events, 33 legacy controls, and four
factor-schedule mutation rejections. These counts are distinct from the unit
test census and the additional structured validation.

Logical inputs, CSVs, certificates, and checker judgments are deterministic.
CPU/wall time, RSS, temporary paths, and PDF bytes are environmental quantities,
not deterministic results or physical-performance claims. Finite checks do not
replace the general proofs, and the custom kernels are not external proof
assistants.

## Model conditions

The bounds are capability-specific. The bit-barrier model uses static
addressing, charges bit stores/loads, and permits output only after the barrier.
The positive-word model permits static positive natural arithmetic, with no
subtraction, division, bit extraction, packed-value branching, or readable
output. Its compiler uses two transient buffers; the barrier clears both, and
the continuation consumes persistent slots by fused multiply-add. The
occurrence model charges identity records rather than compressed multiplicities.
Changing these conditions may change the optimum.

The source-language oracle materializes bags and is separate from replay.
The rank/cache synthesizers and their checkers are separate implementations.
`Replay.test` directly dispatches four validated predicate kinds; the focused
predicate regression compares literal bag equations and all retained semantic
fields. This reuses host bookkeeping without changing modeled metrics or
claiming a measured speedup.

## Provenance and external use

The evidence is not independently blind-reviewed. Authors must inspect and take responsibility for all content and recheck current venue policies before any external use. No email, account action, external model API, private data, GPU, institutional compute, or human-subject evidence was used.

# Kernel-checked proof components

`logic_kernel.py` is a small sorted first-order equational kernel.  It computes
conclusions from proof terms using only assumptions, equality rules,
implication, and universal quantification.  `residual_theorem.py` checks the
semantic core of the residual lower bound: for every deterministic two-phase
implementation, equal barrier states imply equal residual functions.

The kernel rejects cross-sort equalities, malformed binders, and conflicting
argument/result signatures for a function symbol across the entire derivation.
Universal elimination checks the instantiation sort even when a shadowed or
unused binder would make substitution leave the body unchanged.  Focused
regressions exercise both rejection and valid shadowing.

`semiring_kernel.py` is a separate natural-polynomial normalizer.  It rebuilds
the target bilinear polynomial and the extracted factor schedule for every
retained integer-rank packet, then checks equality after normalization.

Run from the repository root:

```sh
python formal/check.py
```

This is purpose-built mechanization, not an external proof assistant and not a
verification of CPython.  Cardinality arithmetic, the positive-coefficient
substitution lemma, and the replay metatheory remain paper proofs.  The scope is
stated this way in the manuscript and evidence ledger.

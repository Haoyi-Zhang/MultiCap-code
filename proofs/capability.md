# Capability-indexed resource semantics

This document fixes the semantic and machine boundaries used by the paper.  It
is a handwritten mathematical proof, supplemented by the executable witnesses
listed in the claim ledger.  It does not assert a lower bound outside the
capability signature to which that bound is attached.

## 1. Programs and observations

A finite bag over a set `T` is a finitely supported function `T -> N`.  The
source language is an acyclic typed expression graph over finite bags.  Its
constructors are source, typed empty, selection, projection, additive union,
Cartesian product, truncated difference, minimum intersection, maximum union,
left outer join, and full outer join.  Their denotations are the usual
multiplicity functions.  The observable result is the final bag; output order,
source-read order, and internal state are not observations.

A program implementation is correct when it terminates and emits exactly the
source-language multiplicity function on every well-typed finite input.  This
is deliberately weaker than cost contextual equivalence and deliberately
stronger than set equality.

## 2. Capability signatures

A capability signature is a tuple

    kappa = (access, algebra, addressing, fast, slow, output).

`access` declares which source occurrences may be revisited and whether a
one-way phase barrier exists.  `algebra` declares the dynamic representation
and operations: arbitrary finite bits, positive natural count words, or
occurrence identities.  `addressing` states whether an address/access pattern
is static or itself charged as state.  `fast` states the persistent state unit
and capacity at a barrier.  `slow` states the transferred unit and operation
charged.  `output` states when output is permitted and whether it is readable.

The signature is part of the theorem statement.  A read allowance, a word
algebra, or a free output channel is not an implementation detail that may be
silently changed after a lower bound has been proved.

For a program P and capacity M, `OPT_kappa(P,M)` is the infimum of the declared
cost coordinate over correct implementations admitted by kappa.  It is
infinity if no correct implementation exists.

## 3. Capability simulation

Write `kappa <= lambda` when every kappa implementation has a semantics- and
cost-preserving simulation under lambda.  This relation is reflexive and
transitive by identity and composition of simulations.

### Theorem C1 (capability monotonicity)

If `kappa <= lambda`, then for every program P and compatible capacity M,

    OPT_lambda(P,M) <= OPT_kappa(P,M).

### Proof

Take any correct kappa implementation I.  By the definition of the preorder,
there is a correct lambda implementation sim(I) with cost no greater than that
of I.  Taking the infimum over I yields the inequality.  If there is no correct
kappa implementation, the right side is infinity and the result is immediate.

The theorem is elementary but prevents an important invalid inference: a lower
bound proved under a weaker capability does not automatically survive when a
stronger source, representation, or output channel is admitted.

## 4. Strict separations

### C2. Restartable source versus a one-way positive barrier

Let `D_n(x,y) = sum_i x_i y_i` for natural vectors.  In the restartable pure bag
machine, the evaluator can enumerate the necessary source occurrences and emit
the scalar without storing a derived relation; its derived-store transfer cost
is zero once its finite control stack fits.  In the positive one-way barrier
machine with zero persistent count words, the coefficient matrix is the n by n
identity and has nonnegative integer rank n.  The exact positive-barrier theorem
therefore gives `2n` temporary word transfers.  For every positive n the costs
are different for the same bag function.

### C3. Arbitrary bits versus positive count words

Restrict x and y to Boolean n-vectors and retain the integer dot product.  The
residual map x |-> (y |-> x dot y) is injective, so it has `2^n` classes.  The
finite residual machine therefore needs exactly n persistent bits for zero
spill.  In the positive count-word machine, the same coefficient matrix has
integer rank n; with one persistent count word it needs `2(n-1)` word
transfers.  This is a representation separation, not a conversion claiming
that one natural word equals one bit.

### C4. Occurrence identity versus value-count compression

For a 3 by 3 Cartesian product and two occurrence-record slots, the exact
occurrence-cache optimum is ten source-record reads.  When all three records on
each side have the same value and the representation is allowed to aggregate
multiplicity, two counters suffice after six source reads.  The output
multiplicity is nine in both executions.  Thus an occurrence lower bound is not
a lower bound for every bag representation.

The executable file `src/capability_cases.py` reconstructs these numerical
witnesses from the retained exact certificates.

## 5. No denotation-only exact bound

### Corollary C5

There is no function `G` of only a bag denotation and a scalar memory parameter
that equals the exact minimum temporary-materialization cost for all the
capability signatures above.

### Proof

Let `e_star = project_unit(select_equal(X product Y))`.  On inputs supported on
`n` tags its output multiplicity is `D_n`.  The syntax and tuple arities of
`e_star` are fixed independently of `n`, so the replay construction has a fixed
sufficient logical-cell budget `s = S(e_star)`.  Choose `n > s` and supply the
same numerical scalar `s` to both machines.  Replay has exact temporary cost
zero.  The positive one-way machine has coefficient matrix `I_n`, and with `s`
persistent count words its exact cost is `2(n-s) > 0`.  Thus the same bag
denotation and scalar argument would force G to return two different values.

The corollary does not say that machine-independent lower bounds are impossible.
It says that a claimed exact materialization optimum must identify enough of the
machine to make the optimization problem well-defined.

## 6. Relative complete fusion

A fusion certificate has two parts: a semantic derivation establishing bag
equality, and a resource witness admitted by one capability signature.  An
implementation is fully fused relative to kappa when its declared temporary
materialization coordinate is zero.  A compiler is complete for a fragment
relative to kappa when it either produces a zero-cost certificate whenever one
exists or returns a checked positive lower-bound witness and a matching optimal
schedule.

The residual and positive barrier fragments satisfy this relative notion: their
closed-form optima decide whether zero spill exists and their witnesses compile
to schedules meeting the lower bound.  The replay fragment supplies a
sufficient zero-derived-store compiler but not a memory-minimal decision
procedure.  The occurrence cache result is an exact diagnostic for its stated
record model, not a compiler for all bag programs.

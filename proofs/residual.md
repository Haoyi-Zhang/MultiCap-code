# Exact residual-state theorem for a finite one-way barrier

## 1. Machine

Let X, Y, and O be nonempty finite sets and let `F : X x Y -> O`.  The prefix
phase receives x and cannot read y.  A one-way barrier then destroys transient
prefix state.  The continuation receives y and cannot reread x.  Output is
permitted only after the barrier.

The barrier has B persistent fast bits and a finite number of statically
addressed slow bit cells.  Writing one slow bit before the barrier costs one
transfer; reading it after the barrier costs one transfer.  The address and
number of transferred cells may not be an uncharged input-dependent side
channel.  A correct implementation must return F(x,y) for all inputs.  Its cost
is the worst-case total number of slow-bit writes and reads.

Define the residual row of x by `R_x(y)=F(x,y)`.  Define x ~ x' iff their rows
are equal.  Let N_F be the number of equivalence classes and
`K_F = ceil(log2 N_F)`, with `K_F=0` when `N_F=1`.

## 2. Semantic separation lemma

### Lemma R1

If two prefixes x and x' reach the same complete barrier state, then their
residual rows are equal.

### Proof

Fix any y.  After the barrier the implementation is deterministic and sees the
same barrier state and the same y in both runs.  It must therefore produce the
same output.  Correctness makes those outputs F(x,y) and F(x',y).  Since y was
arbitrary, the residual rows are equal.

`formal/residual_theorem.py` constructs a proof term for this implication in the
small sorted first-order kernel.  That check covers this logical core; it does
not mechanize the cardinality arithmetic below.

## 3. Lower bound

### Lemma R2

If every execution transfers at most s distinct slow bits across the barrier,
then the implementation distinguishes at most `2^(B+s)` residual classes.

### Proof

Normalize away a slow write never read and a read of a cell whose value is
fixed independently of x.  The information available to the continuation then
consists of B fast bits and at most s transferred slow bits.  Static addressing
prevents the chosen addresses or trace length from supplying extra information.
Thus there are at most `2^(B+s)` complete barrier states.  By Lemma R1,
different residual classes require different states.

### Corollary R3

Every correct implementation has at least

    2 * max(0, K_F - B)

slow-bit transfers in the worst case.

### Proof

Lemma R2 yields `B+s >= K_F`, hence at least `max(0,K_F-B)` slow bits must cross
the barrier in some execution.  Each such bit must be written before and read
after the one-way barrier, contributing two transfers.

## 4. Matching compiler

Choose one representative for each residual class and assign each class an
injective K_F-bit code.  In the prefix phase, compute the class of x.  Keep the
first min(B,K_F) code bits in fast state and write the remainder once to fixed
slow cells.  After the barrier, read those cells once, reconstruct the code, and
return the representative row's value at y.

### Lemma R4

The compiled program returns F(x,y) and uses exactly
`2*max(0,K_F-B)` slow-bit transfers.

### Proof

The class code decodes to a representative with the same residual row as x, so
lookup at y returns F(x,y).  The number of spilled code bits is exactly the
positive part of K_F-B, and every spilled bit is written and read once.

### Theorem R5 (exact residual-state cost)

For the finite one-way bit machine,

    OPT_bit(F,B) = 2 * max(0, ceil(log2 N_F) - B).

The lower bound is Corollary R3 and the upper bound is Lemma R4.

## 5. Boundaries

The theorem charges bits, not machine words; output is after the barrier and is
not readable; the class table and finite control are static code, not dynamic
state; and input-dependent addressing is not a free channel.  The construction
may be exponentially large in the explicit domain and is not presented as a
practical compiler for unbounded data.  It is an exact semantic normal form for
the finite barrier problem and a reference point for the positive-word
specialization.

## 6. Executable certificates

`src/residual.py` groups equal rows, assigns shortest fixed-width codes, and
emits schedules for each fast capacity.  `src/residual_check.py` independently
reconstructs the equivalence relation pairwise, checks the minimal width and
cost, and executes every compiled input.  The retained corpus contains all 16
Boolean functions on a two-by-two domain, 44 capacity variants, and 176
compiled executions.  These finite checks attack the implementation; they are
not the proof of Theorem R5.

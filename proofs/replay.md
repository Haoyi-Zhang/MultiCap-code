# Replay semantics and memory argument

These are handwritten mathematical arguments. The Python implementation and the finite test corpus do not mechanize the general theorems. This document is self-contained and does not require the paper directory.

## Model

A schema is a finite sequence of `int` or `int?` columns. The latter admits a distinguished null value. A finite bag B over a schema is a finite-support function from tuples to natural-number multiplicities. Bag equality includes multiplicity, not order. Equality of tuples, used for multiplicity counting, treats two nulls as equal. In contrast, all comparison predicates return false when either compared field is null; otherwise they implement integer equality, inequality, or strict less-than. This explicitly chosen convention is not a formalization of all SQL null behavior.

A program is a finite acyclic graph whose nodes refer only to earlier nodes. Sources are finite immutable arrays with independently restartable cursors. Restart must reproduce the same order, including duplicates. The graph is a compact syntax representation: a use of a shared node may recompute its expression; there is no implicit shared stream, shared cursor, cache, or single-evaluation guarantee. Operators are typed empty, source, bag sum, product, projection, filter, truncated difference, minimum intersection, maximum union, left outer join, and full outer join. Predicates are pure, deterministic and total. There is no aggregation, cyclic recursion, order observation, source mutation, effectful predicate, cancellation observation, or host-language context.

The evaluator outputs one tuple at a time to a sink that does not feed back into the expression. Source input, program text and output sink are not charged as fast working storage. Program control, cursors, tuples, counters and suspended enumerations are charged as working storage. Slow-memory traffic is separated into source reads R, derived writes W, derived reads L and output writes O. Intermediate materialization traffic is W+L, not R+W+L+O. One modeled source read fetches one occurrence; this is not an assertion about cache misses or disk blocks in Python.

## Denotation

For bags A and B of the same schema and a tuple x, sum has multiplicity A(x)+B(x), difference max(A(x)-B(x),0), intersection min(A(x),B(x), and maximum union max(A(x),B(x)). Product multiplies multiplicities of the two constituent tuples. Projection sums multiplicities of all preimages, including non-injective projections. Filtering retains multiplicities precisely when the predicate holds.

A left outer join emits each matching pair (x,y) with multiplicity A(x)B(y). If no y in the support of B matches a given x, it emits (x,nulls) with multiplicity A(x). A full outer join additionally emits (nulls,y) with multiplicity B(y) for every right tuple without a left match. Contributions to the same resulting tuple are added; in particular, padded results from the two sides can collide on all-null tuples. No duplicate-removal convention is imposed on these outputs.

## Enumerator

Source and empty are immediate. Sum concatenates child enumerations. Projection and filter transform one occurrence at a time. Product opens the right enumeration afresh for each left occurrence. This creates no stored product relation.

For difference or intersection, enumerate A in its deterministic order. For its occurrence at position k with value x, independently enumerate the first k positions of A and count x, obtaining rank rho; independently enumerate all of B and count x, obtaining beta. Difference emits x exactly when rho>beta; intersection emits x exactly when rho<=beta. Counts are discarded after this decision. Prefix enumerators are explicitly closed before the next count or output.

Maximum union first emits all of A, then enumerates B. For a right occurrence y at position k, compute its prefix rank rho within B and its total count alpha in A. Emit y exactly when rho>alpha.

For left join, retain one occurrence x from A, scan B and emit every passing pair; emit one padded x only if this complete scan found no match. Full join does this and then enumerates B again, retaining one y while it rescans A for existence of a match. It emits padded y exactly when that scan finds none. Existence scans may stop early, and must close the scanned child.

## Theorem R1: termination, typing and multiplicity preservation

For every program in the declared fragment and every conforming finite input, a complete replay enumeration terminates and produces exactly the denoted bag, containing only values of the inferred output schema.

Proof. Induct on the topological node index, with the stronger induction hypothesis that every fresh invocation of a child terminates, returns the same deterministic finite sequence, and has the specified bag and schema. Source order is immutable, so the base case holds. A typed empty returns no tuples. Every higher operator invokes only earlier nodes, and invokes each child finitely many times: one, once per child occurrence, or finitely many additional prefix/count scans per occurrence. Each scan terminates by the induction hypothesis. The surrounding finite loops therefore terminate, including early-return existence scans. Determinism of iteration, predicates, rank choices and concatenation establishes the sequence part of the hypothesis.

Sum, product, projection and filtering have the stated multiplicities directly: product enumerates all ordered pairs of child occurrences exactly once; projection does not deduplicate equal projected values. For a fixed x occurring alpha times in A, its successive within-value prefix ranks are exactly 1 through alpha, independently of intervening unequal values. The scan of B returns beta=B(x). There are max(alpha-beta,0) ranks greater than beta and min(alpha,beta) ranks at most beta. These are the two required multiplicities. For maximum union, the first phase emits alpha copies and the second emits max(beta-alpha,0), totaling max(alpha,beta).

For each left tuple value x, the join phase visits every occurrence of x and each right occurrence. Thus a matching value pair has multiplicity A(x)B(y). An unmatched left occurrence is padded exactly once, not once per failed right comparison. The full join's second phase pads exactly the unmatched right occurrences. No matching pair is emitted in that second phase, so none is double-counted. If padding from different phases produces the same value tuple, both copies legitimately contribute to the bag. Projection and predicate formation preserve component types, concatenation constructs the product schema, and nullable padding is accepted by the output schema. All operators therefore establish typing and bag equality. QED.

## Corollary R2: contextual bag equivalence

Replacing an expression by its replay realization preserves observations in any well-typed pure acyclic context built from the declared bag operators, provided the replacement is observed as a finite bag, not by emission order or cost. In particular, this is not equivalence under an arbitrary host-language context.

Proof. Each operator's denotation depends only on its input bags and pure predicates. Theorem R1 supplies equal bags of the same type at the hole. Induction from the hole through the surrounding finite context gives equal root bags. Multiple uses of a hole preserve this property because each use receives the same immutable denotation. This is a semantic substitutivity argument, not a resource-equivalence or evaluation-count assertion. QED.

## Cardinality and counter widths

Assign C(input)=its length and C(empty)=0. For child bounds a,b, let C(sum)=C(max-union)=a+b, C(product)=ab, C(left)=a(b+1), C(full)=ab+a+b, C(diff)=a, and C(inter)=min(a,b). Projection and filter inherit the child's bound. Induction on denotation proves every invocation's output length at most its C. These are upper bounds, not cardinality predictions. Let Cmax be the maximum of the node bounds and input lengths. Every local position, prefix rank and multiplicity count fits in ceil(log2(Cmax+2)) bits, up to a constant number of sentinel bits. Cmax is used only in the proof; the evaluator need not compute or store this global bound.

## Theorem R3: a sufficient logical-frame bound

Define F(input)=F(empty)=1. For unary projection or filter use 1+F(A), and use 1+max(F(A),F(B)) for sum. Product, left join and full join use 1+F(A)+F(B). Difference and intersection use 1+max(2F(A),F(A)+F(B)). Maximum union uses 1+max(F(A),2F(B),F(A)+F(B)). At most F(root) logical replay frames are simultaneously active.

Proof. Count one frame for the current operator. Unary operators suspend one child, while sum finishes one child before starting the next. Product and the first join phase suspend the left enumeration while a right enumeration is active. The second full-join phase exchanges the roles, yielding the same sum. In difference and intersection, the outer A is suspended while a second A computes a rank, or while B computes a total count. These scans are sequential, not concurrent with each other. Maximum union's first phase needs only A; its second phase suspends B while either another B computes a prefix rank or A computes a count. Taking the largest concurrent child sum in each case gives the stated recurrence. Early closing can decrease but never increase these bounds. Shared syntax nodes have separate frames whenever there are concurrent invocations. QED.

Regression witness.  If A is empty and B is a one-element source under four identity projections, then F(A)=1 and F(B)=5.  The actual maximum-union recurrence yields `1+max(1,10,6)=11`; the stale symmetric formula `1+2F(A)+F(B)` would give 8.  Focused tests observe the dynamic peak of 11 and also cover swapped operands and both nesting orders.

## Theorem R4: zero intermediate materialization above a sufficient memory budget

For fixed P, let a be the maximum tuple arity and b bound the bit-width of each input value and each literal. There is an implementation-dependent constant K and finite program/control storage D(P) such that the abstract replay evaluator needs at most

D(P) + K F(P) [(a+1)(b+1) + ceil(log2(Cmax+2))]

bits of working storage, plus a fixed-size output interface. For every memory budget at least this sufficient bound, intermediate materialization traffic is zero. This expression is not claimed minimal or to be the actual byte footprint of a Python process.

Proof. A logical frame contains only a constant number of current or suspended tuple values, local cursors, positions, counts, phase tags and references to fixed syntax. No operator creates data values other than existing components and nulls; product concatenates and projection selects them, so tuple components stay within the input/literal bit-width bound. Each local counter has the bound proved above. Abstract cursors are indexes into immutable source arrays or references to a child frame; reopening allocates no source-sized structure. Theorem R3 bounds simultaneously live frames. Retaining a constant number of fields per frame gives the displayed bound after increasing K and D(P). Every data fetch is from a base source, every derived tuple is passed directly through the active call structure, and every final occurrence is sent directly to the output sink. Consequently W=L=0. Since W+L is nonnegative, zero is the exact minimum of that isolated cost coordinate among implementations admitted by this memory budget. No conclusion follows about the minimum total R+W+L+O. QED.

For a fixed P, each C is bounded by a polynomial in total input length N: the recurrences use only addition, multiplication and domination by such expressions. Thus local counters use O_P(log(N+2)) bits. The degree and F(P) need not be small uniformly in the syntax DAG size. Repeated self-products can double cardinality exponents, and repeated nonmonotone self-use can multiply frame bounds. There is no uniform constant-byte-space result, no guarantee for every positive memory budget, and no practical time bound here. Instrumentation fields in the Python simulator and the materializing Counter test oracle are outside this abstract storage claim.

## Why the result is a boundary, not a new complete-fusion theorem

The construction is an explicit recomputation baseline. It preserves bags and avoids derived relations, but does not eliminate generator allocations, function calls or control overhead. It is not complete fusion in the stronger no-allocation/no-call sense used in staged stream compilation. It does not certify minimum base reads, physical I/O, or an arbitrary semantics-preserving compiler rewrite. It is retained as a falsifier for overly broad materialization-only conjectures, not as a claimed original journal-level result.

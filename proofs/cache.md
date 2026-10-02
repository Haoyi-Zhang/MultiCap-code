# Exact certificates for an occurrence-pair cache model

This document contains handwritten arguments and the interpretation of finite certificates. The checker does not constitute proof-assistant mechanization.

## Machine and observations

Let R={r_0,...,r_(n-1)} and S={s_0,...,s_(m-1)} be distinct occurrence identities, with n,m positive. Payloads may coincide, but identities cannot be compressed, synthesized, or represented by another occurrence. Initially every input occurrence is in immutable slow memory and the fast source-record cache is empty. The cache holds at most M occurrence records. A load of a nonresident occurrence costs one. Eviction is free. A pair (r_i,s_j) can be emitted only when both records are resident. All nm pairs must be emitted exactly once, in any order. Outputs are appended directly, not retained in the cache. There is no intermediate store. The cost reported is source reads only; counting output transfers adds nm to every legal schedule.

These are offline schedules for given n,m,M, not an online machine with an uncharged dynamic ledger. A chosen finite schedule can be compiled to a straight-line list of loads, evictions and pair emissions. Its program text is not counted as source-record cache capacity. The search tracks a set of already emitted pairs only to synthesize and check this trace. If the emission ledger were maintained by an online executor, its storage would have to be charged separately. The upper witnesses certify source-cache capacity only, not total code size or total working bytes.

## Normal form

It suffices to consider schedules that eagerly emit all not-yet-emitted pairs whose endpoints are resident after a load; do not load already resident records; and postpone eviction until a cache miss on a full cache, then evict just one record.

Proof. Moving a legal emission earlier cannot change values, consume a cache slot, constrain future loads, or change the final unordered occurrence output. Redundant resident loads can be removed. For evictions, maintain a normalized cache containing the original schedule's current cache. When the original schedule loads x, the normalized execution may already contain x, requiring no read. Otherwise the original cache after its load has size at most M. If the normalized cache is full, an element outside that original post-load cache exists and may be evicted. Then load x. This preserves the containment invariant and never uses more reads. At each original emission both endpoints are in the normalized cache; the normalized execution can already have emitted that pair, or emit it then. Eagerly emitting any newly available pairs only helps. No state has more than M records, and deletion is needed only at a full-cache load. Thus every legal schedule has a normal-form schedule of no greater cost. QED.

The normal-form state is (C,E), with resident set C and completed pair set E. It is saturated: (C intersect R) times (C intersect S) is contained in E. A transition selects x outside C, evicts nothing if |C|<M or one member if |C|=M, installs x, then adds all cross pairs of the new C to E. Every transition costs one. The start is (empty,empty); a goal has E=R times S.

## Symmetry and exact finite search

Independent permutations of R and S act on both C and E. They preserve capacity, transitions, saturation, start, goals and costs. Therefore the orbit quotient has exactly the same minimum path length as the concrete state graph.

Proof. A concrete path maps to an orbit path. Conversely, consider a quotient path and an already chosen concrete representative of its current state. By definition the next quotient edge is witnessed by a concrete transition from some representative of the current orbit. A permutation maps that representative to the chosen one; applying the same permutation to the transition gives a legal successor in the desired next orbit. Inductively lift the entire path. The start has a unique representative and goals are permutation-invariant. Both projections preserve length. QED.

For finite n,m the graph has at most 2^(n+m+nm) states before imposing capacity and saturation. Breadth-first search on its unit-cost quotient returns a shortest path. This is ordinary finite graph search, not a novel optimization theorem, and its worst-case state bound is exponential. The retained implementation is deliberately limited to 1<=n,m<=3. State variables use n+m cache bits and nm completed-pair bits; the maximum tested instance uses six and nine bits respectively. There are no quantified SMT formulas or external solvers.

## Lower-bound certificates

A certificate gives a finite partial map h from canonical saturated states to positive integers, and gives h=0 for every state absent from the map. It must satisfy: h(start)=q; no goal has positive h; and h(s)<=1+h(t) for every transition out of a state with h(s)>=2. For h(s)=1 the inequality holds automatically since h(t)>=0; for h(s)=0 it also holds automatically. The checker independently generates transitions using sets and independently canonicalizes by permutations.

For any legal quotient path s_0,...,s_k ending in a goal, chaining the inequalities gives h(s_0)<=k+h(s_k)=k. Thus q is a lower bound on every normal-form path. The normal-form theorem lifts it to all legal occurrence schedules. A checked legal trace of q reads reaching every pair supplies the matching upper bound. Search is not trusted by this argument. The trust base comprises the written machine definition, the normal-form and symmetry proofs, the independently implemented checker's correctness, the runtime and the hardware. Only finite checking is executable here.

Breadth-first search constructs h(s)=max(q-d(s),0), where d is shortest distance from the start. Any successor t satisfies d(t)<=d(s)+1, giving h(s)<=1+h(t). The implementation may omit all nonpositive entries. Breadth-first termination upon the first goal has discovered every state of distance below q; such states are exactly those with positive potential. Retaining a concrete representative and its physical parent action when each orbit is first discovered permits reconstruction of a contiguous physically labeled witness.

## Elementary parameterized bounds

### Two slots

For n,m>=1 and M=2, the exact minimum number of reads is nm+1.

Lower bound: the first load completes no pair, and every further load can expose at most one new pair because it coexists with at most one other record. At least nm additional loads are needed. Upper bound: load r_0, traverse every S occurrence, and emit the resulting row. Keep the final S occurrence, load the next R occurrence, emit that pair, and traverse the remaining S occurrences in reverse order. Alternate direction in successive rows. The first row costs m+1 reads; each further row costs one new R and m-1 S reads, or m. Total m+1+(n-1)m=nm+1. All pairs are emitted exactly once. No intermediate records are written. QED.

### One read per occurrence

There exists a schedule reading each occurrence at most once if and only if M>=min(n,m)+1.

Upper bound: retain the entire smaller side and stream each occurrence of the other side once. Lower bound: consider the first eviction. Before it, no loaded record has been evicted. If the evicted record belongs to R, it cannot return and hence must already have met all m members of S. These m records and that R record were all resident immediately before eviction, requiring M>=m+1>=min(n,m)+1. The case of an S eviction is symmetric. If there is no eviction, all n+m records must be simultaneously resident before completion, an even stronger condition. Every vertex is needed because n,m>0 and every pair is required. QED.

### A coarse counting bound

For 2<=M<=n+m, every schedule uses at least

max(n+m, M + ceil((nm-floor(M*M/4))/(M-1)))

reads. If the second numerator is negative, the first bound dominates, so the displayed weaker expression is still valid. At most floor(M*M/4) distinct pairs can be exposed by the first M reads: only at most M distinct endpoints have been loaded, and the product of their side counts is bounded by that value. Each later load exposes at most M-1 new pairs. In addition every input occurrence must be read. These are necessary bounds, not sufficient conditions for scheduling. QED.

## Exact 3 by 3 case

For n=m=M=3 the coarse counting bound is 7. The retained certificate cache-07 proves the exact value 8, using 136 positive potential states and 748 checked local inequalities. Its physical witness loads occurrence identifiers 0,1,3,2,4,5,0,1, with evictions absent,absent,absent,0,1,3,2,0. Here identifiers 0,1,2 denote R and 3,4,5 denote S. It emits all nine pairs. The exact gap of one refutes tightness of this counting argument on that instance; it does not refute the validity of the bound or establish a general closed form for M=3.

A current unsymmetrized recomputation finds distance 8 by breadth-first search with 2,916 discovered states and 25,548 transitions.  The earlier raw pilot record was not retained; `results/pilot.json` states this provenance and must not be presented as the original run.  `run.py check` recomputes and matches all deterministic pilot fields while ignoring CPU/RSS measurements.  The quotient search found 144 states and examined 1,198 transitions.  These are implementation-specific enumeration counts, not query-execution cost or claims of an asymptotic optimization gain.

## Direct lower proof for the 3 by 3 instance

The exact value eight also has a handwritten proof independent of the search and certificate implementation. Represent the residency of a once-loaded record by its closed interval of discrete cache states. At a legal pair emission, the corresponding two intervals (or a residency segment of a reloaded record) intersect.

First consider a schedule at capacity three in which two R records b,c and all three S records are each loaded exactly once. The intervals of b and c must intersect. Otherwise, suppose b ends before c starts. Every S must meet both b and c, so all three S are still resident at the first state containing c. This gives four resident records and is impossible. Let I be the intersection of the b and c intervals.

Each S interval must meet I: an interval meeting both overlapping intervals meets their intersection. The three intersections with I are nonempty and pairwise disjoint, since b,c already occupy two slots throughout I. Order them from left to right and call the middle S record y. Its entire residency interval lies strictly between a point in the first intersection and a point in the third intersection. Otherwise it overlaps the first or third S while b,c are also resident. In particular y is resident only within I. A third R record a can never coexist with y, because b,c,y already fill the cache. Therefore the pair (a,y) cannot be emitted, a contradiction. This argument permits arbitrarily many reloads of a.

Every schedule for three by three reads all six records. A schedule with at most seven reads has at most one record read more than once. If that record is in R, the other two R and all three S satisfy the preceding contradiction. If it is in S, exchange the sides. If no record repeats, choose either side for the same argument. Thus at least eight reads are necessary. The explicit eight-read trace supplies the upper bound. This proof applies to the declared occurrence machine only; no originality or general M=3 formula is claimed.

## Representation boundary

An occurrence certificate is not a lower bound for all implementations producing the same value bag. A concrete counterexample has R=[0,0,0], S=[0,0,0], and capacity two unit records. An implementation required to be correct for arbitrary equal-length arrays can stream R and S once, verify that every value equals one saved representative, and count their lengths; then emit nine copies of (0,0). The saved representative and the current value require only two value-record slots; the emitted pair may reference the same representative twice. If either verification fails it can use a general replay fallback. On this input it reads six values, rather than the occurrence model's ten. Counter storage and code must be accounted for in a byte-based model, but this is enough to show that mandatory distinct occurrence residency is an additional restriction, not a consequence of bag semantics. No claimed lower bound here survives removal of that restriction without a new argument.

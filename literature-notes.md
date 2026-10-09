# Literature calibration and source boundaries

Access dates are 2026-09-14--2026-09-17.  Scholarly sources were read through
publisher eReaders, author manuscripts, institutional repositories, or arXiv
full text.  No paper PDF or third-party research code is redistributed in this
repository.  Publisher pages and bibliographic indexes were used to verify
metadata; they are not experimental dependencies.

## A. Same-venue calibration: twelve TOPLAS articles

The matrix records the article-level pattern used to calibrate exposition.  It
is not a quality ranking and its page counts are bibliographic counts, not a
claim about an official TOPLAS limit.

| Article | Problem and principle | Proof/performance argument | Practical connection | Narrative/visual pattern |
|---|---|---|---|---|
| Fradet & Le Métayer 1991, *Compilation of Functional Languages by Program Transformation*, 13(1):21--51 | Correct and efficient compilation as a sequence of functional transformations | Equational transformations connect source terms to machine-like terms | Sequential functional-language compiler | Language and transformations first; correctness threaded through examples |
| Waters 1991, *Automatic Transformation of Series Expressions into Loops*, 13(1):52--98 | Eliminate intermediate series while retaining compositional syntax | Translation rules plus generated-loop argument | Common Lisp SERIES implementation | Running examples, transformation rules, implementation consequences |
| Debray & Lin 1993, *Cost Analysis of Logic Programs*, 15(5):826--875 | Static worst-case cost in the presence of failure, nondeterminism, and multiple solutions | Recurrence extraction and solution with soundness arguments | Program transformation and parallelizing compilers | Problem-specific semantic obstacles before analysis machinery |
| Sands 1996, *Total Correctness by Local Improvement in the Transformation of Functional Programs*, 18(2):175--234 | Local improvements as a route to global transformation correctness | Operational improvement theorem and derived transformation rules | Deforestation/unfold-fold reasoning | One general theorem followed by applications and limits |
| Aßmann 2000, *Graph Rewrite Systems for Program Optimization*, 22(4):583--637 | Uniform representation of analyses and optimizations | Graph-rewrite specification and correctness discipline | Optimizer construction | Framework, executable method, substantial examples |
| Walker, Crary & Morrisett 2000, *Typed Memory Management via Static Capabilities*, 22(4):701--771 | Safe explicit memory management without lexical region lifetimes | Typed operational semantics, preservation/progress, compiler-oriented calculus | Extensible systems and region management | Capabilities are explicit in types rather than prose assumptions |
| Quilleré & Rajopadhye 2000, *Optimizing Memory Usage in the Polyhedral Model*, 22(5):773--815 | Reduce residual memory for a fixed affine schedule | Tight constructive bounds on independent projection vectors | Alpha compiler and generated examples | Exact theorem paired with constructive allocation algorithm |
| Kalvala, Warburton & Lacey 2009, *Program Transformations Using Temporal Logic Side Conditions*, 31(4):1--48 | Trustworthy optimization with declarative side conditions | Temporal-logic formulation and transformation strategies | Transformational case study | Formal side-condition language, then end-to-end optimization case |
| Hoffmann, Aehlig & Hofmann 2012, *Multivariate Amortized Resource Analysis*, 34(3):14:1--14:62 | Automatic multivariate polynomial resource bounds | Resource-aware type system, soundness, inference constraints | Prototype and program corpus | General resource principle, inference algorithm, evaluation |
| Nandivada et al. 2013, *A Transformation Framework for Optimizing Task-Parallel Programs*, 35(1):3:1--3:48 | Reduce task creation/termination overhead while preserving exceptions | Dependence/happens-before analyses and legality proofs | Habanero-Java transformations and measurements | Semantics-sensitive legality before performance evidence |
| Jangda & Bondhugula 2020, *An Effective Fusion and Tile Size Model for PolyMage*, 42(3):12:1--12:27 | Choose fusion groups and tile sizes under interacting locality/parallelism effects | Dynamic program driven by a concrete cost model | PolyMage/Halide image pipelines on multicore systems | Model, algorithm, ablations, performance comparison |
| Frohn et al. 2020, *Inferring Lower Runtime Bounds for Integer Programs*, 42(3):13:1--13:50 | Automatic worst-case lower bounds beyond tail recursion | Under-approximating transformations, acceleration, calculus, SMT encoding | LoAT implementation and benchmark evaluation | Formal lower-bound pipeline, explicit soundness, broad evaluation |

**Calibration used in this article.**  The main text states the machine before
its bound (Walker; Quilleré; Frohn), places one reusable theorem before special
cases (Sands), couples lower bounds to constructive witnesses (Quilleré), and
keeps finite checker evidence separate from general proofs (Debray; Hoffmann;
Frohn).  It does not imitate the outline or wording of any one article.

## B. Five foundational or demonstrably influential fusion/resource papers

| Work | Why it matters here | Boundary retained |
|---|---|---|
| Wadler 1990, *Deforestation* | Establishes removal of intermediate trees by semantics-preserving transformation | No bounded-memory optimality theorem is attributed to it |
| Gill, Launchbury & Peyton Jones 1993, *A Short Cut to Deforestation* | Local producer/consumer rule and compiler implementation | Applies to a typed list representation, not arbitrary bags |
| Coutts, Leshchinskiy & Stewart 2007, *Stream Fusion* | Exposes a stream representation designed to eliminate intermediate lists | Performance/representation result, not a universal materialization lower bound |
| Kiselyov et al. 2017, *Stream Fusion, to Completeness* | Makes a precise completeness claim relative to a stream language/normalization method | “Complete” is representation-relative; stateful extensions need more machinery |
| Hong & Kung 1981, *The Red-Blue Pebble Game* | Canonical machine-dependent I/O lower-bound framework | Its graph/memory rules must be declared before importing a bound |

## C. Five closest adjacent papers

| Work | Exact inspected scope | Delta to this article |
|---|---|---|
| Dong & Kjolstad 2026, *A Compiler for Fused Relational Operations on Multisets* | Full 25-page article; iteration machines, ALIR, layouts, reset, temporary storage and evaluation sections | Concrete bag-fusion compiler; does not give the capability-indexed no-go theorem or the two exact barrier optima developed here |
| Kovach et al. 2023, *Indexed Streams* | Full paper/author materials on the formal IR and contraction fusion | Formal fused contraction IR; not a bounded-memory materialization optimum across capability signatures |
| Dalvi et al. 2003, *Pipelining in Multi-Query Optimization* | Execution model, validity conditions, algorithms and evaluation | Shared query pipelines with explicit access constraints; not typed bag resource semantics or exact rank/state bounds |
| Fournier et al. 2019, *Nonnegative Rank Measures and Monotone Algebraic Branching Programs* | Full 14-page LIPIcs paper | Establishes rank/monotone-computation connections and warns that rank characterizations depend on model depth; this article does not rename those measures as new |
| Gouveia & Wiebe 2026, *Matrices of Nonnegative Integer Rank Two* | Full current preprint, including geometric reduction and algorithmic discussion | Studies the integer-rank decision problem itself; this article uses the established measure as an operational invariant under a declared positive barrier |

## D. Strongest-work comparison and novelty boundary

The closest 2026 multiset compiler demonstrates that bag operators can be fused
through an iteration-machine/ALIR pipeline and explicitly identifies cases where
its chosen representation uses temporary storage.  It does not imply that such
storage is unavoidable under every source or representation capability.  The
fusion literature likewise makes completeness claims relative to particular
stream languages.  Communication/state complexity and nonnegative-rank work
already supply the mathematical measures used by two of our specializations.

Accordingly, the paper does **not** claim to invent residual equivalence,
communication complexity, nonnegative integer rank, replay, or pebbling.  Its
retained contribution is the capability-indexed resource semantics that makes
those model assumptions first-class, the strict same-denotation separations,
and two exact lower/upper specializations integrated with proof-producing bag
compilers.  A claim that rank alone characterizes arbitrary multiset fusion, or
that temporary storage in one compiler proves universal necessity, is excluded.

## E. Source and rule limitations

The TOPLAS and general ACM author-guideline URLs returned access failures during
the final 2026-09-15 recheck.  The supplied `acmart` class identifies itself as
version 2.20 dated 2026-08-16 and was retained byte-for-byte.  The 50-page total
is the supplied internal planning contract, not a publisher maximum.  Initial
upload slots, live anonymity rules, open-access charges, and venue-specific
external-use declarations therefore remain a pre-submission human recheck, not
a scientific gap in the internal article.


## F. Complete bibliography audit

The manuscript contains 81 scholarly references, and every bibliography
entry is cited in the text.  The machine-readable `reference-audit.csv` has one
row for each key, recording title, year, entry type, persistent identifier,
verification basis, access date, technical role, and manuscript location.  The
paper-side `check_bibliography.py` rejects undefined or uncited keys, duplicate
DOI values, missing core metadata, entries without a DOI or stable scholarly
URL, and any mismatch between the BibTeX file and the audit.  The final static
report has 81 entries, 81 cited keys, 81 persistent identifiers, 75 distinct DOI
values, six stable scholarly URLs, and zero errors.

Verification depth is recorded rather than overstated.  The closest-work and
calibration papers were read through full text where available; some broader
context entries were checked against publisher, institutional, author, DBLP, or
DOI metadata and then used only for the technical role stated in the audit.
Web pages and author guidelines are workflow evidence, not manuscript
substitutes for scholarship.  No reference is included solely to raise the
count.

The final audit also repaired concrete metadata defects found during source
reconciliation: the SDQL TOPLAS article number is 89; the Yannakakis extension-
complexity article is dated 1988; the TACO workspace paper uses IEEE DOI
`10.1109/CGO.2019.8661185`; the Umbra CIDR paper is seven pages; and a weakly
related matrix-rank citation was removed rather than padded into the related-
work section.  These repairs are reflected in both `references.bib` and the
reference audit.

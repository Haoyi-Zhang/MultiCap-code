"""Exact nonnegative-integer factorization rank for bounded tiny matrices.

For a target A, every factor column/row contributes a nonzero integer rank-one
atom R <= A.  Dynamic programming over all elementwise residual matrices finds
the minimum number of atoms.  The emitted certificate contains both a witness
and a Bellman potential over every residual state; integer_rank_check.py checks
it using independently generated atoms and transitions.
"""
from __future__ import annotations
from functools import lru_cache
from itertools import product
from typing import Any

Matrix=tuple[tuple[int,...],...]


def nat(value: Any, label: str = 'value') -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f'{label} must be a natural integer')
    return value


def as_matrix(value) -> Matrix:
    if not isinstance(value,(list,tuple)) or not value or not isinstance(value[0],(list,tuple)) or not value[0]:
        raise ValueError('nonempty rectangular matrix required')
    width=len(value[0]);rows=[]
    for i,row in enumerate(value):
        if not isinstance(row,(list,tuple)) or len(row)!=width:
            raise ValueError('nonempty rectangular matrix required')
        rows.append(tuple(nat(x,f'matrix[{i}][{j}]') for j,x in enumerate(row)))
    return tuple(rows)


def nat_vector(value,length:int,label:str)->tuple[int,...]:
    if not isinstance(value,(list,tuple)) or len(value)!=length:
        raise ValueError(f'{label} dimension mismatch')
    return tuple(nat(x,f'{label}[{i}]') for i,x in enumerate(value))


def zero_like(a: Matrix) -> Matrix:
    return tuple(tuple(0 for _ in row) for row in a)


def leq(a: Matrix,b: Matrix)->bool:
    return all(x<=y for ra,rb in zip(a,b) for x,y in zip(ra,rb))


def sub(a:Matrix,b:Matrix)->Matrix:
    if not leq(b,a):raise ValueError('negative residual')
    return tuple(tuple(x-y for x,y in zip(ra,rb)) for ra,rb in zip(a,b))


def add(a:Matrix,b:Matrix)->Matrix:
    return tuple(tuple(x+y for x,y in zip(ra,rb)) for ra,rb in zip(a,b))


def outer(u:tuple[int,...],v:tuple[int,...])->Matrix:
    return tuple(tuple(x*y for y in v) for x in u)


def atoms_for(target: Matrix) -> list[tuple[Matrix,tuple[int,...],tuple[int,...]]]:
    m,n=len(target),len(target[0]);mx=max(max(r) for r in target)
    if mx==0:return []
    seen={}
    for u in product(range(mx+1),repeat=m):
        if not any(u):continue
        for v in product(range(mx+1),repeat=n):
            if not any(v):continue
            r=outer(u,v)
            if any(any(row) for row in r) and leq(r,target) and r not in seen:
                seen[r]=(tuple(u),tuple(v))
    return [(r,*seen[r]) for r in sorted(seen)]


def all_residuals(target:Matrix):
    flat=[x for row in target for x in row]
    m,n=len(target),len(target[0])
    for values in product(*[range(x+1) for x in flat]):
        yield tuple(tuple(values[i*n+j] for j in range(n)) for i in range(m))


def solve_rank(value) -> dict:
    a=as_matrix(value);zero=zero_like(a);atoms=atoms_for(a)
    @lru_cache(maxsize=None)
    def opt(state:Matrix):
        if state==zero:return (0,())
        best=None
        # Deterministic atom order makes results stable.
        for idx,(r,_u,_v) in enumerate(atoms):
            if leq(r,state):
                d,path=opt(sub(state,r));candidate=(1+d,(idx,)+path)
                if best is None or candidate[0]<best[0] or (candidate[0]==best[0] and candidate[1]<best[1]):
                    best=candidate
        if best is None:raise RuntimeError('unit atoms should make nonzero state reachable')
        return best
    rank,path=opt(a)
    potential=[]
    for state in all_residuals(a):
        d,_=opt(state);potential.append({'state':[list(r) for r in state],'value':d})
    witness=[]
    state=a
    for idx in path:
        r,u,v=atoms[idx]
        witness.append({'u':list(u),'v':list(v),'atom':[list(row) for row in r]})
        state=sub(state,r)
    assert state==zero
    return {'matrix':[list(r) for r in a],'rows':len(a),'cols':len(a[0]),
            'rank':rank,'witness':witness,'potential':potential,
            'atom_count':len(atoms),'model':'nonnegative integer factorization rank'}


def _schedule_factors(packet:dict)->tuple[Matrix,list[tuple[tuple[int,...],tuple[int,...]]]]:
    if not isinstance(packet,dict):raise ValueError('factor packet must be an object')
    a=as_matrix(packet.get('matrix'));m,n=len(a),len(a[0])
    if 'rows' in packet and nat(packet['rows'],'rows')!=m:raise ValueError('row mismatch')
    if 'cols' in packet and nat(packet['cols'],'cols')!=n:raise ValueError('column mismatch')
    witness=packet.get('witness')
    if not isinstance(witness,list):raise ValueError('witness must be a list')
    factors=[];total=[[0]*n for _ in range(m)]
    for ell,f in enumerate(witness):
        if not isinstance(f,dict):raise ValueError('factor must be an object')
        u=nat_vector(f.get('u'),m,f'factor {ell} u');v=nat_vector(f.get('v'),n,f'factor {ell} v')
        atom=outer(u,v)
        if 'atom' in f and as_matrix(f['atom'])!=atom:raise ValueError('factor atom mismatch')
        for i in range(m):
            for j in range(n):total[i][j]+=atom[i][j]
        factors.append((u,v))
    if tuple(tuple(row) for row in total)!=a:raise ValueError('witness does not factor matrix')
    return a,factors


def compile_fragments(packet:dict,x:list[int],y:list[int],fast_words:int)->dict:
    """Generate and execute the fixed two-phase/two-buffer factor schedule.

    Prefix phase: T0 accumulates one left summary at a time; T1 is unused.  The
    first min(M,r) summaries are retained in fixed fast slots and the rest are
    written once to fixed slow slots.  The barrier clears both transient
    buffers and makes x inaccessible.  Continuation phase: T0 is the sole
    output accumulator and T1 holds one right linear form.  A persistent
    summary is consumed by one fused read/multiply-add, so no third transient
    value exists.  The final output channel is append-only and unreadable.
    """
    matrix,factors=_schedule_factors(packet);m,n=len(matrix),len(matrix[0])
    xv=nat_vector(x,m,'x');yv=nat_vector(y,n,'y');M=nat(fast_words,'fast_words')
    width=len(factors);fast_count=min(M,width)
    events=[];fast={};slow={};summaries=[]
    # Prefix phase.  T0 is live; T1 is deliberately unused.
    for ell,(u,_v) in enumerate(factors):
        events.append({'op':'prefix_reset','factor':ell,'temp':'T0'});t0=0
        for i,c in enumerate(u):
            events.append({'op':'prefix_madd','factor':ell,'x_index':i,'coefficient':c,'temp':'T0'})
            t0+=c*xv[i]
        summaries.append(t0)
        if ell<fast_count:
            events.append({'op':'keep_fast','factor':ell,'slot':ell,'from':'T0'});fast[ell]=t0
        else:
            slot=ell-fast_count
            events.append({'op':'write_slow','factor':ell,'slot':slot,'from':'T0'});slow[slot]=t0
    events.append({'op':'barrier','clears':['T0','T1']})
    # The barrier clears both transient values.  The continuation starts fresh.
    t0=0;events.append({'op':'output_reset','temp':'T0'});fragments=[]
    for ell,(_u,v) in enumerate(factors):
        events.append({'op':'right_reset','factor':ell,'temp':'T1'});t1=0
        for j,c in enumerate(v):
            events.append({'op':'right_madd','factor':ell,'y_index':j,'coefficient':c,'temp':'T1'})
            t1+=c*yv[j]
        if ell<fast_count:
            events.append({'op':'accumulate_fast','factor':ell,'slot':ell,'right_temp':'T1','output_temp':'T0'})
            term=fast[ell]*t1
        else:
            slot=ell-fast_count
            events.append({'op':'read_slow_madd','factor':ell,'slot':slot,'right_temp':'T1','output_temp':'T0'})
            term=slow[slot]*t1
        t0+=term;fragments.append(term)
    events.append({'op':'emit','from':'T0','channel':'append_only'})
    slow_count=width-fast_count
    return {'value':t0,'summaries':summaries,'fragments':fragments,'factor_width':width,
            'fast_words':M,'fast_slots_used':fast_count,'slow_slots_used':slow_count,
            'slow_writes':slow_count,'slow_reads':slow_count,
            'temporary_word_transfers':2*slow_count,'transient_buffers':2,
            'barrier_clears':['T0','T1'],'output_channel':'append_only','events':events}


def bilinear(matrix:list[list[int]],x:list[int],y:list[int])->int:
    a=as_matrix(matrix);xv=nat_vector(x,len(a),'x');yv=nat_vector(y,len(a[0]),'y')
    return sum(a[i][j]*xv[i]*yv[j] for i in range(len(xv)) for j in range(len(yv)))

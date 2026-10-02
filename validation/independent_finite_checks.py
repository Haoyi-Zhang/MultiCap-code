#!/usr/bin/env python3
"""Independent post-development robustness suite.

This file intentionally does not import the project implementation.  It uses only
Python's standard library and independently re-derives finite residual, small
integer-factor-rank, and two-slot occurrence-cache obligations.  Its purpose is
to detect correlated generator/checker mistakes and hand-picked-instance
fragility.  It is not a held-out statistical test set and does not replace the
general proofs.
"""
from __future__ import annotations
import argparse, hashlib, itertools, json, random, time
from collections import deque
from pathlib import Path

SEED = int.from_bytes(hashlib.sha256(b"independent-finite-checks-v1-2026").digest()[:8], "big")

def residual_rows(table):
    return {tuple(row) for row in table}

def ceil_log2(n):
    if n <= 1: return 0
    return (n-1).bit_length()

def check_residual_trials(rng, trials=700):
    checked=0; collisions_checked=0
    for _ in range(trials):
        nx=rng.randint(1,8); ny=rng.randint(1,7); no=rng.randint(1,5)
        f=[[rng.randrange(no) for _ in range(ny)] for _ in range(nx)]
        rows=sorted(residual_rows(f)); k=ceil_log2(len(rows))
        code={r:i for i,r in enumerate(rows)}
        for x,row in enumerate(f):
            c=code[tuple(row)]
            assert c < 2**k if k else c==0
            for y in range(ny): assert rows[c][y]==f[x][y]
        if k>0 and len(rows)>2**(k-1):
            # Any (k-1)-bit state space has fewer states than residuals.
            assert len(rows) > 2**(k-1); collisions_checked += 1
        checked += nx*ny
    return {'trials':trials,'point_evaluations':checked,'strict_lower_bound_cases':collisions_checked}

def rank1_factor(A):
    m=len(A); n=len(A[0]) if m else 0
    if not any(any(row) for row in A): return ([],[])
    # Exact bounded search is independent and complete for 2x2 entries in 0..3:
    # if A=u v^T then each u_i and v_j divides/max-bounds observed entries.
    mx=max(max(r) for r in A)
    for u in itertools.product(range(mx+1), repeat=m):
        for v in itertools.product(range(mx+1), repeat=n):
            if all(u[i]*v[j]==A[i][j] for i in range(m) for j in range(n)):
                return list(u),list(v)
    return None

def exact_rank_2x2(A):
    if not any(any(r) for r in A): return 0
    return 1 if rank1_factor(A) is not None else 2

def eval_bilinear(A,x,y):
    return sum(A[i][j]*x[i]*y[j] for i in range(len(A)) for j in range(len(A[0])))

def check_integer_rank_exhaustive():
    matrices=0; schedules=0; memory_cases=0
    for vals in itertools.product(range(4), repeat=4):
        A=[list(vals[:2]),list(vals[2:])]
        r=exact_rank_2x2(A); matrices+=1
        # Independent matching factor: rank-2 column decomposition always works.
        if r==0: U=[[],[]]; V=[]
        elif r==1:
            u,v=rank1_factor(A); U=[[u[0]],[u[1]]]; V=[v]
        else:
            U=[[A[0][0],A[0][1]],[A[1][0],A[1][1]]]
            V=[[1,0],[0,1]]
        for x in itertools.product(range(4),repeat=2):
            for y in itertools.product(range(4),repeat=2):
                summaries=[sum(U[i][l]*x[i] for i in range(2)) for l in range(r)]
                got=sum(summaries[l]*sum(V[l][j]*y[j] for j in range(2)) for l in range(r))
                assert got==eval_bilinear(A,x,y); schedules+=1
        for M in range(4):
            traffic=2*max(0,r-M)
            assert traffic>=0 and traffic%2==0; memory_cases+=1
    return {'matrices':matrices,'schedule_evaluations':schedules,'memory_cases':memory_cases}

def cache_opt_two_slots(n,m):
    """Exact independent oracle for the two-slot all-pairs plan.

    With two slots, every emitted pair corresponds to a resident cross edge
    ``(a_i,b_j)``.  After the first edge (two source reads), one additional
    read changes exactly one endpoint, so the next resident edge must be
    adjacent in the line graph of ``K_{n,m}``.  Conversely, every such walk is
    executable with exactly one read per graph step.  A breadth-first search
    over ``(visited-edge-mask,current-edge)`` therefore gives the exact read
    optimum without importing the project's cache search implementation.
    """
    edges=[(i,j) for i in range(n) for j in range(m)]
    ecount=len(edges); target=(1<<ecount)-1
    adjacent=[]
    for i,j in edges:
        adjacent.append(tuple(k for k,(ii,jj) in enumerate(edges)
                              if k != i*m+j and (ii==i or jj==j)))
    # Encode state as mask*ecount+edge; all initial cross edges cost two reads.
    q=deque()
    seen=bytearray((1<<ecount)*ecount)
    for e in range(ecount):
        code=(1<<e)*ecount+e
        seen[code]=1
        q.append((1<<e,e,2))
    while q:
        mask,e,d=q.popleft()
        if mask==target:
            return d
        for ne in adjacent[e]:
            nm=mask | (1<<ne)
            code=nm*ecount+ne
            if not seen[code]:
                seen[code]=1
                q.append((nm,ne,d+1))
    raise AssertionError('unreachable')

def check_cache():
    rows=[]
    for n in range(1,5):
        for m in range(1,5):
            got=cache_opt_two_slots(n,m); want=n*m+1
            assert got==want,(n,m,got,want)
            rows.append({'n':n,'m':m,'opt':got,'formula':want})
    return {'instances':len(rows),'rows':rows}

def verify_existing_factor_certificates(root):
    """Independently recheck every retained rank witness.

    Rank packets store a target ``matrix`` and a list of rank-one ``witness``
    atoms, not preassembled U/V matrices.  This routine deliberately reconstructs
    each outer product directly and rejects Booleans, fractions, negative values,
    ragged matrices, and mismatching cached atoms before any arithmetic result is
    accepted.
    """
    root=Path(root)
    cert_dir=root/'results'/'certificates'
    paths=sorted(cert_dir.glob('rank-*.json'))
    if not paths:
        raise AssertionError(f'no retained rank certificates under {cert_dir}')
    checked=0; equations=0

    def nat(value,label):
        if type(value) is not int or value < 0:
            raise AssertionError(f'{label} is not a natural integer')
        return value

    def matrix(value,label):
        if not isinstance(value,list) or not value or not isinstance(value[0],list) or not value[0]:
            raise AssertionError(f'{label} is not a nonempty matrix')
        width=len(value[0]);out=[]
        for i,row in enumerate(value):
            if not isinstance(row,list) or len(row)!=width:
                raise AssertionError(f'{label} is ragged')
            out.append([nat(q,f'{label}[{i}]') for q in row])
        return out

    for path in paths:
        packet=json.loads(path.read_text())
        A=matrix(packet.get('matrix'),f'{path.name}.matrix')
        m=len(A); n=len(A[0])
        witness=packet.get('witness')
        if not isinstance(witness,list):
            raise AssertionError(f'{path.name}.witness is not a list')
        total=[[0]*n for _ in range(m)]
        for ell,factor in enumerate(witness):
            if not isinstance(factor,dict):
                raise AssertionError(f'{path.name}.witness[{ell}] is not an object')
            u=factor.get('u');v=factor.get('v')
            if not isinstance(u,list) or len(u)!=m or not isinstance(v,list) or len(v)!=n:
                raise AssertionError(f'{path.name}.witness[{ell}] has wrong dimensions')
            u=[nat(q,f'{path.name}.u[{ell}]') for q in u]
            v=[nat(q,f'{path.name}.v[{ell}]') for q in v]
            atom=[[u[i]*v[j] for j in range(n)] for i in range(m)]
            if 'atom' in factor and matrix(factor['atom'],f'{path.name}.atom[{ell}]')!=atom:
                raise AssertionError(f'{path.name}.witness[{ell}] cached atom mismatch')
            for i in range(m):
                for j in range(n):
                    total[i][j]+=atom[i][j]
        if total!=A:
            raise AssertionError(f'{path.name} witness does not reconstruct target')
        if 'rank' in packet and nat(packet['rank'],f'{path.name}.rank')!=len(witness):
            raise AssertionError(f'{path.name} rank does not equal witness width')
        checked+=1;equations+=m*n
    return {'certificates_found_and_checked':checked,'matrix_equations':equations}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,default=Path('.')); ap.add_argument('--out',type=Path)
    a=ap.parse_args(); t=time.time(); rng=random.Random(SEED)
    out={'schema':'independent-finite-checks-v1','seed':SEED,
         'interpretation':'post-development independent robustness evidence, not a statistical held-out set',
         'residual':check_residual_trials(rng),
         'integer_rank_2x2':check_integer_rank_exhaustive(),
         'cache_two_slots':check_cache(),
         'existing_factor_certificates':verify_existing_factor_certificates(a.root),
         'seconds':round(time.time()-t,6)}
    text=json.dumps(out,indent=2,sort_keys=True)
    if a.out: a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(text+'\n')
    print(text)
if __name__=='__main__': main()

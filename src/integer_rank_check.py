"""Independent checker for tiny nonnegative-integer rank certificates."""
from __future__ import annotations
from itertools import product
from typing import Any


def nat(value:Any,label:str)->int:
    if type(value) is not int or value<0:raise ValueError(f'{label} must be a natural integer')
    return value


def mat(value,label='matrix'):
    if not isinstance(value,(list,tuple)) or not value or not isinstance(value[0],(list,tuple)) or not value[0]:
        raise ValueError(f'{label}: bad matrix')
    width=len(value[0]);rows=[]
    for i,row in enumerate(value):
        if not isinstance(row,(list,tuple)) or len(row)!=width:raise ValueError(f'{label}: bad matrix')
        rows.append(tuple(nat(x,f'{label}[{i}][{j}]') for j,x in enumerate(row)))
    return tuple(rows)


def vector(value,length,label):
    if not isinstance(value,(list,tuple)) or len(value)!=length:raise ValueError(f'{label}: dimensions')
    return tuple(nat(x,f'{label}[{i}]') for i,x in enumerate(value))


def outer(u,v):return tuple(tuple(x*y for y in v) for x in u)
def leq(a,b):return all(x<=y for ra,rb in zip(a,b) for x,y in zip(ra,rb))
def subtract(a,b):return tuple(tuple(x-y for x,y in zip(ra,rb)) for ra,rb in zip(a,b))
def plus(a,b):return tuple(tuple(x+y for x,y in zip(ra,rb)) for ra,rb in zip(a,b))


def independent_atoms(target):
    m,n=len(target),len(target[0]);mx=max(max(r) for r in target);found={}
    # Different loop nesting and canonicalization from the solver.
    for v in product(range(mx+1),repeat=n):
        for u in product(range(mx+1),repeat=m):
            if not any(u) or not any(v):continue
            r=outer(u,v)
            if any(z for row in r for z in row) and leq(r,target):
                old=found.get(r);pair=(u,v)
                if old is None or pair<old:found[r]=pair
    return found


def check_rank(packet):
    if not isinstance(packet,dict):raise ValueError('packet must be an object')
    a=mat(packet.get('matrix'));m,n=len(a),len(a[0]);zero=tuple(tuple(0 for _ in range(n)) for _ in range(m))
    if nat(packet.get('rows'),'rows')!=m or nat(packet.get('cols'),'cols')!=n:raise ValueError('dimensions')
    rank=nat(packet.get('rank'),'rank');atom_count=nat(packet.get('atom_count'),'atom_count')
    witness=packet.get('witness');potential=packet.get('potential')
    if not isinstance(witness,list) or not isinstance(potential,list):raise ValueError('witness and potential must be lists')
    atoms=independent_atoms(a)
    if atom_count!=len(atoms):raise ValueError('atom count mismatch')
    total=zero
    for ell,f in enumerate(witness):
        if not isinstance(f,dict):raise ValueError('bad factor')
        u=vector(f.get('u'),m,f'factor {ell} u');v=vector(f.get('v'),n,f'factor {ell} v');r=mat(f.get('atom'),f'factor {ell} atom')
        if r!=outer(u,v) or r not in atoms:raise ValueError('bad factor')
        total=plus(total,r)
    if total!=a or len(witness)!=rank:raise ValueError('bad upper witness')
    potentials={}
    for index,item in enumerate(potential):
        if not isinstance(item,dict):raise ValueError('bad potential item')
        state=mat(item.get('state'),f'potential {index} state');value=nat(item.get('value'),f'potential {index} value')
        if state in potentials:raise ValueError('duplicate potential state')
        potentials[state]=value
    expected=1
    for row in a:
        for x in row:expected*=x+1
    if len(potentials)!=expected or potentials.get(zero)!=0 or potentials.get(a)!=rank:
        raise ValueError('incomplete potential')
    inequalities=0
    for s,h in potentials.items():
        if s!=zero and h<1:raise ValueError('nonzero state has zero potential')
        for r in atoms:
            if leq(r,s):
                nxt=subtract(s,r)
                if nxt not in potentials:raise ValueError('successor omitted')
                if h>1+potentials[nxt]:raise ValueError('potential can drop by more than one')
                inequalities+=1
    return {'rank':rank,'witness_factors':len(witness),
            'potential_states':len(potentials),'checked_inequalities':inequalities,
            'independent_atoms':len(atoms)}

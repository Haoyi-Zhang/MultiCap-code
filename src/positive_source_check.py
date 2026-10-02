"""Finite monomial-quotient checker independent of numeric probes."""
from __future__ import annotations

C=('c',);BAD=('bad',)

def plus(a,b,cap):
    out=dict(a)
    for k,v in b.items():out[k]=min(cap,out.get(k,0)+v)
    return {k:v for k,v in out.items() if v}

def keymul(a,b):
    if a==C:return b
    if b==C:return a
    if a==BAD or b==BAD:return BAD
    if a[0]=='x' and b[0]=='y':return ('xy',a[1],b[1])
    if a[0]=='y' and b[0]=='x':return ('xy',b[1],a[1])
    return BAD

def times(a,b,cap):
    out={}
    for ka,va in a.items():
        for kb,vb in b.items():
            k=keymul(ka,kb);out[k]=min(cap,out.get(k,0)+va*vb)
    return {k:v for k,v in out.items() if v}

def interpret(node,m,n,cap,depth=0):
    if depth>256:raise ValueError('depth')
    op=node.get('op')
    if op=='const':
        v=node.get('value')
        if type(v) is not int or v<0:raise ValueError('constant')
        return {} if v==0 else {C:min(cap,v)}
    if op in ('x','y'):
        i=node.get('index');limit=m if op=='x' else n
        if type(i) is not int or not(0<=i<limit):raise ValueError('variable')
        return {(op,i):1}
    if op in ('add','mul'):
        a=interpret(node['left'],m,n,cap,depth+1);b=interpret(node['right'],m,n,cap,depth+1)
        return plus(a,b,cap) if op=='add' else times(a,b,cap)
    raise ValueError('operator')

def quotient_extract(source,max_coefficient=8):
    m=source['left_tags'];n=source['right_tags'];cap=max_coefficient+1
    p=interpret(source['expression'],m,n,cap)
    forbidden=[k for k,v in p.items() if v and (k==C or k==BAD or k[0] in ('x','y'))]
    if forbidden:raise ValueError('non-bilinear monomial present')
    matrix=[[p.get(('xy',i,j),0) for j in range(n)] for i in range(m)]
    if any(v>max_coefficient for row in matrix for v in row):raise ValueError('coefficient cap')
    return {'matrix':matrix,'abstract_terms':len(p),'coefficient_cap':max_coefficient}

"""Small positive arithmetic source language and complete bilinear probes.

An expression denotes the multiplicity of a singleton output bag.  Operators
are natural constants, input-tag counts, addition, and multiplication.  This is
an executable admission front end for the matrix theorem, not a general SQL IR.
"""
from __future__ import annotations


def _nat(value,label):
    if type(value) is not int or value<0:raise ValueError(f'{label} must be a natural integer')
    return value

def const(c):return {'op':'const','value':_nat(c,'constant')}
def xvar(i):return {'op':'x','index':_nat(i,'left variable index')}
def yvar(j):return {'op':'y','index':_nat(j,'right variable index')}
def add(a,b):return {'op':'add','left':a,'right':b}
def mul(a,b):return {'op':'mul','left':a,'right':b}


def canonical_source(matrix):
    if not isinstance(matrix,(list,tuple)) or not matrix or not isinstance(matrix[0],(list,tuple)) or not matrix[0]:
        raise ValueError('nonempty rectangular matrix required')
    n=len(matrix[0])
    if any(not isinstance(row,(list,tuple)) or len(row)!=n for row in matrix):
        raise ValueError('rectangular matrix required')
    m=len(matrix);expr=const(0)
    for i in range(m):
        for j in range(n):
            c=_nat(matrix[i][j],f'matrix[{i}][{j}]')
            if c:
                expr=add(expr,mul(mul(const(c),xvar(i)),yvar(j)))
    return {'left_tags':m,'right_tags':n,'expression':expr}


def validate(node,m,n,depth=0):
    if depth>256:raise ValueError('expression depth cap')
    op=node.get('op')
    if op=='const':
        if type(node.get('value')) is not int or node['value']<0:raise ValueError('bad constant')
        return 1
    if op in ('x','y'):
        k=node.get('index');limit=m if op=='x' else n
        if type(k) is not int or not (0<=k<limit):raise ValueError('bad variable')
        return 1
    if op in ('add','mul'):
        return 1+validate(node['left'],m,n,depth+1)+validate(node['right'],m,n,depth+1)
    raise ValueError('bad op')


def evaluate(node,x,y,cap=None):
    op=node['op']
    if op=='const':v=node['value']
    elif op=='x':v=x[node['index']]
    elif op=='y':v=y[node['index']]
    else:
        a=evaluate(node['left'],x,y,cap);b=evaluate(node['right'],x,y,cap)
        v=a+b if op=='add' else a*b
    return min(cap,v) if cap is not None else v


def probe_extract(source,max_coefficient=8):
    m=source['left_tags'];n=source['right_tags'];expr=source['expression']
    nodes=validate(expr,m,n)
    zero_x=[0]*m;zero_y=[0]*n;one_x=[1]*m;one_y=[1]*n
    matrix=[]
    for i in range(m):
        row=[]
        for j in range(n):
            x=[0]*m;y=[0]*n;x[i]=1;y[j]=1
            value=evaluate(expr,x,y,max_coefficient+1)
            if value>max_coefficient:raise ValueError('coefficient cap exceeded')
            row.append(value)
        matrix.append(row)
    total=sum(map(sum,matrix));cap=2*total+1
    observations=[
        (zero_x,one_y,0),(one_x,zero_y,0),(one_x,one_y,total),
        ([2]*m,one_y,2*total),(one_x,[2]*n,2*total)]
    for x,y,want in observations:
        if evaluate(expr,x,y,cap)!=want:raise ValueError('positive bilinearity probe failed')
    return {'matrix':matrix,'nodes':nodes,'probes':m*n+5,'coefficient_cap':max_coefficient}

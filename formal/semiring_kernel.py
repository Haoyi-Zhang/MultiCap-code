"""Independent natural-semiring normalization for extracted factor schedules."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple,Union,Any

@dataclass(frozen=True)
class Const: value:int
@dataclass(frozen=True)
class Var: name:str
@dataclass(frozen=True)
class Add: left:'Expr'; right:'Expr'
@dataclass(frozen=True)
class Mul: left:'Expr'; right:'Expr'
Expr=Union[Const,Var,Add,Mul]
Monomial=Tuple[str,...]
Polynomial=dict[Monomial,int]


def _nat(value:Any,label:str)->int:
    if type(value) is not int or value<0:raise ValueError(f'{label} must be a natural integer')
    return value


def normalize(e:Expr)->Polynomial:
    if isinstance(e,Const):
        value=_nat(e.value,'constant')
        return {} if value==0 else {():value}
    if isinstance(e,Var):
        if type(e.name) is not str or not e.name:raise ValueError('variable name must be a nonempty string')
        return {(e.name,):1}
    if isinstance(e,Add):
        out=normalize(e.left)
        for m,c in normalize(e.right).items():out[m]=out.get(m,0)+c
        return {m:c for m,c in out.items() if c}
    if not isinstance(e,Mul):raise TypeError('unknown semiring expression')
    a=normalize(e.left);b=normalize(e.right);out={}
    for ma,ca in a.items():
        for mb,cb in b.items():
            m=tuple(sorted(ma+mb));out[m]=out.get(m,0)+ca*cb
    return {m:c for m,c in out.items() if c}


def _matrix(value):
    if not isinstance(value,(list,tuple)) or not value or not isinstance(value[0],(list,tuple)) or not value[0]:
        raise ValueError('nonempty rectangular matrix required')
    width=len(value[0]);out=[]
    for i,row in enumerate(value):
        if not isinstance(row,(list,tuple)) or len(row)!=width:raise ValueError('rectangular matrix required')
        out.append(tuple(_nat(x,f'matrix[{i}][{j}]') for j,x in enumerate(row)))
    return tuple(out)


def _vector(value,length,label):
    if not isinstance(value,(list,tuple)) or len(value)!=length:raise ValueError(f'{label} dimension mismatch')
    return tuple(_nat(x,f'{label}[{i}]') for i,x in enumerate(value))


def add_many(xs):
    out=Const(0)
    for x in xs:out=Add(out,x)
    return out


def mul_const(c,e):return Mul(Const(_nat(c,'coefficient')),e)


def target_expression(matrix):
    a=_matrix(matrix)
    return add_many(mul_const(a[i][j],Mul(Var(f'x{i}'),Var(f'y{j}')))
        for i in range(len(a)) for j in range(len(a[0])))


def compiled_expression(witness,rows,cols):
    if not isinstance(witness,list):raise ValueError('witness must be a list')
    terms=[]
    for ell,f in enumerate(witness):
        if not isinstance(f,dict):raise ValueError('factor must be an object')
        u=_vector(f.get('u'),rows,f'factor {ell} u');v=_vector(f.get('v'),cols,f'factor {ell} v')
        if 'atom' in f:
            atom=_matrix(f['atom'])
            expected=tuple(tuple(u[i]*v[j] for j in range(cols)) for i in range(rows))
            if atom!=expected:raise ValueError('factor atom mismatch')
        left=add_many(mul_const(c,Var(f'x{i}')) for i,c in enumerate(u))
        right=add_many(mul_const(c,Var(f'y{j}')) for j,c in enumerate(v))
        terms.append(Mul(left,right))
    return add_many(terms)


def verify_factor_packet(packet)->dict:
    if not isinstance(packet,dict):raise ValueError('packet must be an object')
    matrix=_matrix(packet.get('matrix'));rows,cols=len(matrix),len(matrix[0])
    if 'rows' in packet and _nat(packet['rows'],'rows')!=rows:raise ValueError('row mismatch')
    if 'cols' in packet and _nat(packet['cols'],'cols')!=cols:raise ValueError('column mismatch')
    target=normalize(target_expression(matrix))
    compiled=normalize(compiled_expression(packet.get('witness'),rows,cols))
    if target!=compiled:raise ValueError('factor schedule polynomial mismatch')
    return {'variables':rows+cols,'target_monomials':len(target),
            'compiled_monomials':len(compiled),'checked':True}

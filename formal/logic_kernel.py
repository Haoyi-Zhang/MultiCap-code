"""A deliberately small first-order equational proof kernel.

The kernel computes theorem conclusions from proof terms.  It supports sorted
variables, uninterpreted function applications, equality, implication, and
universal quantification.  It is sufficient to check the semantic core of the
residual-state lower bound: correctness plus equal barrier states implies equal
residual functions.  The implementation is independent of the compiler and
certificate checkers.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Union

@dataclass(frozen=True)
class Var:
    name:str
    sort:str

@dataclass(frozen=True)
class App:
    name:str
    args:Tuple['Term',...]
    sort:str

Term=Union[Var,App]

@dataclass(frozen=True)
class Eq:
    left:Term
    right:Term

@dataclass(frozen=True)
class Imp:
    premise:'Formula'
    conclusion:'Formula'

@dataclass(frozen=True)
class Forall:
    var:Var
    body:'Formula'

Formula=Union[Eq,Imp,Forall]

@dataclass(frozen=True)
class Assumption:
    formula:Formula

@dataclass(frozen=True)
class Refl:
    term:Term

@dataclass(frozen=True)
class Symm:
    proof:'Proof'

@dataclass(frozen=True)
class Trans:
    first:'Proof'
    second:'Proof'

@dataclass(frozen=True)
class Congr:
    name:str
    result_sort:str
    proofs:Tuple['Proof',...]

@dataclass(frozen=True)
class ImpIntro:
    assumption:Formula
    body:'Proof'

@dataclass(frozen=True)
class ImpElim:
    implication:'Proof'
    premise:'Proof'

@dataclass(frozen=True)
class ForallIntro:
    var:Var
    body:'Proof'

@dataclass(frozen=True)
class ForallElim:
    quantified:'Proof'
    term:Term

Proof=Union[Assumption,Refl,Symm,Trans,Congr,ImpIntro,ImpElim,ForallIntro,ForallElim]


def term_sort(t:Term)->str:
    return t.sort


def free_term(t:Term)->set[Var]:
    if isinstance(t,Var):return {t}
    out=set()
    for a in t.args:out |= free_term(a)
    return out


def free_formula(f:Formula)->set[Var]:
    if isinstance(f,Eq):return free_term(f.left)|free_term(f.right)
    if isinstance(f,Imp):return free_formula(f.premise)|free_formula(f.conclusion)
    out=free_formula(f.body);out.discard(f.var);return out


def subst_term(t:Term,var:Var,value:Term)->Term:
    if term_sort(value)!=var.sort:raise TypeError('substitution sort mismatch')
    if isinstance(t,Var):return value if t==var else t
    return App(t.name,tuple(subst_term(a,var,value) for a in t.args),t.sort)


def subst_formula(f:Formula,var:Var,value:Term)->Formula:
    if isinstance(f,Eq):return Eq(subst_term(f.left,var,value),subst_term(f.right,var,value))
    if isinstance(f,Imp):return Imp(subst_formula(f.premise,var,value),subst_formula(f.conclusion,var,value))
    if f.var==var:return f
    if f.var in free_term(value):raise ValueError('capture-avoiding substitution requires a fresh binder')
    return Forall(f.var,subst_formula(f.body,var,value))


def validate_term(t:Term,signatures:dict)->str:
    if not isinstance(t,(Var,App)) or type(t.name) is not str or not t.name:
        raise TypeError('malformed sorted term')
    if type(t.sort) is not str or not t.sort:
        raise TypeError('term needs a nonempty sort')
    if isinstance(t,App):
        if not isinstance(t.args,tuple):raise TypeError('application arguments must be a tuple')
        argument_sorts=tuple(validate_term(a,signatures) for a in t.args)
        signature=(argument_sorts,t.sort)
        if t.name in signatures and signatures[t.name]!=signature:
            raise TypeError('inconsistent function signature: '+t.name)
        signatures[t.name]=signature
    return t.sort


def validate_formula(f:Formula,signatures:dict)->None:
    if isinstance(f,Eq):
        if validate_term(f.left,signatures)!=validate_term(f.right,signatures):
            raise TypeError('equality sort mismatch')
    elif isinstance(f,Imp):
        validate_formula(f.premise,signatures);validate_formula(f.conclusion,signatures)
    elif isinstance(f,Forall):
        if not isinstance(f.var,Var):raise TypeError('quantifier binder must be a variable')
        validate_term(f.var,signatures);validate_formula(f.body,signatures)
    else:raise TypeError('unknown formula node')


def check(proof:Proof,context:Tuple[Formula,...]=())->Formula:
    # A symbol has one input/result signature throughout this derivation.
    signatures={}
    def checked(p,ctx):
        for f in ctx:validate_formula(f,signatures)
        # An unused/shadowed instantiation term may disappear from the
        # conclusion, but it must still be a well-sorted term of this language.
        if isinstance(p,(Refl,ForallElim)):validate_term(p.term,signatures)
        if isinstance(p,ForallIntro):
            if not isinstance(p.var,Var):raise TypeError('quantifier binder must be a variable')
            validate_term(p.var,signatures)
        result=_infer(p,ctx,checked)
        validate_formula(result,signatures)
        return result
    return checked(proof,context)


def _infer(proof:Proof,context:Tuple[Formula,...],recur)->Formula:
    if isinstance(proof,Assumption):
        if proof.formula not in context:raise ValueError('undeclared assumption')
        return proof.formula
    if isinstance(proof,Refl):return Eq(proof.term,proof.term)
    if isinstance(proof,Symm):
        f=recur(proof.proof,context)
        if not isinstance(f,Eq):raise TypeError('symmetry requires equality')
        return Eq(f.right,f.left)
    if isinstance(proof,Trans):
        a=recur(proof.first,context);b=recur(proof.second,context)
        if not isinstance(a,Eq) or not isinstance(b,Eq) or a.right!=b.left:
            raise ValueError('invalid equality transitivity')
        return Eq(a.left,b.right)
    if isinstance(proof,Congr):
        equalities=[recur(p,context) for p in proof.proofs]
        if any(not isinstance(e,Eq) for e in equalities):raise TypeError('congruence arguments')
        left=App(proof.name,tuple(e.left for e in equalities),proof.result_sort)
        right=App(proof.name,tuple(e.right for e in equalities),proof.result_sort)
        return Eq(left,right)
    if isinstance(proof,ImpIntro):
        body=recur(proof.body,context+(proof.assumption,))
        return Imp(proof.assumption,body)
    if isinstance(proof,ImpElim):
        arrow=recur(proof.implication,context);premise=recur(proof.premise,context)
        if not isinstance(arrow,Imp) or arrow.premise!=premise:raise ValueError('invalid implication elimination')
        return arrow.conclusion
    if isinstance(proof,ForallIntro):
        if any(proof.var in free_formula(f) for f in context):
            raise ValueError('universal variable occurs free in context')
        return Forall(proof.var,recur(proof.body,context))
    if isinstance(proof,ForallElim):
        q=recur(proof.quantified,context)
        if not isinstance(q,Forall):raise TypeError('universal elimination requires forall')
        if not isinstance(proof.term,(Var,App)) or term_sort(proof.term)!=q.var.sort:
            raise TypeError('substitution sort mismatch')
        return subst_formula(q.body,q.var,proof.term)
    raise TypeError('unknown proof node')

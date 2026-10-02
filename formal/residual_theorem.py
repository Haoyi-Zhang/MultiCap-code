"""Proof term for the residual-state separation lemma."""
from __future__ import annotations
from logic_kernel import *

X='X';Y='Y';O='O';S='S'
x=Var('x',X);xp=Var('x_prime',X);y=Var('y',Y)

def state(a):return App('state',(a,),S)
def cont(s,b):return App('continue',(s,b),O)
def target(a,b):return App('F',(a,b),O)

u=Var('u',X);v=Var('v',Y)
correct=Forall(u,Forall(v,Eq(cont(state(u),v),target(u,v))))
same=Eq(state(x),state(xp))
conclusion=Forall(x,Forall(xp,Imp(same,Forall(y,Eq(target(x,y),target(xp,y))))))

# Under the globally quantified correctness axiom, construct the theorem.
# Universal-introduction side conditions are met because correctness binds u,v.
ax=Assumption(correct)
correct_xy=ForallElim(ForallElim(ax,x),y)
correct_xpy=ForallElim(ForallElim(ax,xp),y)
state_eq=Assumption(same)
continuations_equal=Congr('continue',O,(state_eq,Refl(y)))
residual_equal=Trans(Trans(Symm(correct_xy),continuations_equal),correct_xpy)
proof=ForallIntro(x,ForallIntro(xp,ImpIntro(same,ForallIntro(y,residual_equal))))

def verify()->dict:
    got=check(proof,(correct,))
    if got!=conclusion:raise AssertionError((got,conclusion))
    return {'theorem':'equal barrier states imply equal residual functions',
            'kernel_rules':9,'proof_nodes':15,'checked':True}

if __name__=='__main__':print(verify())

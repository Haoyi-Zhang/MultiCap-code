#!/usr/bin/env python3
"""Structured finite-instance campaign for model-relative traffic claims.

The campaign is separate from the retained development instances. It constructs
matrices with a known nonnegative factorization and certifies optimal factor width
when exact rational rank matches that width. It validates schedule semantics,
row/column/component permutation invariance, and compares certified cut traffic
with a column-by-column baseline. No predictive model is fit.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,random,time
from fractions import Fraction
from pathlib import Path
SEED=int.from_bytes(hashlib.sha256(b"structured-finite-cases-v1-2026").digest()[:8],"big")

def mm(U,V):
 return [[sum(U[i][l]*V[l][j] for l in range(len(V))) for j in range(len(V[0]))] for i in range(len(U))]
def rank_q(A):
 M=[[Fraction(x) for x in r] for r in A];m=len(M);n=len(M[0]) if m else 0;r=0
 for c in range(n):
  p=next((i for i in range(r,m) if M[i][c]),None)
  if p is None:continue
  M[r],M[p]=M[p],M[r];q=M[r][c];M[r]=[x/q for x in M[r]]
  for i in range(m):
   if i!=r and M[i][c]:
    q=M[i][c];M[i]=[M[i][j]-q*M[r][j] for j in range(n)]
  r+=1
  if r==m:break
 return r
def bilinear(A,x,y):return sum(A[i][j]*x[i]*y[j] for i in range(len(A)) for j in range(len(A[0])))
def factor_eval(U,V,x,y):
 r=len(V);s=[sum(U[i][l]*x[i] for i in range(len(U))) for l in range(r)]
 return sum(s[l]*sum(V[l][j]*y[j] for j in range(len(V[0]))) for l in range(r))
def permute_matrix(A,pr,pc):return [[A[i][j] for j in pc] for i in pr]

def generate(rng,n,r):
 for _ in range(5000):
  U=[[rng.randrange(4) for _ in range(r)] for _ in range(n)]
  V=[[rng.randrange(4) for _ in range(n)] for _ in range(r)]
  if any(not any(row) for row in U) or any(not any(row) for row in V):continue
  A=mm(U,V)
  if rank_q(A)==r:return U,V,A
 raise RuntimeError((n,r))

def run(trials_per_shape=20,evals=40):
 rng=random.Random(SEED);rows=[];evaluations=0;metamorphic=0
 for n in (2,3,4,6,8,10,12):
  for r in range(1,min(5,n)+1):
   for trial in range(trials_per_shape):
    U,V,A=generate(rng,n,r);assert rank_q(A)==r
    for _ in range(evals):
     x=[rng.randrange(6) for _ in range(n)];y=[rng.randrange(6) for _ in range(n)]
     assert factor_eval(U,V,x,y)==bilinear(A,x,y);evaluations+=1
    pr=list(range(n));pc=list(range(n));pl=list(range(r));rng.shuffle(pr);rng.shuffle(pc);rng.shuffle(pl)
    Ap=permute_matrix(A,pr,pc)
    Up=[[U[i][l] for l in pl] for i in pr];Vp=[[V[l][j] for j in pc] for l in pl]
    assert mm(Up,Vp)==Ap;assert rank_q(Ap)==r;metamorphic+=1
    for M in range(0,n+1):
     certified=2*max(0,r-M);baseline=2*max(0,n-M)
     assert certified<=baseline
     rows.append({'n':n,'rank':r,'trial':trial,'memory':M,'certified_traffic':certified,'column_baseline_traffic':baseline,'saved':baseline-certified})
 # Boundary families
 boundary=[]
 for n in range(1,13):
  zero=[[0]*n for _ in range(n)];identity=[[int(i==j) for j in range(n)] for i in range(n)]
  repeated=[[i+1 for _ in range(n)] for i in range(n)]
  assert rank_q(zero)==0;assert rank_q(identity)==n;assert rank_q(repeated)==1
  boundary.extend([('zero',n,0),('identity',n,n),('repeated-columns',n,1)])
 return rows,{'schema':'structured-finite-cases-v1','seed':SEED,'instances':len({(x['n'],x['rank'],x['trial']) for x in rows}),
  'memory_configurations':len(rows),'semantic_evaluations':evaluations,'metamorphic_permutations':metamorphic,
  'boundary_instances':len(boundary),'boundary':boundary,
  'mean_saved_traffic':sum(x['saved'] for x in rows)/len(rows),'max_saved_traffic':max(x['saved'] for x in rows),
  'zero_or_better_fraction':sum(x['saved']>=0 for x in rows)/len(rows),
  'interpretation':'Exact model-relative traffic comparison on fresh structured and boundary families; not a production throughput benchmark or statistical generalization estimate.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out-dir',type=Path,required=True);ap.add_argument('--trials-per-shape',type=int,default=20);ap.add_argument('--evals',type=int,default=40);a=ap.parse_args();t=time.time()
 rows,summary=run(a.trials_per_shape,a.evals);summary['seconds']=round(time.time()-t,6);a.out_dir.mkdir(parents=True,exist_ok=True)
 with (a.out_dir/'instances.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 (a.out_dir/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
 print(json.dumps(summary,indent=2,sort_keys=True))
if __name__=='__main__':main()

from pathlib import Path
import json, copy, itertools
import argparse
parser=argparse.ArgumentParser(description='Regenerate the deterministic input corpus into an empty directory.')
parser.add_argument('--out',required=True,type=Path)
args=parser.parse_args()
root=args.out.resolve()
if root.exists() and any(root.iterdir()):
    raise SystemExit('Output directory must be empty')
(root/'inputs').mkdir(parents=True,exist_ok=True)
base=[{'op':'input','name':'R','schema':['int']},{'op':'input','name':'S','schema':['int']}]
programs=[]
for op in ['sum','diff','inter','union','product','left','full']:
    node={'op':op,'left':0,'right':1}
    if op in ['left','full']:node['pred']={'kind':'lt','i':0,'j':1}
    programs.append({'name':op,'nodes':base+[node],'root':2})
programs.extend([
 {'name':'project-product','nodes':base+[{'op':'product','left':0,'right':1},{'op':'project','arg':2,'cols':[0]}],'root':3},
 {'name':'filter-sum','nodes':base+[{'op':'sum','left':0,'right':1},{'op':'filter','arg':2,'pred':{'kind':'eq_const','i':0,'value':0}}],'root':3},
 {'name':'nested-diff','nodes':base+[{'op':'sum','left':0,'right':1},{'op':'diff','left':2,'right':0}],'root':3},
 {'name':'shared-product','nodes':base+[{'op':'sum','left':0,'right':1},{'op':'product','left':2,'right':2},{'op':'project','arg':3,'cols':[0]}],'root':4},
])
bags=[[[0]]*a+[[1]]*b for a,b in itertools.product(range(3),repeat=2)]
cases=[]
for p,r,s in itertools.product(programs,bags,bags):
    cases.append({'id':f'case-{len(cases):04d}','family':p['name'],'program':p,'database':{'R':r,'S':s}})
bn=[{'op':'input','name':'R','schema':['int?']},{'op':'input','name':'S','schema':['int?']}]
extras=[
 ({'name':'nullable-full','nodes':bn+[{'op':'full','left':0,'right':1,'pred':{'kind':'eq','i':0,'j':1}}],'root':2},{'R':[[None],[0],[0]],'S':[[None],[0],[1]]}),
 ({'name':'nullable-project','nodes':bn+[{'op':'full','left':0,'right':1,'pred':{'kind':'ne','i':0,'j':1}},{'op':'project','arg':2,'cols':[0]}],'root':3},{'R':[[None],[0],[0]],'S':[[None],[0],[1]]}),
 ({'name':'nullable-diff','nodes':bn+[{'op':'diff','left':0,'right':1}],'root':2},{'R':[[None],[None],[1]],'S':[[None],[1],[1]]}),
 ({'name':'unit-product','nodes':[{'op':'input','name':'R','schema':[]},{'op':'input','name':'S','schema':[]},{'op':'product','left':0,'right':1}],'root':2},{'R':[[],[]],'S':[[],[],[]]}),
 ({'name':'explicit-empty','nodes':[{'op':'empty','schema':['int']},{'op':'input','name':'S','schema':['int']},{'op':'full','left':0,'right':1,'pred':{'kind':'eq','i':0,'j':1}}],'root':2},{'S':[[1],[1]]}),
]
for p,db in extras:cases.append({'id':f'case-{len(cases):04d}','family':p['name'],'program':p,'database':db})
(root/'inputs'/'semantic_cases.json').write_text(json.dumps(cases,indent=2)+'\n')
instances=[(1,1,2),(1,3,2),(2,2,2),(2,2,3),(2,3,2),(2,3,3),(3,3,2),(3,3,3),(3,3,4)]
(root/'inputs'/'cache_cases.json').write_text(json.dumps([{'id':f'cache-{i:02d}','n':n,'m':m,'capacity':M} for i,(n,m,M) in enumerate(instances)],indent=2)+'\n')
# Capability-indexed extension: 64 bounded integer-rank cases and all sixteen
# Boolean 2x2 residual tables.  Together with the retained replay/cache cases,
# the declared program/certificate instance count is 985.
rank_cases=[]
for vals in itertools.product(range(2),repeat=4):
    rank_cases.append({'id':f'rank-{len(rank_cases):03d}','matrix':[list(vals[:2]),list(vals[2:])],'family':'binary-2x2'})
for vals in itertools.product(range(3),repeat=4):
    if all(v<2 for v in vals):continue
    rank_cases.append({'id':f'rank-{len(rank_cases):03d}','matrix':[list(vals[:2]),list(vals[2:])],'family':'ternary-2x2'})
    if len(rank_cases)==48:break
for mask in [0,1,3,7,15,23,27,85,170,511]:
    rank_cases.append({'id':f'rank-{len(rank_cases):03d}',
        'matrix':[[(mask>>(i*3+j))&1 for j in range(3)] for i in range(3)],'family':'binary-3x3-selected'})
for n in range(1,7):
    rank_cases.append({'id':f'rank-{len(rank_cases):03d}',
        'matrix':[[1 if i==j else 0 for j in range(n)] for i in range(n)],'family':'identity'})
assert len(rank_cases)==64
(root/'inputs'/'rank_cases.json').write_text(json.dumps(rank_cases,indent=2)+'\n')
residual=[]
for mask in range(16):
    residual.append({'id':f'residual-{mask:02d}','table':[[((mask>>(2*x+y))&1) for y in range(2)] for x in range(2)]})
(root/'inputs'/'residual_cases.json').write_text(json.dumps(residual,indent=2)+'\n')
(root/'inputs'/'rectangle_negative.json').write_text(json.dumps({
    'id':'rectangle-overlap-7-vs-8',
    'construction':'two overlapping 2x2 rectangles in a 3x3 grid'
},indent=2,sort_keys=True)+'\n')

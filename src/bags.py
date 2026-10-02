"""Typed acyclic bag syntax and a deliberately materializing denotation oracle.

The Counter oracle belongs to the test harness, not the replay executor or its
bounded-memory claim. Input occurrences are represented as lists in this simulator.
"""
from __future__ import annotations
from collections import Counter


def check_program(program: dict) -> list[tuple[str,...]]:
    nodes=program['nodes']
    if not (1<=len(nodes)<=64):raise ValueError('Operator limit')
    schemas=[]
    for i,node in enumerate(nodes):
        op=node.get('op')
        def child(k):
            j=node.get(k)
            if type(j) is not int or not(0<=j<i):raise ValueError('Non-acyclic child')
            return schemas[j]
        if op in ('input','empty'):
            schema=tuple(node['schema'])
            if len(schema)>16 or any(t not in ('int','int?') for t in schema):raise ValueError('Invalid schema')
            if op=='input' and (not isinstance(node['name'],str) or not node['name']):raise ValueError('Invalid source')
        elif op in ('sum','diff','inter','union','product','left','full'):
            a,b=child('left'),child('right')
            if op in ('sum','diff','inter','union'):
                if a!=b:raise ValueError('Schema mismatch')
                schema=a
            else:
                if op=='product':schema=a+b
                elif op=='left':schema=a+tuple('int?' for _ in b)
                else:schema=tuple('int?' for _ in a+b)
                if op in ('left','full'):check_pred(node['pred'],a+b)
        elif op in ('project','filter'):
            a=child('arg')
            if op=='project':
                cols=node['cols']
                if any(type(c) is not int or not(0<=c<len(a)) for c in cols):raise ValueError('Bad projection')
                schema=tuple(a[c] for c in cols)
            else:check_pred(node['pred'],a);schema=a
        else:raise ValueError('Unknown operator')
        if len(schema)>16:raise ValueError('Tuple arity cap')
        schemas.append(schema)
    if type(program['root']) is not int or not(0<=program['root']<len(nodes)):raise ValueError('Bad root')
    declared={}
    for node,schema in zip(nodes,schemas):
        if node['op']=='input':
            name=node['name']
            if name in declared and declared[name]!=schema:raise ValueError('Source schema disagreement')
            declared[name]=schema
    if len(declared)>16:raise ValueError('Relation cap')
    return schemas


def check_pred(p: dict, schema: tuple[str,...]) -> None:
    if p['kind'] not in ('eq','lt','ne','eq_const'):raise ValueError('Bad predicate')
    for k in ('i',) if p['kind']=='eq_const' else ('i','j'):
        if type(p[k]) is not int or not(0<=p[k]<len(schema)):raise ValueError('Predicate column')
    if p['kind']=='eq_const' and type(p['value']) is not int:raise ValueError('Predicate constant')


def predicate(p: dict, row: tuple) -> bool:
    a=row[p['i']];b=p['value'] if p['kind']=='eq_const' else row[p['j']]
    # Explicit two-valued nullable predicates; this is not full SQL semantics.
    if a is None or b is None:return False
    if p['kind'] in ('eq','eq_const'):return a==b
    if p['kind']=='lt':return a<b
    return a!=b


def check_inputs(program: dict, schemas: list[tuple], database: dict) -> None:
    for node,schema in zip(program['nodes'],schemas):
        if node['op']!='input':continue
        for row in database[node['name']]:
            if len(row)!=len(schema):raise ValueError('Input arity')
            for x,t in zip(row,schema):
                if not(type(x) is int or x is None and t=='int?'):raise ValueError('Input type')


def denote(program: dict, database: dict) -> Counter:
    schemas=check_program(program);check_inputs(program,schemas,database)
    values=[]
    for node in program['nodes']:
        op=node['op'];out=Counter()
        if op=='input':out=Counter(tuple(r) for r in database[node['name']])
        elif op=='empty':pass
        elif op in ('project','filter'):
            a=values[node['arg']]
            for x,c in a.items():
                if op=='project':out[tuple(x[i] for i in node['cols'])]+=c
                elif predicate(node['pred'],x):out[x]+=c
        else:
            a,b=values[node['left']],values[node['right']]
            if op=='sum':out=a+b
            elif op=='diff':out=a-b
            elif op=='inter':out=a&b
            elif op=='union':out=a|b
            else:
                for x,c in a.items():
                    matched=False
                    for y,d in b.items():
                        if op=='product' or predicate(node['pred'],x+y):
                            out[x+y]+=c*d;matched=True
                    if not matched and op in ('left','full'):
                        out[x+(None,)*len(schemas[node['right']])]+=c
                if op=='full':
                    for y,d in b.items():
                        if not any(predicate(node['pred'],x+y) for x in a):
                            out[(None,)*len(schemas[node['left']])+y]+=d
        values.append(+out)
    return values[program['root']]


def frame_bound(program: dict) -> int:
    check_program(program);bounds=[]
    for node in program['nodes']:
        op=node['op']
        if op in ('input','empty'):v=1
        elif op in ('project','filter'):v=1+bounds[node['arg']]
        else:
            a,b=bounds[node['left']],bounds[node['right']]
            if op=='sum':v=1+max(a,b)
            elif op in ('product','left','full'):v=1+a+b
            elif op in ('diff','inter'):v=1+max(2*a,a+b)
            elif op=='union':v=1+max(a,2*b,a+b)
            else:raise ValueError('unrecognized validated operator')
        bounds.append(v)
    return bounds[program['root']]


def cardinality_bounds(program: dict, database: dict) -> list[int]:
    """Safe cardinality bounds, not claimed tight for outer joins or filtering."""
    check_program(program)
    bounds=[]
    for node in program['nodes']:
        op=node['op']
        if op=='input':v=len(database[node['name']])
        elif op=='empty':v=0
        elif op in ('project','filter'):v=bounds[node['arg']]
        else:
            a,b=bounds[node['left']],bounds[node['right']]
            if op in ('sum','union'):v=a+b
            elif op=='product':v=a*b
            elif op=='left':v=a*(b+1)
            elif op=='full':v=a*b+a+b
            elif op=='diff':v=a
            elif op=='inter':v=min(a,b)
        bounds.append(v)
    return bounds

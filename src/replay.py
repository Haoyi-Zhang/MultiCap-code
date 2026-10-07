"""Restartable occurrence enumerator. No derived relation is collected here.

Input arrays simulate immutable slow memory. Every yielded base occurrence counts
as one modeled read; Python memory or elapsed time is not external-I/O performance.
All prefix enumerations are explicitly closed, including early termination.
"""
from __future__ import annotations
from contextlib import closing
from dataclasses import dataclass
from bags import check_program

@dataclass
class Metrics:
    base_reads:int=0
    node_yields:int=0
    active_frames:int=0
    peak_frames:int=0
    max_counter:int=0

class Replay:
    def __init__(self, program:dict, database:dict, read_limit:int=1_000_000):
        self.schemas=check_program(program)
        self.program=program;self.database=database;self.stats=Metrics();self.read_limit=read_limit

    def test(self,p,row):
        # Kept separate from the Counter oracle predicate evaluator.
        a=row[p['i']]
        b=p['value'] if p['kind']=='eq_const' else row[p['j']]
        if a is None or b is None:return False
        kind=p['kind']
        if kind in ('eq','eq_const'):return a==b
        if kind=='lt':return a<b
        if kind=='ne':return a!=b
        # Preserve unsupported hashable/unhashable dispatch failures as well.
        return {}[kind]

    def count(self,node,value,prefix=None):
        total=0
        with closing(self.rows(node)) as it:
            for position,x in enumerate(it,1):
                if x==value:total+=1
                self.stats.max_counter=max(self.stats.max_counter,total,position)
                if prefix is not None and position>=prefix:break
        return total

    def exists(self,node,p,left=None,right=None):
        with closing(self.rows(node)) as it:
            for x in it:
                row=left+x if left is not None else x+right
                if self.test(p,row):return True
        return False

    def rows(self,index=None):
        if index is None:index=self.program['root']
        s=self.stats;s.active_frames+=1;s.peak_frames=max(s.peak_frames,s.active_frames)
        try:
            for x in self.body(index):
                s.node_yields+=1
                yield x
        finally:s.active_frames-=1

    def body(self,index):
        node=self.program['nodes'][index];op=node['op']
        if op=='input':
            for x in self.database[node['name']]:
                self.stats.base_reads+=1
                if self.stats.base_reads>self.read_limit:raise RuntimeError('Modeled read cap exceeded')
                schema=self.schemas[index]
                if len(x)!=len(schema) or any(not(type(v) is int or v is None and t=='int?') for v,t in zip(x,schema)):
                    raise ValueError('Input tuple violates source schema')
                yield tuple(x)
            return
        if op=='empty':return
        if op in ('filter','project'):
            with closing(self.rows(node['arg'])) as it:
                for x in it:
                    if op=='project':yield tuple(x[i] for i in node['cols'])
                    elif self.test(node['pred'],x):yield x
            return
        a,b=node['left'],node['right']
        if op=='sum':
            for side in (a,b):
                with closing(self.rows(side)) as it:yield from it
        elif op in ('product','left','full'):
            with closing(self.rows(a)) as outer:
                for x in outer:
                    matched=False
                    with closing(self.rows(b)) as inner:
                        for y in inner:
                            if op=='product' or self.test(node['pred'],x+y):
                                matched=True;yield x+y
                    if not matched and op in ('left','full'):
                        yield x+(None,)*len(self.schemas[b])
            if op=='full':
                with closing(self.rows(b)) as outer:
                    for y in outer:
                        if not self.exists(a,node['pred'],right=y):
                            yield (None,)*len(self.schemas[a])+y
        elif op in ('diff','inter'):
            with closing(self.rows(a)) as it:
                for position,x in enumerate(it,1):
                    rank=self.count(a,x,prefix=position)
                    count=self.count(b,x)
                    self.stats.max_counter=max(self.stats.max_counter,position)
                    if (rank>count if op=='diff' else rank<=count):yield x
        elif op=='union':
            with closing(self.rows(a)) as it:yield from it
            with closing(self.rows(b)) as it:
                for position,y in enumerate(it,1):
                    rank=self.count(b,y,prefix=position)
                    count=self.count(a,y)
                    self.stats.max_counter=max(self.stats.max_counter,position)
                    if rank>count:yield y
        else:raise ValueError('Unrecognized validated operator')

"""Exact offline occurrence-pair read search. Not a production query optimizer.

Symmetry reduction only renames occurrences within each of the two sources.
The returned trace is in physical labels; the lower-bound potential is on orbits.
"""
from __future__ import annotations
from collections import deque
from itertools import permutations
from functools import lru_cache


def solve(n: int, m: int, capacity: int, max_edges: int = 20000) -> dict:
    if not (1 <= n <= 3 and 1 <= m <= 3 and 2 <= capacity <= n+m):
        raise ValueError('Supported diagnostic dimensions: 1..3, capacity 2..n+m')
    N = n+m
    target = (1 << (n*m))-1
    perms=[]
    for a in permutations(range(n)):
        for b in permutations(range(m)):
            vertex=a+tuple(n+j for j in b)
            edge=tuple(a[i]*m+b[j] for i in range(n) for j in range(m))
            perms.append((vertex,edge))
    @lru_cache(None)
    def canonical(cache: int, done: int) -> tuple[int,int]:
        return min((sum(1<<p[i] for i in range(N) if cache>>i&1),
                    sum(1<<e[k] for k in range(n*m) if done>>k&1)) for p,e in perms)
    cross = {c: sum(1<<(i*m+j) for i in range(n) for j in range(m)
                    if c>>i&1 and c>>(n+j)&1) for c in range(1<<N)}
    start=(0,0)
    q=deque([start]); distance={start:0}; representatives={start:start}; parent={}
    examined=0; goal=None
    while q:
        key=q.popleft()
        cache,done=representatives[key]
        if done==target:
            goal=key;break
        for load in range(N):
            if cache>>load&1:continue
            evictions=[None] if cache.bit_count()<capacity else [v for v in range(N) if cache>>v&1]
            for evict in evictions:
                examined+=1
                if examined>max_edges:raise RuntimeError('Search transition cap exceeded')
                c=(cache if evict is None else cache&~(1<<evict))|(1<<load)
                d=done|cross[c]
                new=canonical(c,d)
                if new not in distance:
                    distance[new]=distance[key]+1
                    representatives[new]=(c,d)
                    parent[new]=(key,load,evict)
                    q.append(new)
    if goal is None:raise RuntimeError('No accepting state')
    optimum=distance[goal]; trace=[]; p=goal
    while p!=start:
        old,load,evict=parent[p]
        trace.append({'load':load,'evict':evict})
        p=old
    trace.reverse()
    potential=[{'cache':c,'done':d,'h':optimum-dist} for (c,d),dist in sorted(distance.items()) if dist<optimum]
    return {'n':n,'m':m,'capacity':capacity,'optimum':optimum,'trace':trace,
            'potential':potential,'search_states':len(distance),'search_transitions':examined}

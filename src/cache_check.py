"""Read-only checker: independently enumerated set transitions and orbit keys.

Does not import the search engine. Its general soundness argument is handwritten
in proofs/cache.md; running this file does not mechanize that argument.
"""
from __future__ import annotations
from itertools import permutations
from functools import lru_cache


def check(packet: dict) -> dict:
    n,m,M=(packet[k] for k in ('n','m','capacity'))
    if any(type(v) is not int for v in (n,m,M)) or not(1<=n<=3 and 1<=m<=3 and 2<=M<=n+m):
        raise ValueError('Bad instance dimensions')
    universe=frozenset(range(n+m)); pairs=frozenset((i,n+j) for i in range(n) for j in range(m))
    def decode(c,d):
        if type(c) is not int or type(d) is not int or not(0<=c<2**(n+m) and 0<=d<2**(n*m)):
            raise ValueError('Out-of-range state')
        resident=frozenset(v for v in universe if c&(2**v))
        emitted=frozenset((i,n+j) for i in range(n) for j in range(m) if d&(2**(i*m+j)))
        if len(resident)>M:raise ValueError('Capacity violated in potential')
        if not all((a,b) in emitted for a in resident if a<n for b in resident if b>=n):
            raise ValueError('State is not emission-saturated')
        return resident,emitted
    @lru_cache(None)
    def key(resident,emitted):
        candidates=[]
        for a in permutations(range(n)):
            for b in permutations(range(n,n+m)):
                ren=dict(enumerate(a+b))
                newresident={ren[v] for v in resident}
                newpairs={(ren[u],ren[v]) for u,v in emitted}
                c=sum(2**v for v in newresident)
                d=sum(2**(u*m+(v-n)) for u,v in newpairs)
                candidates.append((c,d))
        return min(candidates)
    h={}; decoded={}
    for entry in packet['potential']:
        c,d,v=(entry[k] for k in ('cache','done','h'))
        state=decode(c,d)
        if type(v) is not int or not (1<=v<=100):raise ValueError('Bad potential')
        if (c,d)!=key(*state):raise ValueError('Noncanonical potential key')
        if (c,d) in h:raise ValueError('Duplicate potential key')
        if state[1]==pairs:raise ValueError('Positive potential at goal')
        h[c,d]=v;decoded[c,d]=state
    claimed=packet['optimum']
    if type(claimed) is not int or h.get((0,0),0)!=claimed:raise ValueError('Wrong initial lower bound')
    inequalities=0
    for k,v in h.items():
        if v==1:continue # all successor potentials are nonnegative
        resident,emitted=decoded[k]
        for load in sorted(universe-resident):
            evictions=[None] if len(resident)<M else sorted(resident)
            for evict in evictions:
                after=(resident if evict is None else resident-{evict})|{load}
                out=emitted|{(a,b) for a in after if a<n for b in after if b>=n}
                if v>1+h.get(key(frozenset(after),frozenset(out)),0):
                    raise ValueError('Bellman inequality violated')
                inequalities+=1
    resident=set(); emitted=set(); emitted_order=[]
    for step in packet['trace']:
        if set(step)!={'load','evict'}:raise ValueError('Bad trace action')
        load,evict=step['load'],step['evict']
        if type(load) is not int or load not in universe or load in resident:raise ValueError('Illegal read')
        if evict is not None:
            if type(evict) is not int or evict not in resident:raise ValueError('Illegal eviction')
            resident.remove(evict)
        if len(resident)>=M:raise ValueError('Trace exceeds capacity')
        resident.add(load)
        for a in sorted(resident):
            for b in sorted(resident):
                if a<n<=b and (a,b) not in emitted:
                    emitted.add((a,b));emitted_order.append([a,b-n])
    if emitted!=set(pairs):raise ValueError('Missing output pair')
    if len(packet['trace'])!=claimed:raise ValueError('Upper and lower bounds differ')
    return {'upper_reads':len(packet['trace']),'lower_reads':claimed,
            'potential_entries':len(h),'checked_inequalities':inequalities,
            'emitted_pairs':emitted_order}

"""Bounded exact all-pairs cache oracle for the 3x3, M=3 diagnostic.

The retained result is a current recomputation.  An earlier raw pilot record was
not retained, so this module never labels its output as the original run.
"""
from __future__ import annotations
from collections import deque
import json
import os
import resource
import signal
import time


def solve_pilot(include_measurements: bool = True) -> dict:
    n=m=3;capacity=3;N=n+m;target=(1<<(n*m))-1
    edges={c:sum(1<<(i*m+j) for i in range(n) for j in range(m)
                 if c>>i&1 and c>>(n+j)&1) for c in range(1<<N)}
    start=(0,0);q=deque([start]);distance={start:0};parent={};trials=0
    t0=time.process_time();goal=None
    while q:
        state=q.popleft();cache,done=state
        if done==target:
            goal=state;break
        for x in range(N):
            if cache>>x&1:continue
            evicts=[-1] if cache.bit_count()<capacity else [i for i in range(N) if cache>>i&1]
            for ev in evicts:
                trials+=1
                if trials>100000:raise RuntimeError('transition budget exceeded')
                c=(cache if ev<0 else cache&~(1<<ev))|(1<<x)
                nxt=(c,done|edges[c])
                if nxt not in distance:
                    distance[nxt]=distance[state]+1;parent[nxt]=(state,x,ev);q.append(nxt)
    if goal is None:raise RuntimeError('infeasible')
    steps=[];state=goal
    while state!=start:
        prev,x,ev=parent[state];steps.append({'load':x,'evict':None if ev<0 else ev});state=prev
    steps.reverse()
    out={'n':n,'m':m,'M':capacity,'reads':distance[goal],
         'states_discovered':len(distance),'transitions_examined':trials,'trace':steps,
         'provenance':'recomputed diagnostic; an earlier raw pilot record was not retained'}
    if include_measurements:
        out.update({'cpu_seconds':time.process_time()-t0,
                    'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    return out


def main() -> None:
    if hasattr(signal,'alarm'):signal.alarm(115)
    if hasattr(os,'sched_getaffinity') and hasattr(os,'sched_setaffinity'):
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS,(1500*1024*1024,1500*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    print(json.dumps(solve_pilot(),indent=2,sort_keys=True))


if __name__=='__main__':main()

"""Four targeted mutations for the two-phase factor-schedule checker."""
from __future__ import annotations
from copy import deepcopy
from integer_rank import compile_fragments, solve_rank
from factor_schedule_check import check_factor_schedule


def run() -> list[dict]:
    packet=solve_rank([[1,0],[0,1]])
    x=[2,3];y=[5,7];fast=0
    good=compile_fragments(packet,x,y,fast)
    check_factor_schedule(packet,x,y,fast,good)
    mutations=[]

    missing=deepcopy(good)
    index=next(i for i,e in enumerate(missing['events']) if e['op']=='write_slow')
    del missing['events'][index]
    mutations.append(('missing-slow-write',missing))

    wrong=deepcopy(good)
    event=next(e for e in wrong['events'] if e['op']=='write_slow')
    event['slot']=1  # In range, but belongs to the other factor and overloads its address.
    mutations.append(('wrong-slow-address',wrong))

    reload=deepcopy(good)
    index=next(i for i,e in enumerate(reload['events']) if e['op']=='read_slow_madd')
    reload['events'].insert(index+1,deepcopy(reload['events'][index]))
    mutations.append(('duplicate-slow-reload',reload))

    outside=deepcopy(good)
    event=next(e for e in outside['events'] if e['op']=='read_slow_madd')
    event['slot']=99
    mutations.append(('out-of-range-slow-access',outside))

    rows=[]
    for name,schedule in mutations:
        try:check_factor_schedule(packet,x,y,fast,schedule)
        except (ValueError,KeyError,TypeError) as exc:
            rows.append({'name':name,'result':'rejected','reason':str(exc)})
        else:raise AssertionError('Factor schedule mutation unexpectedly accepted: '+name)
    return rows

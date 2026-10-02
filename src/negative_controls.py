"""Deterministic adverse inputs. No test is a proof of a general theorem."""
from __future__ import annotations
from collections import Counter
from contextlib import closing
from copy import deepcopy
from bags import check_program, denote
from replay import Replay
from cache_check import check


def run(packet: dict) -> dict[str,list[dict]]:
    groups={
        'cache_rejections':[],
        'syntax_type_rejections':[],
        'semantic_differences':[],
        'lifecycle_tests':[],
    }
    def rejected(group,name,value,fn=check):
        try:fn(value)
        except (ValueError,KeyError,TypeError):groups[group].append({'name':name,'result':'rejected'})
        else:raise AssertionError('Negative control unexpectedly accepted: '+name)

    # Twelve malformed occurrence-cache certificates.
    p=deepcopy(packet);p['optimum']+=1;rejected('cache_rejections','wrong-optimum',p)
    p=deepcopy(packet);p['potential'][0]['h']+=1;rejected('cache_rejections','inflated-initial-potential',p)
    p=deepcopy(packet);p['potential']=[e for e in p['potential'] if e['cache']==0];rejected('cache_rejections','missing-positive-successors',p)
    p=deepcopy(packet);p['potential'].append(deepcopy(p['potential'][0]));rejected('cache_rejections','duplicate-potential-entry',p)
    p=deepcopy(packet);p['potential'][0]['cache']=2**20;rejected('cache_rejections','out-of-range-state',p)
    p=deepcopy(packet);p['trace']=p['trace'][:-1];rejected('cache_rejections','truncated-trace',p)
    p=deepcopy(packet);p['trace'][0]['evict']=0;rejected('cache_rejections','evict-absent-occurrence',p)
    p=deepcopy(packet);p['trace'][1]['load']=p['trace'][0]['load'];rejected('cache_rejections','read-resident-occurrence',p)
    p=deepcopy(packet);p['trace'][3]['evict']=None;rejected('cache_rejections','overfill-cache',p)
    p=deepcopy(packet);p['capacity']=1;rejected('cache_rejections','unsupported-capacity',p)
    p=deepcopy(packet);p['potential'][0]['h']=True;rejected('cache_rejections','boolean-potential-not-integer',p)
    p=deepcopy(packet);p['trace'][0]['extra']='not-an-action';rejected('cache_rejections','unknown-action-field',p)

    # Eight syntax/type/program-fragment rejections.
    base={'nodes':[{'op':'input','name':'R','schema':['int']},{'op':'input','name':'S','schema':['int']},{'op':'sum','left':0,'right':1}],'root':2}
    p=deepcopy(base);p['nodes'][2]['right']=2;rejected('syntax_type_rejections','cyclic-child',p,check_program)
    p=deepcopy(base);p['nodes'][1]['schema']=['int','int'];rejected('syntax_type_rejections','binary-schema-mismatch',p,check_program)
    p=deepcopy(base);p['nodes'][2]={'op':'project','arg':0,'cols':[1]};rejected('syntax_type_rejections','projection-column-out-of-range',p,check_program)
    p=deepcopy(base);p['nodes'][2]={'op':'filter','arg':0,'pred':{'kind':'eq','i':0,'j':1}};rejected('syntax_type_rejections','predicate-column-out-of-range',p,check_program)
    p=deepcopy(base);p['nodes'][1]['name']='R';p['nodes'][1]['schema']=['int?'];p['root']=0;p['nodes'].pop();rejected('syntax_type_rejections','inconsistent-source-schema',p,check_program)
    p=deepcopy(base);p['root']=True;rejected('syntax_type_rejections','boolean-root-not-index',p,check_program)
    p=deepcopy(base);p['nodes'][0]['schema']=['float'];rejected('syntax_type_rejections','unsupported-base-type',p,check_program)
    p=deepcopy(base);p['nodes'][2]['op']='aggregate';rejected('syntax_type_rejections','operator-outside-fragment',p,check_program)

    # Four semantics-changing but syntactically valid alternatives.
    db={'R':[[0],[0],[1]],'S':[[0],[1],[1]]}
    expected=denote(base,db)
    bad=Counter(set(expected.elements()));assert bad!=expected
    groups['semantic_differences'].append({'name':'set-deduplication','result':'distinguished'})
    p=deepcopy(base);p['nodes'][2]['op']='union';assert denote(p,db)!=expected
    groups['semantic_differences'].append({'name':'max-union-as-sum','result':'distinguished'})
    p['nodes'][2]['op']='diff';assert denote(p,db)!=Counter(x for x in map(tuple,db['R']) if list(x) not in db['S'])
    groups['semantic_differences'].append({'name':'bag-difference-as-antijoin','result':'distinguished'})
    p['nodes'][2]={'op':'left','left':0,'right':1,'pred':{'kind':'lt','i':0,'j':1}}
    assert denote(p,db)[(1,None)]==1
    groups['semantic_differences'].append({'name':'outer-padding-omission','result':'distinguished'})

    # Two generator-lifecycle tests: suspended frames must unwind.
    for name,limit in [('prefix-close',10_000),('read-cap-unwind',1)]:
        r=Replay(base,db,read_limit=limit)
        if limit==1:
            try:list(r.rows())
            except RuntimeError:pass
            else:raise AssertionError('Read guard did not trip')
        else:
            with closing(r.rows()) as it:next(it)
        assert r.stats.active_frames==0
        groups['lifecycle_tests'].append({'name':name,'result':'passed'})
    return groups

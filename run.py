#!/usr/bin/env python3
"""Reproduce and reconcile bounded deterministic evidence.

Invocation: python run.py reproduce --out /tmp/bag-evidence
            python run.py check
Each command uses one process and one worker. No network or shell subprocesses.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
from collections import Counter
from itertools import product
from typing import Any

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'formal'))
from bags import denote, frame_bound, cardinality_bounds, check_program
from replay import Replay
from cache_search import solve
from cache_check import check
from negative_controls import run as non_source_controls
from residual import synthesize
from residual_check import check_residual
from integer_rank import solve_rank, compile_fragments, bilinear
from integer_rank_check import check_rank
from factor_schedule_check import check_factor_schedule
from factor_schedule_controls import run as factor_schedule_controls
from positive_source import canonical_source, probe_extract, const, xvar, yvar, add, mul
from positive_source_check import quotient_extract
from capability_cases import run_separations
from rectangle_case import reconstruct_case
from pilot import solve_pilot
from semiring_kernel import verify_factor_packet


def dump(path:Path,value)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')


def rows_csv(path:Path,rows:list[dict])->None:
    if not rows:raise ValueError('cannot write empty CSV')
    fields=[]
    for row in rows:
        for key in row:
            if key not in fields:fields.append(key)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='raise');w.writeheader();w.writerows(rows)


def read_csv(path:Path)->list[dict[str,str]]:
    with path.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))


def keyed(rows:list[dict],label:str)->dict[str,dict]:
    out={}
    for row in rows:
        case_id=row.get('id')
        if type(case_id) is not str or not case_id or case_id in out:raise ValueError(f'{label}: invalid or duplicate id')
        out[case_id]=row
    return out


def int_field(row:dict[str,str],name:str)->int:
    raw=row.get(name)
    if raw is None or raw.strip()!=str(int(raw)):raise ValueError(f'noncanonical integer field {name}: {raw!r}')
    return int(raw)


def vector_probes(n:int)->list[list[int]]:
    values={(0,)*n,(1,)*n,(2,)*n,tuple(i%2 for i in range(n)),tuple((i+1)%2 for i in range(n))}
    for i in range(n):
        e=[0]*n;e[i]=1;values.add(tuple(e));e=[0]*n;e[i]=2;values.add(tuple(e))
    return [list(v) for v in sorted(values)]


def source_negative_controls()->list[dict]:
    cases=[
        ('pure-left',xvar(0),False),('pure-right',yvar(0),False),('constant',const(1),False),
        ('left-square',mul(mul(xvar(0),xvar(0)),yvar(0)),False),
        ('right-square',mul(xvar(0),mul(yvar(0),yvar(0))),False),
        ('mixed-linear-nonlinear',add(mul(xvar(0),yvar(0)),mul(mul(xvar(0),xvar(0)),yvar(0))),False),
        ('dead-nonlinear',mul(const(0),mul(mul(xvar(0),xvar(0)),yvar(0))),True),
    ]
    rows=[]
    for name,expr,should_accept in cases:
        source={'left_tags':1,'right_tags':1,'expression':expr};outcomes=[]
        for label,fn in [('numeric-probe',probe_extract),('monomial-quotient',quotient_extract)]:
            accepted=True
            try:fn(source)
            except ValueError:accepted=False
            if accepted!=should_accept:raise AssertionError((name,label,accepted,should_accept))
            outcomes.append({'checker':label,'accepted':accepted})
        rows.append({'name':name,'expected_accept':should_accept,'outcomes':outcomes})
    return rows


def execute_rank_schedules(packet:dict,matrix:list[list[int]])->dict[str,int]:
    comparisons=events=slow_writes=slow_reads=0
    xs=vector_probes(len(matrix));ys=vector_probes(len(matrix[0]))
    width=len(packet['witness']);levels=sorted({0,min(1,width),width})
    for x,y,fast in product(xs,ys,levels):
        generated=compile_fragments(packet,x,y,fast)
        checked=check_factor_schedule(packet,x,y,fast,generated)
        want=bilinear(matrix,x,y)
        if generated['value']!=want or checked['value']!=want:raise ValueError('factor schedule value mismatch')
        if generated['temporary_word_transfers']!=2*max(0,width-fast):raise ValueError('factor schedule traffic mismatch')
        comparisons+=1;events+=checked['events_checked'];slow_writes+=checked['slow_writes'];slow_reads+=checked['slow_reads']
    return {'comparisons':comparisons,'events':events,'slow_writes':slow_writes,'slow_reads':slow_reads,
            'x_reads':comparisons*len(matrix)*width,'y_reads':comparisons*len(matrix[0])*width}


def reproduce(out:Path)->None:
    if out.exists() and any(out.iterdir()):raise ValueError('Output directory must be empty')
    out.mkdir(parents=True,exist_ok=True);start=time.process_time();wall=time.monotonic()

    # 1. Restartable source semantics.
    cases=json.loads((ROOT/'inputs/semantic_cases.json').read_text())
    semantic=[];max_ops=max_arity=0
    for case in cases:
        p,db=case['program'],case['database'];expected=denote(p,db);replay=Replay(p,db,read_limit=1_000_000)
        actual=Counter(replay.rows());bounds=cardinality_bounds(p,db)
        assert actual==expected,case['id'];assert replay.stats.active_frames==0,case['id']
        assert replay.stats.peak_frames<=frame_bound(p),case['id'];assert sum(actual.values())<=bounds[p['root']],case['id']
        assert replay.stats.max_counter<=max(bounds),case['id'];schemas=check_program(p)
        max_ops=max(max_ops,len(p['nodes']));max_arity=max(max_arity,max(map(len,schemas)))
        semantic.append({'id':case['id'],'family':case['family'],'input_occurrences':sum(map(len,db.values())),
            'output_occurrences':sum(actual.values()),'base_reads':replay.stats.base_reads,
            'peak_logical_frames':replay.stats.peak_frames,'frame_bound':frame_bound(p),
            'maximum_counter':replay.stats.max_counter,'maximum_cardinality_bound':max(bounds),'equivalent':True})
    rows_csv(out/'semantic.csv',semantic)

    # 2. Occurrence-record cache certificates.
    cache=[];controls=None
    for case in json.loads((ROOT/'inputs/cache_cases.json').read_text()):
        packet=solve(case['n'],case['m'],case['capacity']);checked=check(packet)
        if (case['n'],case['m'],case['capacity'])==(3,3,3):controls=non_source_controls(packet)
        dump(out/'certificates'/(case['id']+'.json'),packet)
        cache.append({'id':case['id'],'n':case['n'],'m':case['m'],'capacity':case['capacity'],
            'optimal_reads':packet['optimum'],'search_states':packet['search_states'],
            'search_transitions':packet['search_transitions'],'potential_entries':checked['potential_entries'],
            'checked_inequalities':checked['checked_inequalities']})
    rows_csv(out/'cache.csv',cache)

    # 3. Positive-source admission, exact integer rank, and actual two-phase schedules.
    rank_rows=[];numeric_comparisons=source_probes=schedule_events=schedule_writes=schedule_reads=0
    for case in json.loads((ROOT/'inputs/rank_cases.json').read_text()):
        matrix=case['matrix'];source=canonical_source(matrix);probed=probe_extract(source,max_coefficient=8)
        quotient=quotient_extract(source,max_coefficient=8);assert probed['matrix']==quotient['matrix']==matrix
        source_probes+=probed['probes'];packet=solve_rank(matrix);checked=check_rank(packet);verify_factor_packet(packet)
        packet.update({'id':case['id'],'family':case['family'],'source':source,
                       'source_probe':probed,'source_quotient':quotient})
        dump(out/'certificates'/(case['id']+'.json'),packet)
        schedule=execute_rank_schedules(packet,matrix)
        numeric_comparisons+=schedule['comparisons'];schedule_events+=schedule['events']
        schedule_writes+=schedule['slow_writes'];schedule_reads+=schedule['slow_reads']
        rank_rows.append({'id':case['id'],'family':case['family'],'rows':len(matrix),'cols':len(matrix[0]),
            'rank':packet['rank'],'rank_one_atoms':packet['atom_count'],
            'potential_states':checked['potential_states'],'checked_inequalities':checked['checked_inequalities'],
            'source_nodes':probed['nodes'],'source_probes':probed['probes'],
            'numeric_schedule_comparisons':schedule['comparisons'],'schedule_events_checked':schedule['events'],
            'slow_writes_checked':schedule['slow_writes'],'slow_reads_checked':schedule['slow_reads']})
    rows_csv(out/'integer_rank.csv',rank_rows)

    # 4. Finite residual-state compiler in every possible Boolean 2x2 function.
    residual_rows=[]
    for case in json.loads((ROOT/'inputs/residual_cases.json').read_text()):
        first=synthesize(case['table'],0);variants=[];checks=[]
        for fast in range(first['code_bits']+2):
            packet=synthesize(case['table'],fast);checked=check_residual(packet);variants.append(packet);checks.append(checked)
        cert={'id':case['id'],'table':case['table'],'variants':variants};dump(out/'certificates'/(case['id']+'.json'),cert)
        residual_rows.append({'id':case['id'],'residual_classes':first['residual_classes'],
            'minimal_code_bits':first['code_bits'],'zero_fast_bit_transfers':first['temporary_bit_transfers'],
            'fast_capacities_checked':len(variants),'compiled_executions_checked':sum(c['executions_checked'] for c in checks)})
    rows_csv(out/'residual.csv',residual_rows)

    # 5. Cross-model witnesses, controls, and reconstructed diagnostics.
    rows_csv(out/'capability_separations.csv',run_separations())
    positive_cases=source_negative_controls();schedule_controls=factor_schedule_controls()
    if controls is None:raise AssertionError('3x3 cache control packet missing')
    dump(out/'negative_controls.json',{**controls,'positive_source':positive_cases,
                                       'factor_schedule_rejections':schedule_controls})
    group_sizes={name:len(rows) for name,rows in controls.items()}
    assert group_sizes=={'cache_rejections':12,'syntax_type_rejections':8,
                         'semantic_differences':4,'lifecycle_tests':2}
    assert len(positive_cases)==7 and len(schedule_controls)==4
    coarse=max(6,3+(9-2+1)//2)
    assert coarse==7 and next(x['optimal_reads'] for x in cache if x['n']==x['m']==x['capacity']==3)==8
    rectangle=reconstruct_case();dump(out/'rectangle_negative.json',rectangle)
    dump(out/'pilot.json',solve_pilot())

    declared_instances=len(cases)+len(cache)+len(rank_rows)+len(residual_rows)
    assert declared_instances==985 and declared_instances<=1000
    cache_obligations=sum(x['search_transitions']+x['checked_inequalities'] for x in cache)
    rank_inequalities=sum(x['checked_inequalities'] for x in rank_rows)
    residual_executions=sum(x['compiled_executions_checked'] for x in residual_rows)
    legacy_non_source=sum(group_sizes.values())
    obligations=(len(cases)*5+cache_obligations+legacy_non_source+rank_inequalities+
                 numeric_comparisons+source_probes+residual_executions+2*len(positive_cases))
    assert obligations==30083,obligations
    summary={'declared_program_or_certificate_instances':declared_instances,
        'semantic_cases':len(cases),'template_families':len({c['family'] for c in cases}),
        'exhaustive_core_templates':11,'exhaustive_core_input_pairs':81,'boundary_cases':5,
        'semantic_failures':0,'cache_instances':len(cache),
        'cache_rejection_controls':group_sizes['cache_rejections'],
        'syntax_type_rejection_controls':group_sizes['syntax_type_rejections'],
        'semantic_difference_controls':group_sizes['semantic_differences'],
        'lifecycle_controls':group_sizes['lifecycle_tests'],
        'legacy_non_source_controls':legacy_non_source,'positive_source_cases':len(positive_cases),
        'legacy_controls_total':legacy_non_source+len(positive_cases),
        'factor_schedule_rejection_controls':len(schedule_controls),
        'all_control_cases':legacy_non_source+len(positive_cases)+len(schedule_controls),
        'negative_control_failures':0,'integer_rank_instances':len(rank_rows),
        'residual_function_instances':len(residual_rows),'maximum_operators':max_ops,
        'maximum_tuple_arity':max_arity,'maximum_base_reads_per_semantic_case':max(r['base_reads'] for r in semantic),
        'total_modeled_base_reads':sum(r['base_reads'] for r in semantic),
        'maximum_logical_frames':max(r['peak_logical_frames'] for r in semantic),
        'cache_search_transitions':sum(r['search_transitions'] for r in cache),
        'cache_certificate_inequalities':sum(r['checked_inequalities'] for r in cache),
        'rank_certificate_inequalities':rank_inequalities,
        'factor_schedule_numeric_comparisons':numeric_comparisons,
        'factor_schedule_legality_checks':numeric_comparisons,
        'factor_schedule_events_checked':schedule_events,
        'factor_schedule_slow_writes_checked':schedule_writes,
        'factor_schedule_slow_reads_checked':schedule_reads,
        'positive_bilinearity_probes':source_probes,'residual_compiled_executions':residual_executions,
        'rectangle_overlap_diagnostics':1,'recomputed_cache_pilots':1,
        'counted_validation_and_transition_obligations':obligations,
        'obligation_count_scope':'legacy 30,083 definition retained for comparability; new event-level schedule checks and four schedule mutations are reported separately',
        'rank_distribution':{str(k):sum(1 for r in rank_rows if r['rank']==k) for k in sorted({r['rank'] for r in rank_rows})},
        'cpu_seconds':time.process_time()-start,'wall_seconds':time.monotonic()-wall,
        'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'workers':1,'child_processes':0,'random_seed':None,
        'rss_scope':'whole Python harness including input data, Counter oracle, exact dynamic programs, and checkers; Linux KiB',
        'logical_memory_scope':'model-level state only; not Python allocation or a physical performance claim',
        'claim_scope':'finite executable cross-checks and proof certificates accompanying separately stated general theorems'}
    dump(out/'summary.json',summary);print(json.dumps(summary,indent=2,sort_keys=True))


def _assert_csv_ids(rows:list[dict[str,str]],inputs:dict[str,dict],label:str)->dict[str,dict[str,str]]:
    mapped=keyed(rows,label)
    if set(mapped)!=set(inputs):raise ValueError(f'{label}: IDs do not match retained inputs')
    return mapped


def verify_retained_payloads(root:Path=ROOT,execute_schedules:bool=True)->dict[str,Any]:
    semantic_inputs=keyed(json.loads((root/'inputs/semantic_cases.json').read_text()),'semantic inputs')
    cache_inputs=keyed(json.loads((root/'inputs/cache_cases.json').read_text()),'cache inputs')
    rank_inputs=keyed(json.loads((root/'inputs/rank_cases.json').read_text()),'rank inputs')
    residual_inputs=keyed(json.loads((root/'inputs/residual_cases.json').read_text()),'residual inputs')
    semantic_rows=_assert_csv_ids(read_csv(root/'results/semantic.csv'),semantic_inputs,'semantic results')
    cache_rows=_assert_csv_ids(read_csv(root/'results/cache.csv'),cache_inputs,'cache results')
    rank_rows=_assert_csv_ids(read_csv(root/'results/integer_rank.csv'),rank_inputs,'rank results')
    residual_rows=_assert_csv_ids(read_csv(root/'results/residual.csv'),residual_inputs,'residual results')
    summary=json.loads((root/'results/summary.json').read_text())

    # Bind every semantic row to its source payload and recompute the reported values.
    total_reads=0
    for case_id,case in semantic_inputs.items():
        p,db=case['program'],case['database'];replay=Replay(p,db,read_limit=1_000_000);actual=Counter(replay.rows())
        expected=denote(p,db);bounds=cardinality_bounds(p,db);row=semantic_rows[case_id]
        if actual!=expected or row['family']!=case['family'] or row['equivalent']!='True':raise ValueError(f'{case_id}: semantic payload mismatch')
        expected_fields={'input_occurrences':sum(map(len,db.values())),'output_occurrences':sum(actual.values()),
            'base_reads':replay.stats.base_reads,'peak_logical_frames':replay.stats.peak_frames,
            'frame_bound':frame_bound(p),'maximum_counter':replay.stats.max_counter,'maximum_cardinality_bound':max(bounds)}
        for name,value in expected_fields.items():
            if int_field(row,name)!=value:raise ValueError(f'{case_id}: semantic field {name} mismatch')
        total_reads+=expected_fields['base_reads']

    cache_checked=0;cache_transitions=cache_ineq=0
    for case_id,case in cache_inputs.items():
        packet=json.loads((root/'results/certificates'/f'{case_id}.json').read_text());row=cache_rows[case_id]
        for name in ('n','m','capacity'):
            if packet.get(name)!=case[name] or int_field(row,name)!=case[name]:raise ValueError(f'{case_id}: cache payload {name} mismatch')
        checked=check(packet)
        expected={'optimal_reads':packet['optimum'],'search_states':packet['search_states'],
                  'search_transitions':packet['search_transitions'],'potential_entries':checked['potential_entries'],
                  'checked_inequalities':checked['checked_inequalities']}
        for name,value in expected.items():
            if int_field(row,name)!=value:raise ValueError(f'{case_id}: cache result {name} mismatch')
        cache_checked+=1;cache_transitions+=packet['search_transitions'];cache_ineq+=checked['checked_inequalities']

    rank_checked=0;rank_ineq=source_probes=schedule_comparisons=schedule_events=slow_writes=slow_reads=0
    for case_id,case in rank_inputs.items():
        packet=json.loads((root/'results/certificates'/f'{case_id}.json').read_text());row=rank_rows[case_id]
        if packet.get('id')!=case_id or packet.get('family')!=case['family'] or packet.get('matrix')!=case['matrix']:
            raise ValueError(f'{case_id}: rank certificate not bound to input payload')
        expected_source=canonical_source(case['matrix']);probed=probe_extract(expected_source,max_coefficient=8);quotient=quotient_extract(expected_source,max_coefficient=8)
        if packet.get('source')!=expected_source or packet.get('source_probe')!=probed or packet.get('source_quotient')!=quotient:
            raise ValueError(f'{case_id}: rank source extraction payload mismatch')
        checked=check_rank(packet);verify_factor_packet(packet)
        expected={'rows':len(case['matrix']),'cols':len(case['matrix'][0]),'rank':checked['rank'],
                  'rank_one_atoms':packet['atom_count'],'potential_states':checked['potential_states'],
                  'checked_inequalities':checked['checked_inequalities'],'source_nodes':probed['nodes'],
                  'source_probes':probed['probes']}
        if row['family']!=case['family']:raise ValueError(f'{case_id}: rank family mismatch')
        for name,value in expected.items():
            if int_field(row,name)!=value:raise ValueError(f'{case_id}: rank result {name} mismatch')
        schedule=execute_rank_schedules(packet,case['matrix']) if execute_schedules else {
            'comparisons':int_field(row,'numeric_schedule_comparisons'),'events':int_field(row,'schedule_events_checked'),
            'slow_writes':int_field(row,'slow_writes_checked'),'slow_reads':int_field(row,'slow_reads_checked')}
        for name,key_name in [('numeric_schedule_comparisons','comparisons'),('schedule_events_checked','events'),
                              ('slow_writes_checked','slow_writes'),('slow_reads_checked','slow_reads')]:
            if int_field(row,name)!=schedule[key_name]:raise ValueError(f'{case_id}: rank schedule field {name} mismatch')
        rank_checked+=1;rank_ineq+=checked['checked_inequalities'];source_probes+=probed['probes']
        schedule_comparisons+=schedule['comparisons'];schedule_events+=schedule['events'];slow_writes+=schedule['slow_writes'];slow_reads+=schedule['slow_reads']

    residual_checked=0;residual_executions=0
    for case_id,case in residual_inputs.items():
        cert=json.loads((root/'results/certificates'/f'{case_id}.json').read_text());row=residual_rows[case_id]
        if cert.get('id')!=case_id or cert.get('table')!=case['table']:raise ValueError(f'{case_id}: residual certificate not bound to input table')
        variants=cert.get('variants');first=synthesize(case['table'],0)
        expected_capacities=list(range(first['code_bits']+2))
        if not isinstance(variants,list) or len(variants)!=len(expected_capacities):raise ValueError(f'{case_id}: residual variant count mismatch')
        executions=0
        for fast,variant in zip(expected_capacities,variants):
            expected=synthesize(case['table'],fast)
            if variant!=expected or variant.get('table')!=cert['table'] or variant.get('fast_bits')!=fast:
                raise ValueError(f'{case_id}: residual variant {fast} not bound to parent table')
            executions+=check_residual(variant)['executions_checked'];residual_checked+=1
        expected_row={'residual_classes':first['residual_classes'],'minimal_code_bits':first['code_bits'],
                      'zero_fast_bit_transfers':first['temporary_bit_transfers'],'fast_capacities_checked':len(variants),
                      'compiled_executions_checked':executions}
        for name,value in expected_row.items():
            if int_field(row,name)!=value:raise ValueError(f'{case_id}: residual result {name} mismatch')
        residual_executions+=executions

    negatives=json.loads((root/'results/negative_controls.json').read_text())
    fresh_non_source=non_source_controls(json.loads((root/'results/certificates/cache-07.json').read_text()))
    for name,expected_count in [('cache_rejections',12),('syntax_type_rejections',8),('semantic_differences',4),('lifecycle_tests',2)]:
        if fresh_non_source[name]!=negatives.get(name) or len(fresh_non_source[name])!=expected_count:
            raise ValueError(f'negative controls: {name} mismatch')
    positive=source_negative_controls();schedule_mutations=factor_schedule_controls()
    if positive!=negatives.get('positive_source') or schedule_mutations!=negatives.get('factor_schedule_rejections'):
        raise ValueError('positive-source or factor-schedule controls mismatch')

    retained_rectangle=json.loads((root/'results/rectangle_negative.json').read_text())
    if retained_rectangle!=reconstruct_case():raise ValueError('rectangle overlap diagnostic mismatch')
    retained_pilot=json.loads((root/'results/pilot.json').read_text());fresh_pilot=solve_pilot(include_measurements=False)
    for name,value in fresh_pilot.items():
        if retained_pilot.get(name)!=value:raise ValueError(f'pilot deterministic field {name} mismatch')

    expected_summary={'declared_program_or_certificate_instances':985,'semantic_cases':896,'cache_instances':9,
        'integer_rank_instances':64,'residual_function_instances':16,'total_modeled_base_reads':total_reads,
        'cache_search_transitions':cache_transitions,'cache_certificate_inequalities':cache_ineq,
        'rank_certificate_inequalities':rank_ineq,'factor_schedule_numeric_comparisons':schedule_comparisons,
        'factor_schedule_legality_checks':schedule_comparisons,'factor_schedule_events_checked':schedule_events,
        'factor_schedule_slow_writes_checked':slow_writes,'factor_schedule_slow_reads_checked':slow_reads,
        'positive_bilinearity_probes':source_probes,'residual_compiled_executions':residual_executions,
        'cache_rejection_controls':12,'syntax_type_rejection_controls':8,'semantic_difference_controls':4,
        'lifecycle_controls':2,'legacy_non_source_controls':26,'positive_source_cases':7,
        'legacy_controls_total':33,'factor_schedule_rejection_controls':4,'all_control_cases':37,
        'counted_validation_and_transition_obligations':30083,'rectangle_overlap_diagnostics':1,
        'recomputed_cache_pilots':1,'negative_control_failures':0}
    for name,value in expected_summary.items():
        if summary.get(name)!=value:raise ValueError(f'summary {name}: expected {value}, found {summary.get(name)!r}')
    return {'semantic_rows':len(semantic_rows),'cache_certificates':cache_checked,'rank_certificates':rank_checked,
            'residual_variants':residual_checked,'factor_schedules':schedule_comparisons,
            'factor_schedule_events':schedule_events,'legacy_controls':33,'additional_schedule_mutations':4,
            'declared_instances':985,'counted_obligations':30083}


def check_retained()->None:
    print(json.dumps(verify_retained_payloads(ROOT,execute_schedules=True),indent=2,sort_keys=True))


def main()->None:
    if not __debug__:raise RuntimeError('Run without -O: assertions are required validation')
    if hasattr(signal,'alarm'):signal.alarm(115)
    resource.setrlimit(resource.RLIMIT_AS,(1536*1024**2,1536*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(100,110))
    if hasattr(os,'sched_getaffinity') and hasattr(os,'sched_setaffinity'):
        available=os.sched_getaffinity(0);os.sched_setaffinity(0,{min(available)})
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['reproduce','check']);parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    if args.command=='reproduce':
        if args.out is None:parser.error('reproduce requires --out')
        reproduce(args.out.resolve())
    else:check_retained()


if __name__=='__main__':
    try:main()
    except (AssertionError,ValueError,KeyError,RuntimeError,RecursionError,TypeError) as error:
        print(f'VALIDATION FAILED: {error}',file=sys.stderr);sys.exit(1)

#!/usr/bin/env python3
"""Regressions for the contract repairs requested during artifact review."""
from __future__ import annotations
import copy
import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'formal')]
from audit import audit,AuditError
from bags import frame_bound
from replay import Replay
from integer_rank import compile_fragments,solve_rank
from integer_rank_check import check_rank
from factor_schedule_check import check_factor_schedule
from factor_schedule_controls import run as schedule_controls
from positive_source import canonical_source,const
from semiring_kernel import Const,normalize,verify_factor_packet


def projected_input(name:str,depth:int,start:int=0):
    nodes=[{'op':'input','name':name,'schema':['int']}]
    for _ in range(depth):nodes.append({'op':'project','arg':start+len(nodes)-1,'cols':[0]})
    return nodes,start+len(nodes)-1


class ReplayFrameRecurrence(unittest.TestCase):
    def test_empty_left_deep_right_union_needs_eleven_frames(self):
        nodes=[{'op':'empty','schema':['int']}]
        right,ri=projected_input('B',4,start=1);nodes.extend(right)
        nodes.append({'op':'union','left':0,'right':ri});program={'nodes':nodes,'root':len(nodes)-1}
        replay=Replay(program,{'B':[[7]]});self.assertEqual(list(replay.rows()),[(7,)])
        self.assertEqual(frame_bound(program),11)
        self.assertEqual(replay.stats.peak_frames,11)
        self.assertNotEqual(frame_bound(program),8)

    def test_max_union_bound_is_left_right_asymmetric(self):
        def build(left_depth,right_depth):
            left,li=projected_input('L',left_depth,0);right_start=len(left)
            right,ri=projected_input('R',right_depth,right_start);nodes=left+right
            nodes.append({'op':'union','left':li,'right':ri});return {'nodes':nodes,'root':len(nodes)-1}
        left_deep=build(3,0);right_deep=build(0,3)
        self.assertEqual(frame_bound(left_deep),6);self.assertEqual(frame_bound(right_deep),9)
        for program,want in [(left_deep,6),(right_deep,9)]:
            replay=Replay(program,{'L':[[1]],'R':[[2]]});list(replay.rows())
            self.assertEqual(replay.stats.peak_frames,want)

    def test_nested_max_union_recurrence(self):
        base=[{'op':'input','name':'A','schema':['int']},{'op':'input','name':'B','schema':['int']},{'op':'input','name':'C','schema':['int']}]
        left={'nodes':base+[{'op':'union','left':0,'right':1},{'op':'union','left':3,'right':2}],'root':4}
        right={'nodes':base+[{'op':'union','left':1,'right':2},{'op':'union','left':0,'right':3}],'root':4}
        self.assertEqual(frame_bound(left),5);self.assertEqual(frame_bound(right),7)
        for program in (left,right):
            replay=Replay(program,{'A':[[0]],'B':[[1]],'C':[[2]]});list(replay.rows())
            self.assertLessEqual(replay.stats.peak_frames,frame_bound(program))


class StrictNaturalAndSchedules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rank058=json.loads((ROOT/'results/certificates/rank-058.json').read_text())

    def test_rank_058_fractional_factor_rejected_by_both_checkers(self):
        packet=copy.deepcopy(self.rank058);packet['witness'][0]['u']=[0.5];packet['witness'][0]['v']=[2]
        for checker in (check_rank,verify_factor_packet):
            with self.subTest(checker=checker.__name__),self.assertRaises(ValueError):checker(packet)

    def test_double_negative_boolean_and_noninteger_matrix_rejected(self):
        variants=[]
        packet=copy.deepcopy(self.rank058);packet['witness'][0]['u']=[-1];packet['witness'][0]['v']=[-1];variants.append(packet)
        packet=copy.deepcopy(self.rank058);packet['witness'][0]['u']=[True];variants.append(packet)
        packet=copy.deepcopy(self.rank058);packet['matrix']=[[1.0]];variants.append(packet)
        for packet in variants:
            for checker in (check_rank,verify_factor_packet):
                with self.subTest(packet=packet,checker=checker.__name__),self.assertRaises(ValueError):checker(packet)

    def test_semiring_and_source_constructors_reject_non_naturals(self):
        for value in (0.5,True,-1):
            with self.subTest(value=value),self.assertRaises(ValueError):normalize(Const(value))
            with self.subTest(source=value),self.assertRaises(ValueError):const(value)
        with self.assertRaises(ValueError):canonical_source([[True]])

    def test_two_buffer_schedule_with_zero_fast_words_and_multiple_factors(self):
        packet=solve_rank([[1,0],[0,1]]);schedule=compile_fragments(packet,[2,3],[5,7],0)
        checked=check_factor_schedule(packet,[2,3],[5,7],0,schedule)
        self.assertEqual(checked['value'],31);self.assertEqual(checked['transient_buffers'],2)
        self.assertEqual((checked['slow_writes'],checked['slow_reads']), (2,2))
        self.assertEqual(checked['temporary_word_transfers'],4)

    def test_nonminimal_width_two_all_ones_factorization_is_feasible_not_rank_optimal(self):
        packet={'matrix':[[1,1],[1,1]],'rows':2,'cols':2,'witness':[
            {'u':[1,0],'v':[1,1],'atom':[[1,1],[0,0]]},
            {'u':[0,1],'v':[1,1],'atom':[[0,0],[1,1]]}]}
        exact=solve_rank(packet['matrix']);self.assertEqual(exact['rank'],1)
        schedule=compile_fragments(packet,[2,3],[5,7],0)
        checked=check_factor_schedule(packet,[2,3],[5,7],0,schedule)
        self.assertEqual(checked['factor_width'],2);self.assertEqual(checked['temporary_word_transfers'],4)
        self.assertEqual(checked['value'],60)

    def test_four_schedule_mutations_are_rejected(self):
        rows=schedule_controls();self.assertEqual([r['name'] for r in rows],[
            'missing-slow-write','wrong-slow-address','duplicate-slow-reload','out-of-range-slow-access'])
        self.assertTrue(all(r['result']=='rejected' for r in rows))


class PayloadBindingAudit(unittest.TestCase):
    def copied_repo(self):
        temp=tempfile.TemporaryDirectory();dest=Path(temp.name)/'repo'
        shutil.copytree(ROOT,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        return temp,dest

    def test_same_id_rank_058_target_mutation_is_rejected(self):
        temp,root=self.copied_repo()
        try:
            path=root/'inputs/rank_cases.json';cases=json.loads(path.read_text())
            case=next(c for c in cases if c['id']=='rank-058');case['matrix'][0][0]=2
            path.write_text(json.dumps(cases,indent=2,sort_keys=True)+'\n')
            with self.assertRaises((AuditError,ValueError)):audit(root)
        finally:temp.cleanup()

    def test_same_id_rank_result_row_mutation_is_rejected(self):
        temp,root=self.copied_repo()
        try:
            path=root/'results/integer_rank.csv'
            with path.open(newline='') as f:rows=list(csv.DictReader(f));fields=list(rows[0])
            next(r for r in rows if r['id']=='rank-058')['rank']='2'
            with path.open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
            with self.assertRaises((AuditError,ValueError)):audit(root)
        finally:temp.cleanup()


if __name__=='__main__':unittest.main()

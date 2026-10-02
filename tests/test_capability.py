#!/usr/bin/env python3
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'formal'))
from residual import synthesize,execute,dot_table
from residual_check import check_residual
from integer_rank import solve_rank,compile_fragments,bilinear
from integer_rank_check import check_rank
from positive_source import canonical_source,probe_extract,xvar,yvar,mul
from positive_source_check import quotient_extract
from residual_theorem import verify as verify_residual_theorem
from semiring_kernel import verify_factor_packet
from logic_kernel import Var,Refl,Trans,check

class CapabilityContracts(unittest.TestCase):
    def test_residual_compiler_exact(self):
        table=[[0,1],[1,0]];packet=synthesize(table,0)
        self.assertEqual(check_residual(packet)['residual_classes'],2)
        self.assertEqual([[execute(packet,x,y) for y in range(2)] for x in range(2)],table)

    def test_residual_partition_mutation_rejected(self):
        packet=synthesize([[0,1],[1,0]],0);packet['class_of_x'][1]=0
        with self.assertRaises(ValueError):check_residual(packet)

    def test_residual_cost_mutation_rejected(self):
        packet=synthesize([[0,1],[1,0]],0);packet['temporary_bit_transfers']-=1
        with self.assertRaises(ValueError):check_residual(packet)

    def test_identity_integer_rank(self):
        a=[[1,0,0],[0,1,0],[0,0,1]];packet=solve_rank(a)
        self.assertEqual(check_rank(packet)['rank'],3)
        x=[2,1,0];y=[1,2,1]
        self.assertEqual(compile_fragments(packet,x,y,1)['value'],bilinear(a,x,y))

    def test_rank_witness_mutation_rejected(self):
        packet=solve_rank([[1,0],[0,1]])
        packet['witness'][0]['atom'][0][0]+=1
        with self.assertRaises(ValueError):check_rank(packet)

    def test_rank_potential_mutation_rejected(self):
        packet=solve_rank([[1,0],[0,1]])
        for item in packet['potential']:
            if item['state']==packet['matrix']:item['value']+=1
        with self.assertRaises(ValueError):check_rank(packet)

    def test_two_admission_methods_agree(self):
        source=canonical_source([[2,1],[0,1]])
        self.assertEqual(probe_extract(source)['matrix'],quotient_extract(source)['matrix'])

    def test_nonlinear_source_rejected(self):
        source={'left_tags':1,'right_tags':1,'expression':mul(mul(xvar(0),xvar(0)),yvar(0))}
        for checker in (probe_extract,quotient_extract):
            with self.assertRaises(ValueError):checker(source)

    def test_dot_residual_classes(self):
        packet=synthesize(dot_table(5),5)
        self.assertEqual(check_residual(packet)['residual_classes'],32)
        self.assertEqual(packet['temporary_bit_transfers'],0)

    def test_first_order_proof_term(self):
        self.assertTrue(verify_residual_theorem()['checked'])

    def test_logic_kernel_rejects_bad_transitivity(self):
        a=Var('a','T');b=Var('b','T')
        with self.assertRaises(ValueError):check(Trans(Refl(a),Refl(b)))

    def test_semiring_mutation_rejected(self):
        packet=solve_rank([[1,0],[0,1]])
        self.assertTrue(verify_factor_packet(packet)['checked'])
        bad=copy.deepcopy(packet);bad['witness'][0]['u'][0]+=1
        with self.assertRaises(ValueError):verify_factor_packet(bad)

if __name__=='__main__':unittest.main()

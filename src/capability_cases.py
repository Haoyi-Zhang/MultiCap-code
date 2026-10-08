"""Strict capability-separation witnesses and compact campaign drivers."""
from __future__ import annotations
from itertools import product
from residual import synthesize, dot_table
from residual_check import check_residual
from integer_rank import solve_rank,compile_fragments,bilinear
from integer_rank_check import check_rank


def identity(n):return [[1 if i==j else 0 for j in range(n)] for i in range(n)]

def run_separations():
    rows=[]
    for n in range(1,7):
        rp=synthesize(dot_table(n),fast_bits=n)
        rc=check_residual(rp)
        rank=solve_rank(identity(n));ic=check_rank(rank)
        if rc['residual_classes']!=(1<<n) or rc['code_bits']!=n or ic['rank']!=n:
            raise AssertionError('identity/dot separation failed')
        rows.append({'family':'bit-packing-vs-positive-counts','n':n,
                     'residual_classes':rc['residual_classes'],'arbitrary_bit_fast_bits':n,
                     'arbitrary_bit_transfers':rp['temporary_bit_transfers'],
                     'positive_integer_rank':rank['rank'],'positive_fast_words':1,
                     'positive_word_transfers':2*max(0,n-1)})
    # The remaining separation rows report theorem-backed example constants;
    # they are not reconstructed from retained certificates here.
    rows.append({'family':'occurrence-vs-value-compression','n':3,
                 'occurrence_two_slot_reads':10,'value_two_slot_reads':6,
                 'residual_classes':'not-comparable','arbitrary_bit_fast_bits':'',
                 'arbitrary_bit_transfers':'','positive_integer_rank':'',
                 'positive_fast_words':'','positive_word_transfers':''})
    rows.append({'family':'replay-vs-one-way-barrier','n':3,
                 'restartable_derived_transfers':0,'barrier_positive_word_transfers':4,
                 'residual_classes':'','arbitrary_bit_fast_bits':'',
                 'arbitrary_bit_transfers':'','positive_integer_rank':3,
                 'positive_fast_words':1,'positive_word_transfers':4})
    return rows

"""Exact residual-state synthesis for finite two-phase functions.

The prefix sees x, the continuation sees y.  A certificate groups x values by
identical residual rows y |-> F(x,y), assigns a shortest fixed-width class code,
and describes a split between persistent fast bits and spilled slow bits.
This module synthesizes; residual_check.py independently validates.
"""
from __future__ import annotations
from typing import Any, Iterable


def bit_width(nclasses: int) -> int:
    if type(nclasses) is not int or nclasses < 1:
        raise ValueError("at least one residual class is required")
    return (nclasses - 1).bit_length()


def residual_rows(table: list[list[Any]]) -> list[tuple[Any, ...]]:
    if not table or not table[0]:
        raise ValueError("nonempty finite domains required")
    width=len(table[0])
    if any(len(row)!=width for row in table):
        raise ValueError("ragged function table")
    return [tuple(row) for row in table]


def synthesize(table: list[list[Any]], fast_bits: int) -> dict:
    if type(fast_bits) is not int or fast_bits < 0:
        raise ValueError("fast_bits must be a nonnegative integer")
    rows=residual_rows(table)
    representatives: list[tuple[Any,...]]=[]
    class_of=[]
    index={}
    for row in rows:
        if row not in index:
            index[row]=len(representatives)
            representatives.append(row)
        class_of.append(index[row])
    k=bit_width(len(representatives))
    slow=max(0,k-fast_bits)
    codes=[format(i,f'0{k}b') if k else '' for i in range(len(representatives))]
    return {
        'x_size':len(rows),
        'y_size':len(rows[0]),
        'table':[list(row) for row in rows],
        'residual_classes':len(representatives),
        'code_bits':k,
        'fast_bits':fast_bits,
        'slow_bits':slow,
        'temporary_bit_transfers':2*slow,
        'class_of_x':class_of,
        'codes':codes,
        'representatives':[list(row) for row in representatives],
        'model':'finite deterministic one-way barrier; output only after barrier; bit transfers',
    }


def execute(packet: dict, x: int, y: int) -> Any:
    """Execute the synthesized normal form, not the original table lookup by x.

    Prefix maps x to a residual-class code.  The barrier retains/reloads that
    code.  Continuation selects only by decoded class and y.
    """
    cls=packet['class_of_x'][x]
    code=packet['codes'][cls]
    fast=code[:packet['fast_bits']]
    slow=code[packet['fast_bits']:]
    restored=fast+slow
    decoded=int(restored,2) if restored else 0
    return packet['representatives'][decoded][y]


def all_boolean_tables(x_size: int, y_size: int) -> Iterable[list[list[int]]]:
    cells=x_size*y_size
    for mask in range(1<<cells):
        yield [[(mask>>(x*y_size+y))&1 for y in range(y_size)] for x in range(x_size)]


def dot_table(n: int) -> list[list[int]]:
    if n < 1 or n > 10:
        raise ValueError("bounded diagnostic n")
    vectors=[tuple((mask>>i)&1 for i in range(n)) for mask in range(1<<n)]
    return [[sum(a*b for a,b in zip(x,y)) for y in vectors] for x in vectors]

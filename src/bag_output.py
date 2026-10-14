"""Canonical observations for the typed finite bag-valued residual interface.

Raw JSON lists are ordered observations. This adapter instead preserves a
bag's schema and positive tuple multiplicities, independent of emission order.
"""
from collections import Counter


def encode_bag_output(rows, schema):
    if type(schema) not in (list, tuple) or len(schema) > 16:
        raise ValueError('a finite typed tuple schema is required')
    if any(kind not in ('int', 'int?') for kind in schema):
        raise ValueError('unsupported bag column type')
    if type(rows) not in (list, tuple):
        raise ValueError('finite occurrence rows are required')
    counts = Counter()
    for row in rows:
        if type(row) not in (list, tuple) or len(row) != len(schema):
            raise ValueError('bag tuple arity mismatch')
        for value, kind in zip(row, schema):
            if not (type(value) is int or value is None and kind == 'int?'):
                raise ValueError('bag tuple type mismatch')
        counts[tuple(row)] += 1
    # Type tags make nullable integer ordering total without comparing None
    # with integers. This ordering is presentation only, not an observation.
    def order(row):
        return tuple((0, 0) if value is None else (1, value) for value in row)
    return {'schema': list(schema),
            'counts': [[list(row), counts[row]] for row in sorted(counts, key=order)]}

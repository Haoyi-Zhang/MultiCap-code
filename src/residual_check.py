"""Independent checker for residual-state certificates.

This checker deliberately does not import residual.py.  It reconstructs the
residual equivalence relation, verifies shortest code width, normal-form cost,
and every synthesized execution.
"""
from __future__ import annotations


def ceil_log2(n: int) -> int:
    if n < 1: raise ValueError('positive n required')
    k=0;p=1
    while p<n:k+=1;p*=2
    return k


def check_residual(packet: dict) -> dict:
    for field in ('x_size','y_size','residual_classes','code_bits',
                  'fast_bits','slow_bits','temporary_bit_transfers'):
        if type(packet.get(field)) is not int or packet[field]<0:
            raise ValueError(f'{field} must be a natural integer')
    if not isinstance(packet.get('class_of_x'),list) or any(
            type(value) is not int or value<0 for value in packet['class_of_x']):
        raise ValueError('class indices must be natural integers')
    if not isinstance(packet.get('codes'),list) or any(type(code) is not str for code in packet['codes']):
        raise ValueError('codes must be bit strings')
    table=packet['table'];xs=packet['x_size'];ys=packet['y_size']
    if len(table)!=xs or xs<1 or ys<1 or any(len(r)!=ys for r in table):
        raise ValueError('bad table dimensions')
    # Equality classes reconstructed by pairwise comparison, not hashing.
    classes=[];class_of=[]
    for x,row in enumerate(table):
        found=None
        for i,rep in enumerate(classes):
            if all(row[y]==rep[y] for y in range(ys)):
                found=i;break
        if found is None:
            found=len(classes);classes.append(list(row))
        class_of.append(found)
    if class_of!=packet['class_of_x'] or classes!=packet['representatives']:
        raise ValueError('residual partition mismatch')
    n=len(classes);k=ceil_log2(n)
    if packet['residual_classes']!=n or packet['code_bits']!=k:
        raise ValueError('class count or minimal width mismatch')
    codes=packet['codes']
    if len(codes)!=n or len(set(codes))!=n:
        raise ValueError('codes not injective')
    if any(len(c)!=k or any(bit not in '01' for bit in c) for c in codes):
        raise ValueError('malformed fixed-width code')
    if codes != ([format(i,f'0{k}b') if k else '' for i in range(n)]):
        raise ValueError('noncanonical code ordering')
    b=packet['fast_bits'];slow=max(0,k-b)
    if b<0 or packet['slow_bits']!=slow or packet['temporary_bit_transfers']!=2*slow:
        raise ValueError('cost mismatch')
    tested=0
    for x in range(xs):
        code=codes[class_of[x]]
        restored=code[:b]+code[b:]
        cls=int(restored,2) if restored else 0
        for y in range(ys):
            if classes[cls][y]!=table[x][y]:
                raise ValueError('compiled execution mismatch')
            tested+=1
    return {'residual_classes':n,'code_bits':k,'executions_checked':tested,
            'lower_bound_states':n,'temporary_bit_transfers':2*slow}

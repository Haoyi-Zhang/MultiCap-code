#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from residual_theorem import verify
from semiring_kernel import verify_factor_packet

def main():
    theorem=verify();packets=[]
    for p in sorted((ROOT/'results/certificates').glob('rank-*.json')):
        packets.append(verify_factor_packet(json.loads(p.read_text())))
    if len(packets)!=64:raise ValueError('expected 64 factor packets')
    out={'first_order_theorems_checked':1,'factor_polynomial_certificates_checked':len(packets),
         'total_target_monomials':sum(x['target_monomials'] for x in packets),
         'kernel_scope':'sorted first-order equality/implication/forall plus independent natural-semiring normalization',
         'not_claimed':'not an external proof assistant or a verification of the Python interpreter',
         'residual_theorem':theorem}
    print(json.dumps(out,indent=2,sort_keys=True))
if __name__=='__main__':main()

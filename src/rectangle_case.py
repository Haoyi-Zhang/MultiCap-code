"""Deterministic 7-versus-8 overlap diagnostic for Boolean rectangles."""
from __future__ import annotations


def reconstruct_case() -> dict:
    # R1={0,1}x{0,1}; R2={1,2}x{1,2}.  Their support union has seven cells,
    # but adding the two rank-one indicator matrices counts the shared centre twice.
    left1=(1,1,0);right1=(1,1,0)
    left2=(0,1,1);right2=(0,1,1)
    atom1=[[left1[i]*right1[j] for j in range(3)] for i in range(3)]
    atom2=[[left2[i]*right2[j] for j in range(3)] for i in range(3)]
    additive=[[atom1[i][j]+atom2[i][j] for j in range(3)] for i in range(3)]
    support=[[1 if additive[i][j] else 0 for j in range(3)] for i in range(3)]
    x=y=[1,1,1]
    support_value=sum(support[i][j]*x[i]*y[j] for i in range(3) for j in range(3))
    additive_value=sum(additive[i][j]*x[i]*y[j] for i in range(3) for j in range(3))
    if support_value!=7 or additive_value!=8 or additive[1][1]!=2:
        raise AssertionError('rectangle diagnostic construction changed')
    return {
        'id':'rectangle-overlap-7-vs-8',
        'domain':{'left_tags':3,'right_tags':3,'probe_x':x,'probe_y':y},
        'rectangles':[{'left_indicator':list(left1),'right_indicator':list(right1),'atom':atom1},
                      {'left_indicator':list(left2),'right_indicator':list(right2),'atom':atom2}],
        'support_union_matrix':support,
        'additive_rectangle_matrix':additive,
        'correct_support_value':support_value,
        'naive_additive_value':additive_value,
        'overlap_cell':[1,1],
        'overlap_multiplicity':additive[1][1],
        'provenance':'deterministically reconstructed from the stated 7-versus-8 property; no earlier retained raw result was available'
    }

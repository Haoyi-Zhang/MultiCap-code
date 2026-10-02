#!/usr/bin/env python3
"""Six bounded contracts supplementing (not replacing) the retained campaign."""
import sys
import unittest
import resource
import signal
from pathlib import Path
from contextlib import closing
from collections import Counter
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from replay import Replay
from bags import denote

class Contracts(unittest.TestCase):
    def test_constructor_does_not_scan_source(self):
        p={'nodes':[{'op':'input','name':'R','schema':['int']}],'root':0}
        e=Replay(p,{'R':[[0],[1]]})
        self.assertEqual(e.stats.base_reads,0)
        self.assertEqual(list(e.rows()),[(0,),(1,)])
        self.assertEqual(e.stats.base_reads,2)

    def test_invalid_source_validation_is_counted(self):
        p={'nodes':[{'op':'input','name':'R','schema':['int']}],'root':0}
        e=Replay(p,{'R':[[True]]})
        with self.assertRaises(ValueError):list(e.rows())
        self.assertEqual(e.stats.base_reads,1)
        self.assertEqual(e.stats.active_frames,0)

    def test_noninjective_projection_preserves_duplicates(self):
        p={'nodes':[{'op':'input','name':'R','schema':['int','int']},
            {'op':'project','arg':0,'cols':[0]}],'root':1}
        db={'R':[[0,1],[0,2]]}
        self.assertEqual(Counter(Replay(p,db).rows()),Counter({(0,):2}))

    def test_colliding_null_padding_is_additive(self):
        p={'nodes':[{'op':'input','name':'R','schema':['int?']},
            {'op':'input','name':'S','schema':['int?']},
            {'op':'full','left':0,'right':1,'pred':{'kind':'eq','i':0,'j':1}}],'root':2}
        db={'R':[[None]],'S':[[None]]}
        self.assertEqual(Counter(Replay(p,db).rows()),Counter({(None,None):2}))
        self.assertEqual(denote(p,db),Counter({(None,None):2}))

    def test_prefix_closure_unwinds(self):
        p={'nodes':[{'op':'input','name':'R','schema':['int']}],'root':0}
        e=Replay(p,{'R':[[0],[0],[1]]})
        self.assertEqual(e.count(0,(0,),prefix=1),1)
        self.assertEqual(e.stats.base_reads,1)
        self.assertEqual(e.stats.active_frames,0)

    def test_outer_consumer_closure_unwinds(self):
        p={'nodes':[{'op':'input','name':'R','schema':['int']},
            {'op':'product','left':0,'right':0}],'root':1}
        e=Replay(p,{'R':[[0],[1]]})
        with closing(e.rows()) as rows:self.assertEqual(next(rows),(0,0))
        self.assertEqual(e.stats.active_frames,0)

if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(1536*1024**2,1536*1024**2))
    resource.setrlimit(resource.RLIMIT_CPU,(100,110))
    signal.alarm(115)
    unittest.main()

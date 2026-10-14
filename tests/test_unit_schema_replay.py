"""Unit-schema multiplicities and cursor closure in benign finite bag programs."""
from collections import Counter
from itertools import product
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from bags import denote, frame_bound
from replay import Replay


class UnitSchemaReplayTests(unittest.TestCase):
    def test_unit_values_are_not_deduplicated(self):
        for left, right, op in product(range(5), range(5), ('sum','diff','inter','union','product')):
            program = {'nodes': [{'op':'input','name':'L','schema':[]},
                                 {'op':'input','name':'R','schema':[]},
                                 {'op':op,'left':0,'right':1}], 'root':2}
            database = {'L':[[] for _ in range(left)], 'R':[[] for _ in range(right)]}
            count = {'sum':left+right,'diff':max(left-right,0),'inter':min(left,right),
                     'union':max(left,right),'product':left*right}[op]
            expected = Counter({():count}) if count else Counter()
            replay = Replay(program, database)
            self.assertEqual(Counter(replay.rows()), expected)
            self.assertEqual(denote(program, database), expected)
            self.assertEqual(replay.stats.active_frames, 0)
            self.assertLessEqual(replay.stats.peak_frames, frame_bound(program))

    def test_empty_projection_preserves_occurrence_counts_and_prefix_close(self):
        program = {'nodes':[{'op':'input','name':'R','schema':['int?']},
                            {'op':'project','arg':0,'cols':[]},
                            {'op':'union','left':1,'right':1}], 'root':2}
        database = {'R':[[None],[0],[0],[-1]]}
        expected = Counter({():4})
        self.assertEqual(denote(program,database),expected)
        replay = Replay(program,database)
        cursor = replay.rows()
        self.assertEqual(next(cursor),())
        cursor.close()
        self.assertEqual(replay.stats.active_frames,0)
        self.assertEqual(Counter(replay.rows()),expected)
        self.assertEqual(replay.stats.active_frames,0)


if __name__ == '__main__':
    unittest.main()

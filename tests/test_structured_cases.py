import importlib.util
import unittest
from unittest.mock import patch
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"validation"/"structured_cases.py"
s=importlib.util.spec_from_file_location("structured_cases",P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class StructuredCaseTests(unittest.TestCase):
    def test_small_campaign(self):
        rows,summary=m.run(trials_per_shape=1,evals=2)
        self.assertGreater(summary["instances"],20)
        self.assertEqual(summary["zero_or_better_fraction"],1.0)
        self.assertTrue(all(r["certified_traffic"]<=r["column_baseline_traffic"] for r in rows))
    def test_compiled_campaign_preserves_formula_input_selection(self):
        streams=[]
        real_random=m.random.Random
        class TracedRandom(real_random):
            def __init__(self,*args):
                super().__init__(*args)
                self.draws=[]
                streams.append(self)
            def randrange(self,*args):
                result=super().randrange(*args)
                self.draws.append(('range',args,result))
                return result
            def shuffle(self,values):
                super().shuffle(values)
                self.draws.append(('shuffle',tuple(values)))
        with patch.object(m.random,'Random',TracedRandom):
            rows,summary=m.run(trials_per_shape=1,evals=2)
            actual,executed=m.run(trials_per_shape=1,evals=2,execute_schedules=True)
        self.assertEqual(streams[0].draws,streams[1].draws)
        self.assertEqual(streams[0].getstate(),streams[1].getstate())
        self.assertEqual(actual,rows)
        self.assertEqual(executed['compiled_factor_schedules_checked'],len(rows))
        self.assertEqual(executed['compiled_column_schedules_checked'],len(rows))
        self.assertEqual(executed['compiled_permuted_schedules_checked'],summary['instances'])
    def test_independent_event_rejection_is_not_hidden(self):
        original=m.check_factor_schedule
        for fail_at in (1,2,3):
            calls=0
            def checked(*args):
                nonlocal calls
                calls+=1
                if calls==fail_at:raise ValueError('event rejection')
                return original(*args)
            with self.subTest(fail_at=fail_at),patch.object(m,'check_factor_schedule',side_effect=checked):
                with self.assertRaisesRegex(ValueError,'event rejection'):
                    m.run(trials_per_shape=1,evals=2,execute_schedules=True)
                self.assertEqual(calls,fail_at)
if __name__=="__main__":unittest.main()

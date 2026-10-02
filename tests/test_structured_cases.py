import importlib.util
import unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"validation"/"structured_cases.py"
s=importlib.util.spec_from_file_location("structured_cases",P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class StructuredCaseTests(unittest.TestCase):
    def test_small_campaign(self):
        rows,summary=m.run(trials_per_shape=1,evals=2)
        self.assertGreater(summary["instances"],20)
        self.assertEqual(summary["zero_or_better_fraction"],1.0)
        self.assertTrue(all(r["certified_traffic"]<=r["column_baseline_traffic"] for r in rows))
if __name__=="__main__":unittest.main()

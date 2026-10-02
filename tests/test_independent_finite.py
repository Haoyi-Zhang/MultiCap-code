import importlib.util
import random
import unittest
from pathlib import Path

P=Path(__file__).resolve().parents[1]/"validation"/"independent_finite_checks.py"
spec=importlib.util.spec_from_file_location("independent_finite_checks",P)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
class IndependentFiniteTests(unittest.TestCase):
    def test_residual_fresh_trials(self): self.assertEqual(m.check_residual_trials(random.Random(m.SEED),20)['trials'],20)
    def test_integer_rank_exhaustive(self): self.assertEqual(m.check_integer_rank_exhaustive()['matrices'],256)
    def test_cache(self): self.assertEqual(m.check_cache()['instances'],16)
    def test_retained_rank_certificates(self):
        root=Path(__file__).resolve().parents[1]
        self.assertEqual(m.verify_existing_factor_certificates(root)['certificates_found_and_checked'],64)
if __name__=='__main__': unittest.main()

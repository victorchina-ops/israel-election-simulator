"""Known exact null tails across and below the signed64 mass boundary."""
from pathlib import Path
import importlib.util
import sys
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
HELPERS=ROOT/'artifacts/strict-post-close'
sys.path.insert(0,str(HELPERS))
from compressed_searchsorted_exact import ScalarBlock,compressed_searchsorted_tail
spec=importlib.util.spec_from_file_location('independent_mass_test',HELPERS/'independent-compressed-counts.py')
independent=importlib.util.module_from_spec(spec);spec.loader.exec_module(independent)

class ExactMassTests(unittest.TestCase):
    def check_null(self,n,mass,threshold,numerator,denominator):
        values=np.array([-1.,1.]);counts=np.array([mass//2,mass//2],dtype=np.int64)
        blocks=[ScalarBlock(values,counts,mass) for _ in range(n)]
        total=mass**n;expected=total*numerator//denominator
        primary=compressed_searchsorted_tail(blocks,threshold)
        secondary,universe,_=independent.direct_tail_counts([[(values,counts)] for _ in range(n)],[threshold])
        self.assertEqual(primary['totalPermutations'],total)
        self.assertEqual(universe,total)
        self.assertEqual(primary['extremeCount'],expected)
        self.assertEqual(int(secondary[0]),expected)

    def test_ordinary_integer_mass(self):self.check_null(2,120,2,1,2)
    def test_large_universe_still_within_signed64(self):self.check_null(2,2**30,2,1,2)
    def test_whole_universe_exceeds_signed64(self):self.check_null(2,2**40,2,1,2)
    def test_a_cartesian_half_exceeds_signed64(self):self.check_null(3,2**40,3,1,4)
    def test_zero_observed_includes_whole_large_universe(self):self.check_null(3,2**40,0,1,1)

if __name__=='__main__':unittest.main()

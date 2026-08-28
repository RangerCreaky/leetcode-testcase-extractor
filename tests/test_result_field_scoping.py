import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "main"))

from problem_solver import ProblemSolver


class EmptyElement:
    def find_elements(self, by, xpath):
        return []


class ResultFieldScopingTests(unittest.TestCase):
    def test_equals_label_is_preferred_over_code_token(self):
        equals_xpath, plain_xpath = ProblemSolver._field_label_xpaths("nums")

        self.assertIn("nums =", equals_xpath)
        self.assertNotIn(" or ", equals_xpath)
        self.assertIn("nums", plain_xpath)

    def test_missing_local_copy_control_does_not_search_global_buttons(self):
        solver = ProblemSolver.__new__(ProblemSolver)
        self.assertEqual(solver._copy_full_result_value(EmptyElement(), EmptyElement()), "")


if __name__ == "__main__":
    unittest.main()

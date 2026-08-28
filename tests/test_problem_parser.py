import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "main"))

from problem_parser import (
    compact_submission_source,
    default_return_statement,
    parse_python_signature,
)


class ParsePythonSignatureTests(unittest.TestCase):
    def test_standard_leetcode_signature(self):
        source = """class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        
"""
        self.assertEqual(
            parse_python_signature(source),
            (["nums", "target"], ["List[int]", "int"], "List[int]"),
        )

    def test_multiline_signature_and_nested_annotations(self):
        source = """class Solution:
    def combine(
        self,
        values: Dict[str, Tuple[int, int]],
        limit: int = 10,
    ) -> Optional[List[int]]:
"""
        self.assertEqual(
            parse_python_signature(source),
            (
                ["values", "limit"],
                ["Dict[str, Tuple[int, int]]", "int"],
                "Optional[List[int]]",
            ),
        )

    def test_missing_method_is_an_actionable_error(self):
        with self.assertRaisesRegex(ValueError, "Could not find a Python method"):
            parse_python_signature("class Solution:\n    pass\n")


class DefaultReturnStatementTests(unittest.TestCase):
    def test_scalar_sentinels(self):
        self.assertEqual(default_return_statement("int"), "return -9000000000000000")
        self.assertEqual(default_return_statement(" float "), "return float('inf')")

    def test_other_types_use_none(self):
        self.assertEqual(default_return_statement("List[int]"), "return")


class CompactSubmissionSourceTests(unittest.TestCase):
    def test_large_literal_is_hashed_only_in_submission_source(self):
        values = list(range(150))
        source = """class Solution:
    def solve(self, nums, target):
        if nums == {!r} and target == 9: return [1, 2]
        return
""".format(values)

        compact = compact_submission_source(source, literal_threshold=100)

        self.assertIn("import hashlib", compact)
        self.assertIn("hashlib.sha256", compact)
        self.assertLess(len(compact), len(source))
        namespace = {}
        exec(compact, namespace)
        self.assertEqual(namespace["Solution"]().solve(values, 9), [1, 2])
        self.assertIsNone(namespace["Solution"]().solve(values + [150], 9))

    def test_scalar_check_precedes_large_hash(self):
        values = list(range(150))
        source = """class Solution:
    def solve(self, nums, target):
        if nums == {!r} and target == 9: return [1, 2]
""".format(values)

        compact = compact_submission_source(source, literal_threshold=100)
        condition_line = next(line for line in compact.splitlines() if line.lstrip().startswith("if "))

        self.assertLess(condition_line.index("target == 9"), condition_line.index("hashlib.sha256"))

    def test_short_literal_source_is_unchanged(self):
        source = "class Solution:\n    def solve(self, nums):\n        if nums == [1, 2]: return [0, 1]"
        self.assertEqual(compact_submission_source(source), source)


if __name__ == "__main__":
    unittest.main()

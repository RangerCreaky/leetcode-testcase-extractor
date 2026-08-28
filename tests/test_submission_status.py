import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "main"))

from locators import ResultConsole


class SubmissionStatusTests(unittest.TestCase):
    def test_console_status(self):
        self.assertEqual(ResultConsole.canonical_status("Wrong Answer"), "Wrong Answer")

    def test_full_submission_heading_with_pass_count(self):
        self.assertEqual(
            ResultConsole.canonical_status("Wrong Answer\n0 / 65 testcases passed"),
            "Wrong Answer",
        )

    def test_unrelated_heading_is_ignored(self):
        self.assertEqual(ResultConsole.canonical_status("All Submissions"), "")

    def test_current_full_submission_result_locator_is_included(self):
        self.assertIn("submission-result", ResultConsole.STATUS_CSS)


if __name__ == "__main__":
    unittest.main()

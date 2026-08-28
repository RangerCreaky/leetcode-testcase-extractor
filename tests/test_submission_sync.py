import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "main"))

from problem_solver import ProblemSolver


class SubmissionSynchronizationTests(unittest.TestCase):
    def solver_with_result(self, retry_message="", status="Wrong Answer", fingerprint=None):
        solver = ProblemSolver.__new__(ProblemSolver)
        solver._retryable_message = lambda: retry_message
        solver._result_status = lambda: status
        solver._result_fingerprint = lambda: fingerprint
        return solver

    def test_old_terminal_result_is_not_accepted(self):
        old_result = ("Wrong Answer", "old panel")
        solver = self.solver_with_result(fingerprint=old_result)

        self.assertFalse(solver._submission_outcome(old_result)(None))

    def test_changed_terminal_result_is_accepted(self):
        old_result = ("Wrong Answer", "old panel")
        new_result = ("Wrong Answer", "new panel")
        solver = self.solver_with_result(fingerprint=new_result)

        self.assertEqual(
            solver._submission_outcome(old_result)(None),
            ("status", "Wrong Answer"),
        )

    def test_retryable_message_wins_over_stale_result(self):
        old_result = ("Wrong Answer", "old panel")
        solver = self.solver_with_result(
            retry_message="too frequently",
            fingerprint=old_result,
        )

        self.assertEqual(
            solver._submission_outcome(old_result)(None),
            ("retry", "too frequently"),
        )

    def test_submission_id_is_read_from_current_result_url(self):
        self.assertEqual(
            ProblemSolver._submission_id(
                "https://leetcode.com/problems/two-sum/submissions/2122668485/"
            ),
            "2122668485",
        )


if __name__ == "__main__":
    unittest.main()

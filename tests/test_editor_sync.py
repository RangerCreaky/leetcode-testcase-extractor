import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "main"))

from problem_page_helper import ProblemPageHelper
from problem_solver import ProblemSolver


class EditorSynchronizationTests(unittest.TestCase):
    def test_source_normalization_handles_clipboard_line_endings(self):
        self.assertEqual(
            ProblemPageHelper.normalize_editor_source("one\r\ntwo\r\n"),
            "one\ntwo",
        )

    def test_editor_match_uses_complete_copied_source(self):
        source = "class Solution:\n    def solve(self):\n        return"
        copied_values = iter(["return", source])
        solver = ProblemSolver.__new__(ProblemSolver)
        solver._copy_editor_source = lambda: next(copied_values)
        condition = solver._editor_source_equals(source)

        self.assertFalse(condition(None))
        self.assertTrue(condition(None))

    def test_source_mismatch_reports_first_changed_line(self):
        self.assertEqual(
            ProblemSolver._first_source_mismatch("one\ntwo", "one\nthree"),
            "line 2 (expected 'two', got 'three')",
        )

    def test_editor_replacement_retries_after_partial_paste(self):
        class FakeEditor:
            def __init__(self):
                self.keys = []

            def send_keys(self, *keys):
                self.keys.append(keys)

        class FakeWait:
            def __init__(self, editor):
                self.editor = editor

            def until(self, condition):
                return self.editor

        editor = FakeEditor()
        solver = ProblemSolver.__new__(ProblemSolver)
        solver.wait = FakeWait(editor)
        solver.modifier_key = "COMMAND"
        solver.click = lambda element: None
        solver.set_clipboard = lambda source: None
        solver._set_monaco_model_source = lambda element, source: False
        attempts = []

        def verify(source):
            attempts.append(source)
            solver._last_editor_source = (
                "class Solution:\n        returnclass Solution:"
                if len(attempts) == 1
                else source
            )
            return len(attempts) == 2

        solver._wait_for_editor_source = verify

        solver._replace_editor_source("class Solution:\n    pass")

        self.assertEqual(len(attempts), 2)
        self.assertEqual(len(editor.keys), 8)

    def test_invalid_generated_testcase_is_rejected_before_write(self):
        original_source = "class Solution:\n    pass"
        with tempfile.TemporaryDirectory() as directory:
            testcase_file = Path(directory) / "problem.py"
            testcase_file.write_text(original_source, encoding="utf-8")
            solver = ProblemSolver.__new__(ProblemSolver)
            solver.filePath = testcase_file
            solver.testcase_strings = ["if nums == class Solution: return [0]"]
            solver.defaultSubmission = "return"

            with self.assertRaisesRegex(
                RuntimeError,
                "Refusing to save an invalid generated testcase",
            ):
                solver.add_testcase()

            self.assertEqual(testcase_file.read_text(encoding="utf-8"), original_source)

    def test_empty_starter_method_is_validated_with_fallback_return(self):
        starter_source = (
            "class Solution:\n"
            "    def longestPalindrome(self, s: str) -> str:"
        )
        with tempfile.TemporaryDirectory() as directory:
            testcase_file = Path(directory) / "problem.py"
            testcase_file.write_text(starter_source, encoding="utf-8")
            submitted = []
            solver = ProblemSolver.__new__(ProblemSolver)
            solver.filePath = testcase_file
            solver.testcase_strings = [""]
            solver.defaultSubmission = "return"
            solver._replace_editor_source = submitted.append

            solver.add_testcase()

            self.assertEqual(testcase_file.read_text(encoding="utf-8"), starter_source)
            self.assertEqual(len(submitted), 1)
            self.assertTrue(submitted[0].endswith("\n        return"))
            compile(submitted[0], "<submission>", "exec")


if __name__ == "__main__":
    unittest.main()

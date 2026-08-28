import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "main"))

from runner import load_problem_sheet, main, mark_completed, selected_row_numbers


class ProblemSheetTests(unittest.TestCase):
    def make_sheet(self, directory):
        path = Path(directory) / "problem_data.csv"
        path.write_text(
            "Number,Title,Link\n"
            "1,One,https://example.test/one\n"
            "2,Two,https://example.test/two\n",
            encoding="utf-8",
        )
        return path

    def test_missing_completed_column_is_initialized_false(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_sheet(directory)
            fieldnames, rows = load_problem_sheet(path)

            self.assertIn("Completed", fieldnames)
            self.assertEqual([row["Completed"] for row in rows], ["FALSE", "FALSE"])

    def test_all_selects_only_incomplete_rows(self):
        rows = [{"Completed": "TRUE"}, {"Completed": "false"}, {"Completed": "Yes"}]
        self.assertEqual(selected_row_numbers(["--all"], rows), [1])

    def test_mark_completed_updates_only_requested_row(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_sheet(directory)
            load_problem_sheet(path)
            mark_completed(1, path)

            with path.open(newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(rows[0]["Completed"], "FALSE")
            self.assertEqual(rows[1]["Completed"], "TRUE")

    def test_all_cannot_be_combined_with_row_numbers(self):
        with self.assertRaisesRegex(ValueError, "cannot be combined"):
            selected_row_numbers(["--all", "2"], [{"Completed": "FALSE"}])

    def test_all_marks_accepted_problems_and_moves_to_the_next_one(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_sheet(directory)

            with patch("runner.solveProblem", return_value="Accepted") as solve:
                self.assertEqual(main(["--all"], path), 0)

            self.assertEqual(solve.call_count, 2)
            with path.open(newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(
                [row["Completed"] for row in rows],
                ["TRUE", "TRUE"],
            )


if __name__ == "__main__":
    unittest.main()

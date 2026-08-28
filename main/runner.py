import csv
import os
import sys
import tempfile
from pathlib import Path

from debug_wrapper import DebugWrapper
from problem_solver import ProblemSolver


PROBLEM_SHEET = Path("problem_data/problem_data.csv")
COMPLETED_COLUMN = "Completed"
TRUE_VALUES = {"1", "true", "yes", "y"}


def solveProblem(problem_link, filePath):
    problemSolver = ProblemSolver(problem_link, filePath)
    problemSolver = DebugWrapper(problemSolver)
    try:
        if problemSolver.overCharacterLimit():
            print("Already at the configured character limit", flush=True)
            return None
        problemSolver.login()
        problemSolver.load_problem()
        problemSolver.switch_to_python()
        problemSolver.reset_to_default()

        problemSolver.parse_inputs()
        problemSolver.setup_file()
        problemSolver.add_testcase()
        outcome = problemSolver.submit()

        while outcome != "Accepted":
            problemSolver.parse_testcase()
            problemSolver.add_testcase()
            outcome = problemSolver.submit()

        print("Completed {}: Accepted".format(filePath), flush=True)
        return outcome
    finally:
        problemSolver.quit()


def _is_completed(row):
    return str(row.get(COMPLETED_COLUMN, "")).strip().lower() in TRUE_VALUES


def _write_problem_sheet(fieldnames, rows, sheet_path=PROBLEM_SHEET):
    sheet_path = Path(sheet_path)
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=sheet_path.parent,
            prefix=sheet_path.name + ".",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_name = temporary_file.name
            writer = csv.DictWriter(
                temporary_file,
                fieldnames=fieldnames,
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary_name, sheet_path)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)


def load_problem_sheet(sheet_path=PROBLEM_SHEET):
    sheet_path = Path(sheet_path)
    with sheet_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    required = {"Number", "Title", "Link"}
    missing = required.difference(fieldnames)
    if missing:
        raise RuntimeError(
            "Problem sheet is missing required columns: {}".format(
                ", ".join(sorted(missing))
            )
        )

    changed = False
    if COMPLETED_COLUMN not in fieldnames:
        fieldnames.append(COMPLETED_COLUMN)
        changed = True
    for row in rows:
        normalized = "TRUE" if _is_completed(row) else "FALSE"
        if row.get(COMPLETED_COLUMN) != normalized:
            row[COMPLETED_COLUMN] = normalized
            changed = True

    if changed:
        _write_problem_sheet(fieldnames, rows, sheet_path)
    return fieldnames, rows


def mark_completed(row_number, sheet_path=PROBLEM_SHEET):
    fieldnames, rows = load_problem_sheet(sheet_path)
    if row_number < 0 or row_number >= len(rows):
        raise IndexError("Problem row {} is out of range".format(row_number))
    rows[row_number][COMPLETED_COLUMN] = "TRUE"
    _write_problem_sheet(fieldnames, rows, sheet_path)


def selected_row_numbers(arguments, rows):
    if "--all" in arguments:
        if len(arguments) != 1:
            raise ValueError("--all cannot be combined with explicit row numbers")
        return [index for index, row in enumerate(rows) if not _is_completed(row)]

    selected = []
    for argument in arguments:
        row_number = int(argument)
        if row_number < 0 or row_number >= len(rows):
            raise IndexError("Problem row {} is out of range".format(row_number))
        selected.append(row_number)
    return selected


def main(arguments=None, sheet_path=PROBLEM_SHEET):
    arguments = sys.argv[1:] if arguments is None else list(arguments)
    if not arguments:
        raise SystemExit(
            "Usage: python3 main/runner.py --all | <problem-row-number> "
            "[<problem-row-number> ...]"
        )

    _, rows = load_problem_sheet(sheet_path)
    try:
        row_numbers = selected_row_numbers(arguments, rows)
    except (ValueError, IndexError) as error:
        raise SystemExit(str(error)) from error

    if not row_numbers:
        print("All problems in the sheet are already completed.", flush=True)
        return 0

    for row_number in row_numbers:
        # Reload before each problem so externally edited completion flags are
        # respected during a long --all run.
        _, current_rows = load_problem_sheet(sheet_path)
        row = current_rows[row_number]
        if _is_completed(row):
            print(
                "Skipping {}. {}: already completed".format(
                    row["Number"],
                    row["Title"],
                ),
                flush=True,
            )
            continue

        problem_name = row["Number"] + ". " + row["Title"]
        outcome = solveProblem(row["Link"], problem_name)
        if outcome == "Accepted":
            mark_completed(row_number, sheet_path)
            print("Marked {} as completed in {}".format(problem_name, sheet_path), flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

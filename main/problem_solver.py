import ast
import os
import re
import time
from csv import DictReader
from pathlib import Path

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from locators import LoginPage, ResultConsole, SingleProblemPage
from problem_page_helper import ProblemPageHelper
from problem_parser import (
    compact_submission_source,
    default_return_statement,
    parse_python_signature,
)
from selenium_base import SeleniumBase


class ProblemSolver(SeleniumBase):
    def __init__(self, prob_link, filePath, waitTime=20):
        super().__init__(waitTime)
        self.filePath = Path("data") / filePath
        self.prob_link = prob_link
        self.variables = []
        self.var_types = []
        self.output_type = ""
        self.defaultSubmission = SingleProblemPage.DEFAULT_SUBMISSION
        self.testcase_strings = [""]
        self.current_submission_source = ""

    def overCharacterLimit(self):
        if not self.filePath.is_file():
            return False
        compact_source = compact_submission_source(
            self.filePath.read_text(encoding="utf-8")
        )
        return len(compact_source.encode("utf-8")) > 95000

    def login(self):
        self.driver.get(LoginPage.URL)
        self.wait.until(EC.presence_of_element_located((By.ID, LoginPage.USERNAME_BTN_ID)))
        self.wait.until_not(EC.presence_of_element_located((By.ID, LoginPage.LOADING_SCREEN_ID)))

        filename = Path("main/leetcode_cookies.csv")
        if filename.is_file():
            with filename.open(newline="") as file:
                for row in DictReader(file):
                    cookie = self._normalize_cookie(row)
                    if cookie.get("name") and cookie.get("value") is not None:
                        self.driver.add_cookie(cookie)
            self.driver.refresh()
            self.wait.until(lambda driver: "/accounts/login" not in driver.current_url)
        else:
            print(
                "\n*** No main/leetcode_cookies.csv found. Log in manually in "
                "the Chrome window; the extractor will continue afterward. ***\n",
                flush=True,
            )
            self.wait.until(lambda driver: "/accounts/login" not in driver.current_url)

    @staticmethod
    def _normalize_cookie(row):
        cookie = {
            key.strip(): value.strip()
            for key, value in row.items()
            if key and value is not None and value.strip() != ""
        }
        allowed = {"name", "value", "path", "domain", "secure", "httpOnly", "expiry", "sameSite"}
        cookie = {key: value for key, value in cookie.items() if key in allowed}
        for boolean_key in ("secure", "httpOnly"):
            if boolean_key in cookie:
                cookie[boolean_key] = cookie[boolean_key].lower() == "true"
        if "expiry" in cookie:
            cookie["expiry"] = int(float(cookie["expiry"]))
        if cookie.get("sameSite", "").lower() not in {"strict", "lax", "none"}:
            cookie.pop("sameSite", None)
        elif "sameSite" in cookie:
            cookie["sameSite"] = cookie["sameSite"].title()
        return cookie

    def load_problem(self, firstTime=True):
        self.driver.get(self.prob_link)
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, SingleProblemPage.EDITOR_CSS)))
        if firstTime:
            self.wait.until(EC.visibility_of_element_located((By.XPATH, SingleProblemPage.LANGUAGE_BTN_XPATH)))

    def switch_to_python(self):
        language_button = self.visible_element(By.XPATH, SingleProblemPage.LANGUAGE_BTN_XPATH)
        if language_button is None:
            raise RuntimeError("Could not find LeetCode's language picker")
        if language_button.text.strip() != "Python3":
            self.click(language_button)
            python_option = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, SingleProblemPage.PYTHON_OPTION_XPATH))
            )
            self.click(python_option)
        self.wait.until(ProblemPageHelper.editor_contains_python_method())

    def reset_to_default(self):
        reset_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, SingleProblemPage.RESET_BUTTON_XPATH))
        )
        self.click(reset_button)
        confirm_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, SingleProblemPage.RESET_CONFIRM_XPATH))
        )
        self.click(confirm_button)
        self.wait.until(ProblemPageHelper.editor_contains_python_method())

    def parse_inputs(self):
        source = self._copy_editor_source()
        variables, var_types, output_type = parse_python_signature(source)
        self.variables = variables
        self.var_types = var_types
        self.output_type = output_type
        self.defaultSubmission = default_return_statement(output_type)

    def setup_file(self):
        if self.filePath.is_file():
            return
        self.filePath.parent.mkdir(parents=True, exist_ok=True)
        self.filePath.write_text(self._copy_editor_source(), encoding="utf-8")

    def _result_status_element(self):
        for element in self.driver.find_elements(By.CSS_SELECTOR, ResultConsole.STATUS_CSS):
            try:
                if element.is_displayed() and ResultConsole.canonical_status(element.text):
                    return element
            except Exception:
                continue
        return None

    def _result_status(self):
        element = self._result_status_element()
        return ResultConsole.canonical_status(element.text) if element is not None else ""

    def _result_panel(self):
        status = self._result_status_element()
        if status is None:
            raise RuntimeError("LeetCode's submission result panel is not visible")
        return status.find_element(By.XPATH, ResultConsole.RESULT_PANEL_XPATH)

    @staticmethod
    def _field_label_xpaths(name):
        # Input labels in the current result UI include ` =`.  Prefer that
        # exact form so Python tokens named `nums`, `target`, etc. in the Code
        # section cannot be mistaken for result-field labels.
        return (
            ".//*[normalize-space(.)='{0} =']".format(name),
            ".//*[normalize-space(.)='{0}']".format(name),
        )

    def _field_value_container(self, panel, name):
        labels = []
        for xpath in self._field_label_xpaths(name):
            labels = [
                label
                for label in panel.find_elements(By.XPATH, xpath)
                if label.is_displayed()
            ]
            if labels:
                break
        if not labels:
            raise RuntimeError("Could not find result field {!r}".format(name))
        label = labels[0]
        for xpath in (
            "./following-sibling::*[normalize-space(.) != ''][1]",
            "../following-sibling::*[normalize-space(.) != ''][1]",
        ):
            for candidate in label.find_elements(By.XPATH, xpath):
                if candidate.is_displayed() and candidate.text.strip():
                    return label, candidate
        raise RuntimeError("Could not read the value for result field {!r}".format(name))

    @staticmethod
    def _clean_result_value(value):
        ignored = {"View all", "View more", "View less", "Copy", "Copied!"}
        lines = [line for line in value.splitlines() if line.strip() not in ignored]
        return "\n".join(lines).strip()

    def _copy_full_result_value(self, label, container):
        copy_icon_xpath = ".//*[contains(concat(' ', @class, ' '), ' fa-clone ')]"
        root_xpaths = (
            "./ancestor::*[{}][1]".format(copy_icon_xpath),
            "./ancestor::*[.//button[contains(translate(@aria-label, 'COPY', 'copy'), 'copy') "
            "or contains(translate(@title, 'COPY', 'copy'), 'copy')]][1]",
        )
        field_root = None
        for xpath in root_xpaths:
            roots = label.find_elements(By.XPATH, xpath)
            if roots:
                field_root = roots[0]
                break
        if field_root is None:
            return ""

        copy_control_xpath = (
            ".//*[contains(@class, 'cursor-pointer') and "
            ".//*[contains(concat(' ', @class, ' '), ' fa-clone ')]] "
            "| .//button[contains(translate(@aria-label, 'COPY', 'copy'), 'copy') "
            "or contains(translate(@title, 'COPY', 'copy'), 'copy')]"
        )
        candidates = field_root.find_elements(By.XPATH, copy_control_xpath)
        if not candidates:
            return ""

        try:
            ActionChains(self.driver).move_to_element(field_root).perform()
        except Exception:
            pass
        for control in candidates:
            try:
                self.set_clipboard("")
                self.click(control)
                copied = self.get_clipboard().strip()
                if copied:
                    return copied
            except Exception:
                continue
        return ""

    def _read_result_field(self, panel, name):
        label, container = self._field_value_container(panel, name)
        visible_value = self._clean_result_value(container.text)
        is_truncated = "View all" in container.text or "View more" in container.text
        if is_truncated:
            copied = self._copy_full_result_value(label, container)
            if copied:
                return copied
            raise RuntimeError(
                "LeetCode truncated result field {!r}, and its Copy control could not be read".format(name)
            )
        if not visible_value:
            raise RuntimeError("LeetCode returned an empty value for result field {!r}".format(name))
        return visible_value

    def parse_testcase(self):
        panel = self._result_panel()
        testcase_inputs = [self._read_result_field(panel, variable) for variable in self.variables]
        output = self._read_result_field(panel, "Expected")
        conditionals = [
            "{} == {}".format(variable, value)
            for variable, value in zip(self.variables, testcase_inputs)
        ]
        testcase_string = "if {}: return {}".format(" and ".join(conditionals), output)
        if testcase_string == self.testcase_strings[-1]:
            raise RuntimeError("LeetCode returned the same testcase twice")
        self.testcase_strings.append(testcase_string)

    def _copy_editor_source(self):
        """Read Monaco's complete document through its native copy command."""
        editor = self.visible_element(By.CSS_SELECTOR, SingleProblemPage.EDITOR_CSS)
        if editor is None:
            return ""
        self.click(editor)
        editor.send_keys(self.modifier_key, "a")
        editor.send_keys(self.modifier_key, "c")
        return self.get_clipboard()

    def _editor_source_equals(self, expected_source):
        expected = ProblemPageHelper.normalize_editor_source(expected_source)

        def condition(driver):
            actual = self._copy_editor_source()
            self._last_editor_source = actual
            return ProblemPageHelper.normalize_editor_source(actual) == expected

        return condition

    @staticmethod
    def _first_source_mismatch(expected, actual):
        expected_lines = ProblemPageHelper.normalize_editor_source(expected).splitlines()
        actual_lines = ProblemPageHelper.normalize_editor_source(actual).splitlines()
        for line_number, (expected_line, actual_line) in enumerate(
            zip(expected_lines, actual_lines),
            start=1,
        ):
            if expected_line != actual_line:
                return "line {} (expected {!r}, got {!r})".format(
                    line_number,
                    expected_line,
                    actual_line,
                )
        if len(expected_lines) != len(actual_lines):
            return "line count (expected {}, got {})".format(
                len(expected_lines),
                len(actual_lines),
            )
        return "unknown difference"

    def _set_monaco_model_source(self, editor, source):
        """Replace the matching Monaco model directly when it is exposed."""
        return bool(self.driver.execute_script(
            """
            const textarea = arguments[0];
            const source = arguments[1];
            const monaco = window.monaco;
            if (!monaco || !monaco.editor || !monaco.editor.getEditors) {
                return false;
            }
            const editor = monaco.editor.getEditors().find((candidate) => {
                const node = candidate.getDomNode && candidate.getDomNode();
                return node && (node === textarea.closest('.monaco-editor') || node.contains(textarea));
            });
            if (!editor) {
                return false;
            }
            editor.setValue(source);
            editor.focus();
            return true;
            """,
            editor,
            source,
        ))

    def _wait_for_editor_source(self, source, timeout=4):
        try:
            WebDriverWait(
                self.driver,
                timeout,
                poll_frequency=0.2,
            ).until(self._editor_source_equals(source))
            return True
        except TimeoutException:
            return False

    def _paste_editor_source(self, editor, source):
        """Clear Monaco before pasting so a lost selection cannot append code."""
        self.click(editor)
        editor.send_keys(self.modifier_key, "a")
        editor.send_keys(Keys.BACKSPACE)

        # Clearing or verifying the editor can replace the system clipboard,
        # so populate it immediately before the paste.
        self.set_clipboard(source)
        editor = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, SingleProblemPage.EDITOR_CSS))
        )
        self.click(editor)
        editor.send_keys(self.modifier_key, "a")
        editor.send_keys(self.modifier_key, "v")

    def _replace_editor_source(self, source):
        mismatch = "unknown difference"
        for attempt in range(1, 4):
            editor = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, SingleProblemPage.EDITOR_CSS))
            )
            if not self._set_monaco_model_source(editor, source):
                self._paste_editor_source(editor, source)

            self._last_editor_source = ""
            if self._wait_for_editor_source(source):
                return
            mismatch = self._first_source_mismatch(source, self._last_editor_source)
            if attempt < 3:
                print(
                    "Monaco source verification failed on attempt {}: {}; retrying".format(
                        attempt,
                        mismatch,
                    ),
                    flush=True,
                )

        raise RuntimeError(
            "Monaco did not retain the pasted source after 3 attempts: {}".format(
                mismatch
            )
        )

    def add_testcase(self):
        testcase = self.testcase_strings[-1]
        existing_source = self.filePath.read_text(encoding="utf-8").rstrip()
        candidate_source = existing_source
        if testcase:
            testcase_line = "        " + testcase
            if not existing_source.endswith(testcase_line):
                candidate_source += "\n" + testcase_line

        compact_source = compact_submission_source(candidate_source)
        self.current_submission_source = (
            compact_source
            + "\n        "
            + self.defaultSubmission
        )
        try:
            # The on-disk archive has no fallback return until its first
            # testcase is discovered, so it is temporarily incomplete Python.
            # Validate the complete source that will actually be submitted.
            ast.parse(self.current_submission_source)
        except SyntaxError as error:
            raise RuntimeError(
                "Refusing to save an invalid generated testcase at line {}: {}".format(
                    error.lineno or "unknown",
                    (error.text or "").strip() or error.msg,
                )
            ) from error

        if candidate_source != existing_source:
            self.filePath.write_text(candidate_source, encoding="utf-8")

        if len(self.current_submission_source.encode("utf-8")) > 95000:
            raise RuntimeError(
                "The compacted submission reached the configured 95,000-byte limit"
            )
        self._replace_editor_source(self.current_submission_source)

    def _retryable_message(self):
        # LeetCode currently renders submission throttling messages in a
        # global `.z-message` portal, outside its aria-labelled notification
        # region.  Keep both selectors for compatibility with either layout.
        regions = self.driver.find_elements(
            By.CSS_SELECTOR,
            "[aria-label='Notifications (F8)'], .z-message, [role='alert']",
        )
        notification_text = "\n".join(region.text for region in regions if region.is_displayed())
        lowered = notification_text.lower()
        for message in ResultConsole.RETRYABLE_MESSAGES:
            if message.lower() in lowered:
                return message
        return ""

    def _result_fingerprint(self):
        """Identify the terminal result currently displayed in the panel."""
        status = self._result_status()
        if status not in ResultConsole.TERMINAL_STATUSES:
            return None
        try:
            panel_text = " ".join(self._result_panel().text.split())
        except Exception:
            panel_text = ""
        return (self._submission_id(self.driver.current_url), status, panel_text)

    @staticmethod
    def _submission_id(url):
        match = re.search(r"/submissions/(?:detail/)?(\d+)(?:/|$)", url)
        return match.group(1) if match else ""

    def _submission_outcome(self, previous_fingerprint):
        """Build a wait condition that rejects the previous submission panel."""
        def condition(driver):
            retryable_message = self._retryable_message()
            if retryable_message:
                return ("retry", retryable_message)

            status = self._result_status()
            current_fingerprint = self._result_fingerprint()
            if (
                status in ResultConsole.TERMINAL_STATUSES
                and current_fingerprint != previous_fingerprint
            ):
                return ("status", status)
            return False

        return condition

    @staticmethod
    def _configured_delay(name, default):
        try:
            return max(0.0, float(os.environ.get(name, default)))
        except ValueError as error:
            raise RuntimeError("{} must be a number of seconds".format(name)) from error

    def _prepare_for_submit(self):
        """Wait for any blocking overlays to clear before clicking submit.

        LeetCode occasionally shows a rate-limit toast ("too soon", etc.) that
        overlaps the toolbar and causes ``element_to_be_clickable`` to time out
        even though the submit button is present in the DOM.  Wait up to 30 s
        for any such message to disappear before proceeding.
        """
        # Wait for any retryable notification to disappear first.
        try:
            WebDriverWait(self.driver, 30).until(lambda driver: not self._retryable_message())
        except TimeoutException:
            pass

        # If the bottom console panel looks collapsed (Testcase tab visible but
        # panel content hidden), clicking the tab will expand it so the inline
        # submit button becomes reachable.  This is best-effort; the submit
        # button in the top toolbar is the primary target.
        try:
            tab = self.driver.find_element(By.CSS_SELECTOR, SingleProblemPage.CONSOLE_TAB_CSS)
            if tab.is_displayed():
                self.click(tab)
                time.sleep(0.5)
        except Exception:
            pass

    def submit(self, pauseTime=None):
        submit_delay = (
            self._configured_delay("LEETCODE_SUBMIT_DELAY", 15)
            if pauseTime is None
            else max(0.0, float(pauseTime))
        )
        retry_delay = self._configured_delay("LEETCODE_RETRY_DELAY", 20)

        for attempt in range(3):
            time.sleep(submit_delay if attempt == 0 else retry_delay)
            self._prepare_for_submit()
            previous_fingerprint = self._result_fingerprint()
            try:
                submit_button = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, SingleProblemPage.SUBMIT_BUTTON_FALLBACK_CSS))
                )
            except TimeoutException as error:
                raise RuntimeError(
                    "Timed out waiting for LeetCode's submit button to become clickable at {}. "
                    "The button may be hidden or disabled after a previous submission result.".format(
                        self.driver.current_url
                    )
                ) from error
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
            except Exception:
                pass
            self.click(submit_button)

            try:
                outcome_type, outcome = self.wait.until(
                    self._submission_outcome(previous_fingerprint)
                )
            except TimeoutException as error:
                headings = [
                    " ".join(heading.text.split())
                    for heading in self.driver.find_elements(By.CSS_SELECTOR, "h3")
                    if heading.is_displayed() and heading.text.strip()
                ]
                raise RuntimeError(
                    "Timed out waiting for LeetCode's submission result at {}. "
                    "Visible result headings: {}".format(
                        self.driver.current_url,
                        headings or "none",
                    )
                ) from error
            if outcome_type == "retry":
                print(
                    "LeetCode reported {!r}; retrying in {} seconds".format(
                        outcome,
                        retry_delay,
                    ),
                    flush=True,
                )
                try:
                    WebDriverWait(self.driver, 8).until(lambda driver: not self._retryable_message())
                except TimeoutException:
                    pass
                continue
            if outcome in {"Wrong Answer", "Accepted"}:
                return outcome
            raise RuntimeError("LeetCode submission failed with status: {}".format(outcome))

        raise RuntimeError("LeetCode rejected three consecutive submission attempts")

    def isSolved(self):
        return self._result_status() == "Accepted"

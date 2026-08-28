from locators import SingleProblemPage
from selenium.webdriver.common.by import By


class ProblemPageHelper:
    @staticmethod
    def normalize_editor_source(source):
        # Monaco uses LF internally, while clipboard integrations can expose
        # CRLF.  A final newline is not semantically part of the editor model
        # for this workflow and can vary between clipboard implementations.
        return source.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")

    @staticmethod
    def editor_contains_python_method():
        def condition(driver):
            # Monaco's textarea is an input surface, not the document model:
            # its value often contains only the current line.  Rendered lines
            # are sufficient for this readiness check because the method
            # declaration is at the top of every LeetCode starter template.
            for line in driver.find_elements(By.CSS_SELECTOR, SingleProblemPage.EDITOR_LINES_CSS):
                try:
                    if line.is_displayed() and "def " in line.text:
                        return True
                except Exception:
                    continue
            return False
        return condition
